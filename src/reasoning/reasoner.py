"""
판단(Reasoning) 모듈

관찰 결과를 바탕으로 구조화된 트레이드오프 분석을 수행합니다.
- Pros (장점)
- Cons (단점)
- Assumptions (가정)
- Constraints (제약)

v2: 입력 특성에 따라 Pros/Cons가 달라지는 규칙 추가
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from src.observation.observer import Observation
from src.observation.schema import ObservationResult


@dataclass
class Analysis:
    """트레이드오프 분석 결과"""

    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)


# === 불확실성/변동성 키워드 ===

UNCERTAINTY_KEYWORDS = [
    "maybe", "perhaps", "possibly", "might", "could be",
    "아마", "검토", "미정", "tbd", "확인 필요", "논의 필요",
    "불확실", "모르", "글쎄", "아직", "예정"
]

VOLATILITY_KEYWORDS = [
    "evolving", "scope change", "flexible", "변동", "변경 가능",
    "유동적", "바뀔 수", "조정 가능", "추후 결정"
]

BUDGET_TIGHT_KEYWORDS = [
    "tight budget", "limited budget", "budget constraint",
    "예산 제약", "예산 부족", "비용 절감", "저예산", "tight"
]


def _detect_ambiguity_level(text: str, observation: Observation) -> str:
    """모호성 수준 감지: HIGH / MEDIUM / LOW"""
    text_lower = text.lower()

    # unknowns가 많으면 HIGH
    if len(observation.unknowns) >= 3:
        return "HIGH"

    # 불확실성 키워드 카운트
    uncertainty_count = sum(1 for kw in UNCERTAINTY_KEYWORDS if kw in text_lower)

    if uncertainty_count >= 3:
        return "HIGH"
    elif uncertainty_count >= 1:
        return "MEDIUM"

    return "LOW"


def _detect_scope_volatility(text: str) -> bool:
    """범위 변동성 감지"""
    text_lower = text.lower()
    return any(kw in text_lower for kw in VOLATILITY_KEYWORDS)


def _detect_tight_budget(text: str) -> bool:
    """예산 제약 감지"""
    text_lower = text.lower()
    return any(kw in text_lower for kw in BUDGET_TIGHT_KEYWORDS)


def _detect_team_uncertainty(observation: Observation) -> bool:
    """팀 규모 불확실성 감지"""
    for constraint in observation.constraints:
        if "확정 필요" in constraint:
            return True
    return False


def reason(
    observation: Observation,
    observation_result: Optional[ObservationResult] = None
) -> Analysis:
    """
    관찰 결과를 분석하여 트레이드오프 구조를 생성합니다.

    v2: 입력 특성에 따라 Pros/Cons가 달라지는 규칙 기반 분석
    """
    pros: list[str] = []
    cons: list[str] = []
    assumptions: list[str] = []
    constraints: list[str] = []

    text = observation.raw_input

    # 관찰된 제약 조건을 분석 제약에 포함
    constraints.extend(observation.constraints)

    # === 모호성 수준 분석 ===
    ambiguity_level = _detect_ambiguity_level(text, observation)

    # === Pros 생성 (조건부) ===
    if observation.requirements:
        # 모호성이 낮을 때만 "요구사항 명확" 문구 사용
        if ambiguity_level == "LOW":
            pros.append("요구사항이 명확하게 정의되어 있어 목표 설정이 가능합니다.")
        elif ambiguity_level == "MEDIUM":
            pros.append("기본적인 요구사항은 파악되었으나 세부 사항 확인이 필요합니다.")
        # HIGH인 경우 "요구사항 명확" 관련 문구 없음

    # 팀 규모가 확정된 경우
    if not _detect_team_uncertainty(observation):
        for constraint in observation.constraints:
            if "[인력]" in constraint and "확정 필요" not in constraint:
                pros.append("팀 규모가 확정되어 역할 분담 계획이 가능합니다.")
                break

    # 일정이 명시된 경우
    for constraint in observation.constraints:
        if "[일정]" in constraint:
            pros.append("일정이 명시되어 마일스톤 설정이 가능합니다.")
            break

    # === Cons 생성 (조건부) ===

    # 모호성이 높은 경우
    if ambiguity_level == "HIGH":
        cons.append("요구사항 불확실성이 높아 재작업 리스크가 있습니다.")
        cons.append("명확화 과정 없이 진행 시 범위 초과(scope creep) 가능성이 큽니다.")

    # 범위 변동성 감지
    if _detect_scope_volatility(text):
        cons.append("요구사항이 변동 중이므로 유연한 아키텍처가 필요합니다.")
        cons.append("범위 변경 가능성으로 인해 초기 설계 시 여유분 확보가 필요합니다.")

    # 예산 제약 감지
    if _detect_tight_budget(text):
        cons.append("예산 제약으로 인해 범위 조정 또는 우선순위 재정립이 필요합니다.")
        cons.append("비용 효율적인 기술 선택이 중요합니다.")

    # 팀 규모 불확실
    if _detect_team_uncertainty(observation):
        cons.append("팀 규모가 미확정이어서 역할 분담 및 일정 계획에 불확실성이 있습니다.")

    # 미확인 정보가 있으면 추가
    if observation.unknowns:
        if ambiguity_level != "HIGH":  # HIGH에서는 이미 추가됨
            cons.append("미확인 정보가 있어 추가 확인이 필요합니다.")

    # Cons가 하나도 없으면 기본 추가
    if not cons:
        cons.append("추가적인 맥락 없이는 최적의 선택을 판단하기 어렵습니다.")

    # === Assumptions 생성 ===
    if ambiguity_level == "LOW":
        assumptions.append("현재 제공된 정보가 의사결정에 충분하다고 가정합니다.")
    elif ambiguity_level == "MEDIUM":
        assumptions.append("미확인 정보는 추후 확인될 것으로 가정합니다.")
    else:  # HIGH
        assumptions.append("요구사항이 구체화되면 분석을 재수행해야 합니다.")
        assumptions.append("현재 분석은 잠정적 방향 설정 용도입니다.")

    if _detect_scope_volatility(text):
        assumptions.append("요구사항 변동에 대응할 수 있는 유연성이 필요합니다.")

    # === Constraints 보강 ===
    if not constraints:
        constraints.append("현재 명시된 기술적/비즈니스적 제약이 없습니다.")

    if _detect_tight_budget(text):
        if not any("예산" in c for c in constraints):
            constraints.append("[예산] 제한적 (비용 효율성 중시)")

    return Analysis(
        pros=pros,
        cons=cons,
        assumptions=assumptions,
        constraints=constraints,
    )
