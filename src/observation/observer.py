"""
Observer 파이프라인 오케스트레이터

사용자 입력을 정량화된 구조 데이터로 변환하는 5단계 파이프라인:
1. Normalize  : 언어/표현 정규화
2. Segment    : 문장/불릿/섹션 분리
3. Extract    : 필드별 추출기 실행
4. Quantify   : 점수/수치화
5. Validate   : 누락/충돌 → unknowns 생성

LLM 없이 rule-based로만 동작한다.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from src.observation.schema import ObservationResult, Unknown, ExtractResult
from src.observation.normalizer import normalize, NormalizeResult
from src.observation.extractors.deadline_extractor import DeadlineExtractor
from src.observation.extractors.team_extractor import TeamSizeExtractor
from src.observation.extractors.requirements_extractor import RequirementsExtractor, RequirementsResult
from src.observation.extractors.platform_extractor import PlatformExtractor
from src.observation.extractors.stack_extractor import StackExtractor
from src.observation.extractors.forbidden_extractor import ForbiddenExtractor


# === Legacy Observation (하위 호환용) ===

@dataclass
class Observation:
    """
    [Legacy] 사용자 입력에서 추출한 관찰 결과

    v0/v1 호환을 위해 유지. 새 코드는 ObservationResult 사용 권장.
    """
    raw_input: str
    requirements: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)


# === Extractor Registry ===

EXTRACTORS = [
    DeadlineExtractor(),
    TeamSizeExtractor(),
    RequirementsExtractor(),
    PlatformExtractor(),
    StackExtractor(),
    ForbiddenExtractor(),
]


# === 불확실성 키워드 ===

UNCERTAINTY_KEYWORDS = [
    "maybe", "perhaps", "possibly", "might", "could be",
    "아마", "검토", "미정", "tbd", "확인 필요", "논의 필요",
    "불확실", "모르", "글쎄", "아직", "예정"
]


# === Pipeline Functions ===

def _run_extractors(
    normalized_text: str,
    sentences: list[str]
) -> list[ExtractResult]:
    """모든 추출기를 실행하고 결과를 수집한다."""
    results: list[ExtractResult] = []

    for extractor in EXTRACTORS:
        result = extractor.extract(normalized_text, sentences)
        if result:
            results.append(result)

    return results


def _calculate_ambiguity_score(
    text: str,
    extractions: list[ExtractResult],
    unknowns: list[Unknown]
) -> int:
    """
    모호성 점수 계산 (0~100)

    높을수록 입력이 모호함:
    - unknowns 많을수록 ↑
    - maybe/TBD 등 불확실 표현 많을수록 ↑
    - 숫자/명세 부족 시 ↑
    """
    score = 0

    # unknowns 개수 (최대 40점)
    score += min(40, len(unknowns) * 10)

    # 불확실 키워드 (최대 30점)
    text_lower = text.lower()
    uncertainty_count = sum(1 for kw in UNCERTAINTY_KEYWORDS if kw in text_lower)
    score += min(30, uncertainty_count * 10)

    # 추출 실패/낮은 신뢰도 (최대 30점)
    low_confidence_count = sum(1 for e in extractions if e.confidence < 0.7)
    missing_critical = 2 - len(extractions)  # deadline, team_size 중 누락된 것
    score += min(30, (low_confidence_count + max(0, missing_critical)) * 10)

    return min(100, score)


def _generate_unknowns(
    text: str,
    extractions: list[ExtractResult],
    deadline_days: Optional[int],
    team_size: Optional[int],
    team_size_min: Optional[int] = None,
    team_size_max: Optional[int] = None,
    team_range_evidence: str = ""
) -> list[Unknown]:
    """
    미확인 정보(unknowns) 자동 생성

    조건:
    - 필수 필드 값이 None
    - 추출 confidence < 임계값
    - 팀 인원이 범위로 입력된 경우
    """
    unknowns: list[Unknown] = []

    # deadline 누락
    if deadline_days is None:
        unknowns.append(Unknown(
            question="프로젝트 마감일이나 기간이 어떻게 되나요?",
            reason="일정 정보가 있어야 적절한 아키텍처 결정이 가능합니다.",
            evidence="일정 관련 정보를 찾지 못했습니다."
        ))

    # team_size 범위인 경우 (확정 필요)
    if team_size_min is not None and team_size_max is not None:
        unknowns.append(Unknown(
            question=f"팀 규모를 {team_size_min}명으로 확정할지 {team_size_max}명으로 확정할지 결정되어 있나요?",
            reason="인원 확정에 따라 일정/범위/역할 분담이 달라집니다.",
            evidence=team_range_evidence
        ))
    # team_size 누락 (범위도 없는 경우)
    elif team_size is None:
        unknowns.append(Unknown(
            question="팀 인원이 몇 명인가요?",
            reason="인력 규모에 따라 적합한 구조가 달라집니다.",
            evidence="인원 관련 정보를 찾지 못했습니다."
        ))

    # 낮은 신뢰도 추출 결과
    for extraction in extractions:
        if extraction.confidence < 0.7:
            unknowns.append(Unknown(
                question=f"{extraction.extractor} 정보가 정확한가요? (추출: {extraction.evidence})",
                reason="추출 신뢰도가 낮습니다.",
                evidence=extraction.evidence
            ))

    return unknowns


def _extract_requirements(sentences: list[str]) -> list[str]:
    """문장에서 요구사항을 추출한다."""
    return [s for s in sentences if s.strip()]


# === Main Pipeline ===

def observe_v2(user_input: str) -> ObservationResult:
    """
    [New] 사용자 입력을 정량화된 구조 데이터로 변환한다.

    Pipeline:
    1. Normalize  : 언어/표현 정규화
    2. Segment    : 문장 분리
    3. Extract    : 추출기 실행
    4. Quantify   : 점수화
    5. Validate   : unknowns 생성
    """
    # 빈 입력 처리
    if not user_input or not user_input.strip():
        return ObservationResult(
            raw_input=user_input,
            unknowns=[Unknown(
                question="입력을 다시 해주세요.",
                reason="입력이 비어 있습니다.",
                evidence=""
            )]
        )

    # 1. Normalize
    norm_result: NormalizeResult = normalize(user_input)

    # 2. Segment (normalize에서 이미 수행)
    sentences = norm_result.sentences

    # 3. Extract
    extractions = _run_extractors(norm_result.normalized, sentences)

    # 추출 결과에서 값 가져오기
    deadline_days: Optional[int] = None
    team_size: Optional[int] = None
    team_size_min: Optional[int] = None
    team_size_max: Optional[int] = None
    team_range_evidence: str = ""
    must_have: list[str] = []
    nice_to_have: list[str] = []
    platform: Optional[str] = None
    language_stack: list[str] = []
    forbidden: list[str] = []

    for extraction in extractions:
        if extraction.extractor == "deadline":
            deadline_days = extraction.value
        elif extraction.extractor == "team_size":
            # 범위인지 단일값인지 확인
            if isinstance(extraction.value, dict):
                # 범위 입력: team_size는 None, min/max만 설정
                team_size_min = extraction.value.get("min")
                team_size_max = extraction.value.get("max")
                team_range_evidence = extraction.evidence
            else:
                # 단일값 입력
                team_size = extraction.value
        elif extraction.extractor == "requirements":
            # RequirementsResult에서 must_have, nice_to_have 추출
            if isinstance(extraction.value, RequirementsResult):
                must_have = extraction.value.must_have
                nice_to_have = extraction.value.nice_to_have
        elif extraction.extractor == "platform":
            platform = extraction.value
        elif extraction.extractor == "stack":
            language_stack = extraction.value if isinstance(extraction.value, list) else [extraction.value]
        elif extraction.extractor == "forbidden":
            forbidden = extraction.value if isinstance(extraction.value, list) else [extraction.value]

    # 4. Validate & Generate Unknowns
    unknowns = _generate_unknowns(
        user_input,
        extractions,
        deadline_days,
        team_size,
        team_size_min,
        team_size_max,
        team_range_evidence
    )

    # 5. Quantify
    ambiguity_score = _calculate_ambiguity_score(user_input, extractions, unknowns)

    # 요구사항: 추출된 항목이 없으면 문장으로 fallback
    if not must_have:
        must_have = _extract_requirements(sentences)

    return ObservationResult(
        raw_input=user_input,
        lang_mix_ratio=norm_result.lang_mix_ratio,
        tokens_estimate=norm_result.tokens_estimate,
        deadline_days=deadline_days,
        team_size=team_size,
        team_size_min=team_size_min,
        team_size_max=team_size_max,
        must_have=must_have,
        nice_to_have=nice_to_have,
        platform=platform,
        language_stack=language_stack,
        forbidden=forbidden,
        ambiguity_score=ambiguity_score,
        unknowns=unknowns,
        extractions=extractions,
    )


def observe(user_input: str) -> Observation:
    """
    [Legacy] 하위 호환용 observe 함수

    기존 Reasoner/Proposer가 사용하는 Observation 형식으로 반환.
    내부적으로는 observe_v2를 사용.
    """
    result = observe_v2(user_input)

    # ObservationResult → Observation 변환
    constraints: list[str] = []

    if result.team_size is not None:
        constraints.append(f"[인력] 팀 {result.team_size}명")
    elif result.team_size_min is not None and result.team_size_max is not None:
        constraints.append(f"[인력] 팀 {result.team_size_min}~{result.team_size_max}명 (확정 필요)")

    if result.deadline_days is not None:
        # 일수를 적절한 단위로 변환
        days = result.deadline_days
        if days >= 365:
            years = days // 365
            months = (days % 365) // 30
            if months > 0:
                constraints.append(f"[일정] {years}년 {months}개월")
            else:
                constraints.append(f"[일정] {years}년")
        elif days >= 30:
            months = days // 30
            constraints.append(f"[일정] {months}개월")
        elif days >= 7:
            weeks = days // 7
            constraints.append(f"[일정] {weeks}주")
        else:
            constraints.append(f"[일정] {days}일")

    # unknowns 변환
    unknowns_str: list[str] = [
        f"[미확인] {u.question}" for u in result.unknowns
    ]

    return Observation(
        raw_input=user_input,
        requirements=result.must_have,
        constraints=constraints,
        unknowns=unknowns_str,
    )
