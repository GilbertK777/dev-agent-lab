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
    # 영어 불확실 표현
    "maybe", "perhaps", "possibly", "might", "could be",
    "likely", "probably", "prefer", "preferred", "ideally",
    # 범위/변동 표현
    "within", "around", "approximately", "about",
    "flexible", "evolving", "changing",
    # 위험 신호
    "tight", "scope change", "budget tight",
    "sooner", "if possible",
    # 한글 불확실 표현
    "아마", "검토", "미정", "tbd", "확인 필요", "논의 필요",
    "불확실", "모르", "글쎄", "아직", "예정",
    "가능성", "변동", "유동적",
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
    unknowns: list[Unknown],
    must_have_count: int = 0,
    nice_to_have_count: int = 0
) -> int:
    """
    모호성 점수 계산 (0~100)

    높을수록 입력이 모호함:
    - unknowns 많을수록 ↑
    - maybe/TBD 등 불확실 표현 많을수록 ↑
    - 숫자/명세 부족 시 ↑
    - 구조화된 요구사항(must_have + nice_to_have)이 많으면 ↓

    스케일:
    - 0~20: 낮음 (명확함)
    - 21~50: 중간
    - 51~100: 높음 (명확화 필요)
    """
    score = 0

    # unknowns 개수 (최대 30점, 항목당 15점)
    score += min(30, len(unknowns) * 15)

    # 불확실 키워드 카운트
    text_lower = text.lower()
    uncertainty_count = sum(1 for kw in UNCERTAINTY_KEYWORDS if kw in text_lower)

    # 키워드 점수 (점진적 증가, 최대 30점)
    # 1-2개: 각 3점, 3-4개: 각 4점, 5개+: 각 5점
    keyword_score = 0
    for i in range(uncertainty_count):
        if i < 2:
            keyword_score += 3
        elif i < 4:
            keyword_score += 4
        else:
            keyword_score += 5
    score += min(30, keyword_score)

    # 핵심 추출기(deadline, team_size) 누락 시 가산점 (최대 20점)
    extractor_names = {e.extractor for e in extractions}
    critical_extractors = {"deadline", "team_size"}
    missing_critical = len(critical_extractors - extractor_names)
    score += missing_critical * 10

    # 낮은 신뢰도 추출 (최대 20점)
    low_confidence_count = sum(1 for e in extractions if e.confidence < 0.7)
    score += min(20, low_confidence_count * 10)

    # 구조화된 요구사항이 풍부하면 감점 (명확한 입력으로 판단)
    # must_have + nice_to_have 합이 5 이상이면 -15점
    structured_count = must_have_count + nice_to_have_count
    if structured_count >= 5:
        score -= 15

    # 컴플라이언스/운영제약 신호가 있으면 +5 (tie-breaker)
    compliance_signals_en = [
        "no internet", "offline", "security", "compliance", "production", "forbidden",
    ]
    compliance_signals_ko = [
        "인터넷 불가", "오프라인", "보안", "컴플라이언스", "운영", "현장", "프로덕션", "금지",
    ]
    # 한글은 공백 변화에도 안정적으로 잡히도록 공백 제거 버전도 검사
    text_compact = text_lower.replace(" ", "")
    has_compliance = (
        any(sig in text_lower for sig in compliance_signals_en) or
        any(sig in text_lower or sig.replace(" ", "") in text_compact for sig in compliance_signals_ko)
    )
    if has_compliance:
        score += 5

    return max(0, min(100, score))


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
        question = _generate_team_range_question(
            text, team_size_min, team_size_max
        )
        unknowns.append(Unknown(
            question=question,
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

    # 키워드 기반 추가 unknowns (우선순위 높은 확인 사항)
    text_lower = text.lower()
    text_compact = text_lower.replace(" ", "")

    # SECS/GEM 프로토콜
    if "secs/gem" in text_lower or "secs gem" in text_lower or "secsgem" in text_compact:
        unknowns.append(Unknown(
            question="SECS/GEM 연동 대상 장비와 메시지 규격이 확정되었나요?",
            reason="SECS/GEM은 장비별로 메시지 구조가 다를 수 있어 사전 확인이 필요합니다.",
            evidence="SECS/GEM integration 언급"
        ))

    # Traceability / Audit logging
    if "traceability" in text_lower or "추적" in text_lower:
        unknowns.append(Unknown(
            question="Traceability 요구 범위가 어디까지인가요? (제품 이력, 공정 이력, 작업자 이력 등)",
            reason="추적 범위에 따라 데이터 모델과 저장 구조가 달라집니다.",
            evidence="traceability 언급"
        ))

    if "audit" in text_lower or "감사" in text_lower:
        unknowns.append(Unknown(
            question="Audit logging 보관 기간과 조회 요구사항이 있나요?",
            reason="로그 보관 정책에 따라 스토리지 설계가 달라집니다.",
            evidence="audit logging 언급"
        ))

    # Role-based access control / 권한
    if "role-based" in text_lower or "rbac" in text_lower or "권한" in text_lower or "access control" in text_lower:
        unknowns.append(Unknown(
            question="운영자 권한 체계(역할/레벨)가 정의되어 있나요?",
            reason="권한 구조에 따라 인증/인가 설계가 달라집니다.",
            evidence="role-based access control / 권한 언급"
        ))

    # No internet / 오프라인 / Offline update
    if "no internet" in text_lower or "인터넷 불가" in text_lower or "인터넷불가" in text_compact:
        unknowns.append(Unknown(
            question="인터넷 불가 환경에서 소프트웨어 배포/업데이트 방식이 정해져 있나요?",
            reason="오프라인 환경은 배포 파이프라인 설계에 영향을 줍니다.",
            evidence="no internet / 인터넷 불가 언급"
        ))

    # Compliance / 보안
    if "compliance" in text_lower or "컴플라이언스" in text_lower:
        unknowns.append(Unknown(
            question="준수해야 할 컴플라이언스 규정(예: FDA, ISO, 내부 보안 정책)이 있나요?",
            reason="컴플라이언스 요구사항에 따라 문서화 및 검증 절차가 달라집니다.",
            evidence="compliance 언급"
        ))

    if ("security" in text_lower or "보안" in text_lower) and "compliance" not in text_lower:
        unknowns.append(Unknown(
            question="보안 요구사항(암호화, 접근 제어, 감사 로그 등)이 구체적으로 정의되어 있나요?",
            reason="보안 요구 수준에 따라 아키텍처가 달라집니다.",
            evidence="security / 보안 언급"
        ))

    # WSL2 개발환경
    if "wsl" in text_lower:
        unknowns.append(Unknown(
            question="WSL2 개발환경과 실제 운영환경(Windows) 간 차이로 인한 제약이 있나요?",
            reason="개발/운영 환경 차이는 CI/CD 및 테스트 전략에 영향을 줍니다.",
            evidence="WSL2 언급"
        ))

    return unknowns


def _generate_team_range_question(
    text: str,
    team_size_min: int,
    team_size_max: int
) -> str:
    """
    팀 인원 범위에 대한 확인 질문을 생성한다.

    입력에 "ideally", "preferred", "선호" 등의 표현이 있으면
    해당 nuance를 반영한 질문을 생성한다.
    """
    text_lower = text.lower()

    # 선호값 추출 패턴
    preferred_value = None
    preferred_keywords = ["ideally", "preferred", "best", "선호", "가능하면", "이상적"]

    # "ideally N" 또는 "선호 N명" 패턴 검색
    ideally_pattern = re.search(r'ideally\s+(\d+)', text_lower)
    preferred_pattern = re.search(r'prefer(?:red|s)?\s+(\d+)', text_lower)
    korean_pattern = re.search(r'(?:선호|이상적)[^\d]*(\d+)', text)

    if ideally_pattern:
        preferred_value = int(ideally_pattern.group(1))
    elif preferred_pattern:
        preferred_value = int(preferred_pattern.group(1))
    elif korean_pattern:
        preferred_value = int(korean_pattern.group(1))

    # 선호 키워드가 있는지 확인
    has_preference = any(kw in text_lower for kw in preferred_keywords)

    # 질문 생성
    if preferred_value and team_size_min <= preferred_value <= team_size_max:
        return (
            f"팀 인원은 {team_size_min}~{team_size_max}명 범위이며, "
            f"이상적으로는 {preferred_value}명을 선호하는 것으로 보입니다. "
            f"초기 기준 인원을 {preferred_value}명으로 확정해도 될까요?"
        )
    elif has_preference:
        return (
            f"팀 인원은 {team_size_min}~{team_size_max}명 범위로 보입니다. "
            f"선호하는 인원 규모가 있다면, 그 기준으로 확정해도 될까요?"
        )
    else:
        return (
            f"팀 규모가 {team_size_min}~{team_size_max}명 범위로 되어 있습니다. "
            f"초기 계획 기준 인원을 몇 명으로 확정할까요?"
        )


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
    # 구조화된 요구사항 개수를 전달 (fallback 전 원본 기준)
    ambiguity_score = _calculate_ambiguity_score(
        user_input, extractions, unknowns,
        must_have_count=len(must_have),
        nice_to_have_count=len(nice_to_have)
    )

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

    # Step2 추출값 반영: 플랫폼/스택/금지
    if result.platform:
        constraints.append(f"[플랫폼] {result.platform}")

    if result.language_stack:
        constraints.append(f"[스택] {'/'.join(result.language_stack)}")

    if result.forbidden:
        constraints.append(f"[금지] {', '.join(result.forbidden)} (운영)")

    # 운영제약 신호 추출 (텍스트에서 직접)
    text_lower = user_input.lower()
    operational_constraints = []

    # WSL2 개발환경
    if "wsl" in text_lower or "wsl2" in text_lower:
        operational_constraints.append("WSL2 개발환경")

    # 인터넷/오프라인 제약
    if "no internet" in text_lower or "인터넷 불가" in text_lower or "인터넷불가" in text_lower:
        operational_constraints.append("인터넷 불가")
    if "offline" in text_lower or "오프라인" in text_lower:
        if "offline update" in text_lower or "오프라인 업데이트" in text_lower:
            operational_constraints.append("오프라인 업데이트만 가능")
        elif "인터넷 불가" not in " ".join(operational_constraints):
            operational_constraints.append("오프라인 환경")

    # 보안/컴플라이언스
    if "security" in text_lower or "보안" in text_lower:
        operational_constraints.append("보안 정책 적용")
    if "compliance" in text_lower or "컴플라이언스" in text_lower:
        operational_constraints.append("컴플라이언스 요구")

    if operational_constraints:
        constraints.append(f"[운영제약] {', '.join(operational_constraints)}")

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
