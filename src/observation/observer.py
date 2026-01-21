"""
관찰(Observation) 모듈

사용자 입력에서 핵심 정보를 추출합니다.
- requirements: 사용자가 해결하고자 하는 문제, 질문 또는 목표
- constraints: 입력에서 감지 가능한 제약 조건
- unknowns: 의사결정에 중요하지만 입력에 없는 정보

주의: 판단이나 추천을 하지 않고, 관찰 가능한 사실과 부족한 정보만 정리합니다.
"""

import re
from dataclasses import dataclass, field


@dataclass
class Observation:
    """사용자 입력에서 추출한 관찰 결과"""

    raw_input: str
    requirements: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)


# 인력(팀 규모) 추출 패턴
TEAM_SIZE_PATTERNS: list[re.Pattern[str]] = [
    # "팀은 3명", "팀 3명", "팀이 5명"
    re.compile(r"팀[은이]?\s*(\d+)\s*명", re.IGNORECASE),
    # "인원 5명", "인원은 3명"
    re.compile(r"인원[은이]?\s*(\d+)\s*명", re.IGNORECASE),
    # "개발자 2명", "개발자는 3명"
    re.compile(r"개발자[는은이]?\s*(\d+)\s*명", re.IGNORECASE),
    # "3명이고", "5명 정도"
    re.compile(r"(\d+)\s*명\s*(이고|정도|으로|의\s*팀)", re.IGNORECASE),
]

# 일정(기간) 추출 패턴
TIMELINE_PATTERNS: list[re.Pattern[str]] = [
    # "출시까지 2개월", "출시까지는 3주"
    re.compile(r"출시\s*(까지[는]?)\s*(\d+)\s*(개월|주|일)", re.IGNORECASE),
    # "2개월 남았", "3주 정도 남았"
    re.compile(r"(\d+)\s*(개월|주|일)\s*(정도\s*)?(남|안에|내에|이내)", re.IGNORECASE),
    # "마감 2주", "기한 1개월"
    re.compile(r"(마감|기한|deadline)[까지]?\s*(\d+)\s*(개월|주|일)", re.IGNORECASE),
    # 단순 기간: "2개월", "3주" (fallback)
    re.compile(r"(\d+)\s*(개월|주|일|week|month|day)", re.IGNORECASE),
]

# 변동성 추출 패턴
VARIABILITY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"요구사항\s*(변경|변동|바뀜)", re.IGNORECASE),
    re.compile(r"변경[이]?\s*(많|잦|자주)", re.IGNORECASE),
    re.compile(r"자주\s*바뀜|불확실", re.IGNORECASE),
]

# 기술적 제약 패턴
TECHNICAL_CONSTRAINT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"필수|금지|불가|cannot|must not|should not|required|레거시|legacy", re.IGNORECASE),
]

# 의사결정에 중요하지만 자주 누락되는 정보
POTENTIAL_UNKNOWNS: list[tuple[str, re.Pattern[str]]] = [
    ("트래픽 규모", re.compile(r"트래픽|traffic|tps|rps|동시\s*접속|사용자\s*수", re.IGNORECASE)),
    ("외부 연동", re.compile(r"외부\s*(api|연동|시스템)|third.?party|integration", re.IGNORECASE)),
    ("배포 방식", re.compile(r"배포|deploy|kubernetes|k8s|docker|cloud|aws|gcp|azure", re.IGNORECASE)),
    ("데이터베이스", re.compile(r"db|database|데이터베이스|mysql|postgres|mongo|redis", re.IGNORECASE)),
    ("인력", re.compile(r"팀|인원|개발자|명", re.IGNORECASE)),
    ("일정", re.compile(r"기간|일정|마감|출시|개월|주|deadline", re.IGNORECASE)),
]


def _extract_team_size(text: str) -> str | None:
    """팀 규모(인력) 정보를 추출합니다."""
    for pattern in TEAM_SIZE_PATTERNS:
        match = pattern.search(text)
        if match:
            # 첫 번째 캡처 그룹이 숫자
            num = match.group(1)
            return f"[인력] 팀 {num}명"
    return None


def _extract_timeline(text: str) -> str | None:
    """일정(기간) 정보를 추출합니다."""
    for pattern in TIMELINE_PATTERNS:
        match = pattern.search(text)
        if match:
            groups = match.groups()
            # 패턴에 따라 숫자와 단위 위치가 다름
            # "출시까지 2개월" 패턴: groups = ('까지', '2', '개월')
            # "2개월 남았" 패턴: groups = ('2', '개월', ...)
            # "마감 2주" 패턴: groups = ('마감', '2', '주')
            # "2개월" 패턴: groups = ('2', '개월')

            num = None
            unit = None
            for g in groups:
                if g and g.isdigit():
                    num = g
                elif g in ('개월', '주', '일', 'week', 'month', 'day'):
                    unit = g

            if num and unit:
                return f"[일정] {num}{unit}"
    return None


def _extract_variability(text: str) -> str | None:
    """요구사항 변동성 정보를 추출합니다."""
    for pattern in VARIABILITY_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"[변동성] {match.group()}"
    return None


def _extract_technical_constraints(text: str) -> str | None:
    """기술적 제약 정보를 추출합니다."""
    for pattern in TECHNICAL_CONSTRAINT_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"[기술 제약] {match.group()}"
    return None


def _extract_constraints(text: str) -> list[str]:
    """입력 텍스트에서 제약 조건을 추출합니다."""
    constraints: list[str] = []

    # 인력(팀 규모) 추출
    team_size = _extract_team_size(text)
    if team_size:
        constraints.append(team_size)

    # 일정(기간) 추출
    timeline = _extract_timeline(text)
    if timeline:
        constraints.append(timeline)

    # 변동성 추출
    variability = _extract_variability(text)
    if variability:
        constraints.append(variability)

    # 기술적 제약 추출
    technical = _extract_technical_constraints(text)
    if technical:
        constraints.append(technical)

    return constraints


def _identify_unknowns(text: str, found_constraints: list[str]) -> list[str]:
    """의사결정에 중요하지만 입력에 없는 정보를 식별합니다."""
    unknowns: list[str] = []

    # 이미 감지된 제약 유형 추출
    found_types = set()
    for constraint in found_constraints:
        if constraint.startswith("[") and "]" in constraint:
            found_types.add(constraint.split("]")[0][1:])

    for unknown_type, pattern in POTENTIAL_UNKNOWNS:
        # 이미 해당 정보가 제약으로 감지되었으면 스킵
        if unknown_type in found_types:
            continue
        # 텍스트에 언급이 없으면 unknown으로 추가
        if not pattern.search(text):
            unknowns.append(f"[미확인] {unknown_type} 정보가 입력에 없습니다.")

    # 중복 제거
    return list(dict.fromkeys(unknowns))


def _extract_requirements(text: str, constraints: list[str]) -> list[str]:
    """요구사항(해결하고자 하는 문제, 질문, 목표)을 추출합니다."""
    requirements: list[str] = []

    # 제약으로 추출된 부분을 제외한 나머지를 요구사항으로 처리
    # 질문 형태나 목표 형태의 문장을 찾음
    lines = text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 전체 라인을 요구사항으로 추가 (제약은 별도로 추출됨)
        requirements.append(line)

    return requirements


def observe(user_input: str) -> Observation:
    """
    사용자 입력을 분석하여 구조화된 관찰 결과를 반환합니다.

    규칙 기반으로 다음을 추출합니다:
    - requirements: 사용자의 질문이나 목표
    - constraints: 팀 규모, 일정, 변동성 등 감지된 제약
    - unknowns: 의사결정에 필요하지만 입력에 없는 정보
    """
    if not user_input.strip():
        return Observation(
            raw_input=user_input,
            requirements=[],
            constraints=[],
            unknowns=["입력이 비어 있습니다."],
        )

    # 1. 제약 조건 추출
    constraints = _extract_constraints(user_input)

    # 2. 요구사항 추출
    requirements = _extract_requirements(user_input, constraints)

    # 3. 누락된 정보(unknowns) 식별
    unknowns = _identify_unknowns(user_input, constraints)

    return Observation(
        raw_input=user_input,
        requirements=requirements,
        constraints=constraints,
        unknowns=unknowns,
    )
