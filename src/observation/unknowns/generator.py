"""
Unknowns Generator

미확인 정보(unknowns) 자동 생성 모듈:
- 필수 필드 누락 감지
- 낮은 신뢰도 추출 결과 확인
- 키워드 기반 도메인 특화 질문 생성
"""

import re
from typing import Optional

from src.observation.schema import Unknown, ExtractResult


def generate_unknowns(
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
    - 키워드 기반 도메인 특화 질문
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
    _add_keyword_based_unknowns(text, unknowns)

    return unknowns


def _add_keyword_based_unknowns(text: str, unknowns: list[Unknown]) -> None:
    """키워드 기반 도메인 특화 질문 추가"""
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
