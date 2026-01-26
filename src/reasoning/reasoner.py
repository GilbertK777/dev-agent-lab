"""
판단(Reasoning) 모듈

관찰 결과를 바탕으로 구조화된 트레이드오프 분석을 수행합니다.
- Pros (장점)
- Cons (단점)
- Assumptions (가정)
- Constraints (제약)
"""

from dataclasses import dataclass, field

from src.observation.schema import ObservationResult


@dataclass
class Analysis:
    """트레이드오프 분석 결과"""
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)


# === 키워드 감지 헬퍼 ===

VOLATILITY_KEYWORDS = [
    "evolving", "scope change", "flexible", "변동", "변경 가능",
    "유동적", "바뀔 수", "조정 가능", "추후 결정"
]

BUDGET_TIGHT_KEYWORDS = [
    "tight budget", "limited budget", "budget constraint",
    "예산 제약", "예산 부족", "비용 절감", "저예산", "tight"
]


def _detect_scope_volatility(text: str) -> bool:
    """범위 변동성 감지"""
    return any(kw in text.lower() for kw in VOLATILITY_KEYWORDS)


def _detect_tight_budget(text: str) -> bool:
    """예산 제약 감지"""
    return any(kw in text.lower() for kw in BUDGET_TIGHT_KEYWORDS)


def _get_ambiguity_level(score: int) -> str:
    """모호성 점수를 바탕으로 수준을 반환: HIGH / MEDIUM / LOW"""
    if score >= 51:
        return "HIGH"
    if score >= 21:
        return "MEDIUM"
    return "LOW"


def _format_constraints(obs: ObservationResult) -> list[str]:
    """ObservationResult를 기반으로 제약조건 리스트를 생성"""
    constraints: list[str] = []

    # 팀 규모
    if obs.team_size is not None:
        constraints.append(f"[인력] 팀 {obs.team_size}명")
    elif obs.team_size_min is not None and obs.team_size_max is not None:
        constraints.append(f"[인력] 팀 {obs.team_size_min}~{obs.team_size_max}명 (확정 필요)")

    # 일정
    if obs.deadline_days is not None:
        days = obs.deadline_days
        if days >= 365:
            years = days // 365
            months = (days % 365) // 30
            unit = f"{years}년 {months}개월" if months > 0 else f"{years}년"
        elif days >= 30:
            unit = f"{days // 30}개월"
        elif days >= 7:
            unit = f"{days // 7}주"
        else:
            unit = f"{days}일"
        constraints.append(f"[일정] {unit}")

    # 플랫폼/스택/금지
    if obs.platform:
        constraints.append(f"[플랫폼] {obs.platform}")
    if obs.language_stack:
        constraints.append(f"[스택] {', '.join(obs.language_stack)}")
    if obs.forbidden:
        constraints.append(f"[금지] {', '.join(obs.forbidden)}")

    return constraints


def reason(obs: ObservationResult) -> Analysis:
    """
    관찰 결과를 분석하여 트레이드오프 구조를 생성합니다.
    """
    pros: list[str] = []
    cons: list[str] = []
    assumptions: list[str] = []

    # 1. 제약조건 포맷팅
    constraints = _format_constraints(obs)

    # 2. 입력 특성 감지
    ambiguity_level = _get_ambiguity_level(obs.ambiguity_score)
    has_scope_volatility = _detect_scope_volatility(obs.raw_input)
    has_tight_budget = _detect_tight_budget(obs.raw_input)
    is_team_size_unconfirmed = obs.team_size_min is not None

    # === Pros 생성 ===
    if obs.must_have or obs.nice_to_have:
        if ambiguity_level == "LOW":
            pros.append("요구사항이 명확하게 정의되어 목표 설정이 수월합니다.")
        elif ambiguity_level == "MEDIUM":
            pros.append("핵심 요구사항이 파악되어 초기 계획 착수가 가능합니다.")

    if not is_team_size_unconfirmed and obs.team_size is not None:
        pros.append("팀 규모가 확정되어 역할 분담 및 리소스 계획이 용이합니다.")

    if obs.deadline_days is not None:
        pros.append("프로젝트 일정이 명시되어 구체적인 마일스톤 설정이 가능합니다.")

    # === Cons 생성 ===
    if ambiguity_level == "HIGH":
        cons.append("입력의 불확실성이 높아 재작업 및 일정 지연 리스크가 존재합니다.")
    if obs.unknowns:
        cons.append(f"{len(obs.unknowns)}개의 미확인 정보가 있어, 진행 전 명확화가 필요합니다.")

    if has_scope_volatility:
        cons.append("요구사항 변동 가능성이 언급되어, 유연하고 확장 가능한 아키텍처 설계가 중요합니다.")
    if has_tight_budget:
        cons.append("예산 제약으로 인해 기술 선택 및 기능 범위에 대한 신중한 트레이드오프가 필요합니다.")
    if is_team_size_unconfirmed:
        cons.append("팀 규모가 확정되지 않아 역할 분담 및 일정 계획에 불확실성이 있습니다.")

    if not cons:
        cons.append("현재 입력만으로는 잠재적 리스크를 판단하기 어렵습니다.")

    # === Assumptions 생성 ===
    if ambiguity_level == "LOW":
        assumptions.append("제공된 정보가 정확하고 완전하다고 가정합니다.")
    else:
        assumptions.append("미확인 및 불확실한 내용은 프로젝트 진행 과정에서 명확화될 것으로 가정합니다.")

    if has_scope_volatility:
        assumptions.append("프로젝트 범위 변경에 대응할 수 있는 프로세스(예: 정기적 우선순위 재검토)가 필요합니다.")
    else:
        assumptions.append("현재 정의된 요구사항이 크게 변경되지 않을 것으로 가정합니다.")

    # === Constraints 보강 ===
    if has_tight_budget and not any("예산" in c for c in constraints):
        constraints.append("[예산] 제한적 (비용 효율성 중시)")

    if not constraints:
        constraints.append("명시적인 기술적/비즈니스적 제약 조건이 없습니다.")

    return Analysis(
        pros=pros,
        cons=cons,
        assumptions=assumptions,
        constraints=constraints,
    )
