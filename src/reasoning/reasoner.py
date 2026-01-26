"""
판단(Reasoning) 모듈

관찰 결과를 바탕으로 구조화된 트레이드오프 분석을 수행합니다.
- Pros (장점)
- Cons (단점)
- Assumptions (가정)
- Constraints (제약)

v2: 입력 특성에 따라 Pros/Cons가 달라지는 규칙 추가
"""

from dataclasses import dataclass, field

from src.observation.schema import ObservationResult
from src.reasoning.rules.base import RuleContext
from src.reasoning.rules.engine import RuleEngine
from src.reasoning.rules.budget_rule import BudgetConstraintRule


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

# NOTE: BUDGET_TIGHT_KEYWORDS는 src/reasoning/rules/budget_rule.py로 이관됨


def _detect_ambiguity_level(text: str, result: ObservationResult) -> str:
    """모호성 수준 감지: HIGH / MEDIUM / LOW"""
    text_lower = text.lower()

    # unknowns가 많으면 HIGH
    if len(result.unknowns) >= 3:
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


# NOTE: _detect_tight_budget()는 BudgetConstraintRule.applies()로 이관됨


def _detect_team_uncertainty(result: ObservationResult) -> bool:
    """팀 규모 불확실성 감지"""
    # team_size_min/max가 있으면 범위 입력 → 불확실
    if result.team_size_min is not None and result.team_size_max is not None:
        return True
    # team_size도 없으면 불확실
    if result.team_size is None:
        return True
    return False


def reason(result: ObservationResult) -> Analysis:
    """
    관찰 결과를 분석하여 트레이드오프 구조를 생성합니다.

    v2: 입력 특성에 따라 Pros/Cons가 달라지는 규칙 기반 분석
    v2.1: Rule Engine Lite 도입 (BudgetConstraintRule)
    """
    text = result.raw_input

    # === 모호성 수준 분석 ===
    ambiguity_level = _detect_ambiguity_level(text, result)

    # === Rule Engine 컨텍스트 초기화 ===
    ctx = RuleContext(
        result=result,
        ambiguity_level=ambiguity_level,
        pros=[],
        cons=[],
        assumptions=[],
        constraints=list(_build_constraints(result)),  # 기존 제약 조건으로 초기화
    )

    # === Pros 생성 (조건부) ===
    if result.must_have:
        # 모호성이 낮을 때만 "요구사항 명확" 문구 사용
        if ambiguity_level == "LOW":
            ctx.pros.append("요구사항이 명확하게 정의되어 있어 목표 설정이 가능합니다.")
        elif ambiguity_level == "MEDIUM":
            ctx.pros.append("기본적인 요구사항은 파악되었으나 세부 사항 확인이 필요합니다.")
        # HIGH인 경우 "요구사항 명확" 관련 문구 없음

    # 팀 규모가 확정된 경우
    if not _detect_team_uncertainty(result):
        if result.team_size is not None:
            ctx.pros.append("팀 규모가 확정되어 역할 분담 계획이 가능합니다.")

    # 일정이 명시된 경우
    if result.deadline_days is not None:
        ctx.pros.append("일정이 명시되어 마일스톤 설정이 가능합니다.")

    # === Cons 생성 (조건부) ===

    # 모호성이 높은 경우
    if ambiguity_level == "HIGH":
        ctx.cons.append("요구사항 불확실성이 높아 재작업 리스크가 있습니다.")
        ctx.cons.append("명확화 과정 없이 진행 시 범위 초과(scope creep) 가능성이 큽니다.")

    # 범위 변동성 감지
    if _detect_scope_volatility(text):
        ctx.cons.append("요구사항이 변동 중이므로 유연한 아키텍처가 필요합니다.")
        ctx.cons.append("범위 변경 가능성으로 인해 초기 설계 시 여유분 확보가 필요합니다.")

    # === Rule Engine 실행 (예산 제약 규칙) ===
    engine = RuleEngine()
    engine.register(BudgetConstraintRule())
    engine.run(ctx)

    # 팀 규모 불확실
    if _detect_team_uncertainty(result):
        ctx.cons.append("팀 규모가 미확정이어서 역할 분담 및 일정 계획에 불확실성이 있습니다.")

    # 미확인 정보가 있으면 추가
    if result.unknowns:
        if ambiguity_level != "HIGH":  # HIGH에서는 이미 추가됨
            ctx.cons.append("미확인 정보가 있어 추가 확인이 필요합니다.")

    # Cons가 하나도 없으면 기본 추가
    if not ctx.cons:
        ctx.cons.append("추가적인 맥락 없이는 최적의 선택을 판단하기 어렵습니다.")

    # === Assumptions 생성 ===
    if ambiguity_level == "LOW":
        ctx.assumptions.append("현재 제공된 정보가 의사결정에 충분하다고 가정합니다.")
    elif ambiguity_level == "MEDIUM":
        ctx.assumptions.append("미확인 정보는 추후 확인될 것으로 가정합니다.")
    else:  # HIGH
        ctx.assumptions.append("요구사항이 구체화되면 분석을 재수행해야 합니다.")
        ctx.assumptions.append("현재 분석은 잠정적 방향 설정 용도입니다.")

    if _detect_scope_volatility(text):
        ctx.assumptions.append("요구사항 변동에 대응할 수 있는 유연성이 필요합니다.")

    # 낮은 신뢰도 추출 결과 경고
    low_confidence_extractions = [
        e for e in result.extractions if e.confidence < 0.7
    ]
    if low_confidence_extractions:
        names = ", ".join(e.extractor for e in low_confidence_extractions)
        ctx.assumptions.append(
            f"[주의] 일부 추출 결과({names})의 신뢰도가 낮아 확인이 필요합니다."
        )

    # === Constraints 보강 ===
    if not ctx.constraints:
        ctx.constraints.append("현재 명시된 기술적/비즈니스적 제약이 없습니다.")

    # NOTE: 예산 제약 추가는 BudgetConstraintRule에서 처리됨

    return Analysis(
        pros=ctx.pros,
        cons=ctx.cons,
        assumptions=ctx.assumptions,
        constraints=ctx.constraints,
    )


def _build_constraints(result: ObservationResult) -> list[str]:
    """ObservationResult에서 제약 조건 목록 생성"""
    constraints: list[str] = []

    # 인력 제약
    if result.team_size is not None:
        constraints.append(f"[인력] 팀 {result.team_size}명")
    elif result.team_size_min is not None and result.team_size_max is not None:
        constraints.append(f"[인력] 팀 {result.team_size_min}~{result.team_size_max}명 (확정 필요)")

    # 일정 제약
    if result.deadline_days is not None:
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

    # 플랫폼 제약
    if result.platform:
        constraints.append(f"[플랫폼] {result.platform}")

    # 스택 제약
    if result.language_stack:
        constraints.append(f"[스택] {'/'.join(result.language_stack)}")

    # 금지 사항
    if result.forbidden:
        constraints.append(f"[금지] {', '.join(result.forbidden)} (운영)")

    # 운영제약 (텍스트에서 직접 추출)
    text_lower = result.raw_input.lower()
    operational = []

    if "wsl" in text_lower or "wsl2" in text_lower:
        operational.append("WSL2 개발환경")

    if "no internet" in text_lower or "인터넷 불가" in text_lower or "인터넷불가" in text_lower:
        operational.append("인터넷 불가")
    if "offline" in text_lower or "오프라인" in text_lower:
        if "offline update" in text_lower or "오프라인 업데이트" in text_lower:
            operational.append("오프라인 업데이트만 가능")
        elif "인터넷 불가" not in " ".join(operational):
            operational.append("오프라인 환경")

    if "security" in text_lower or "보안" in text_lower:
        operational.append("보안 정책 적용")
    if "compliance" in text_lower or "컴플라이언스" in text_lower:
        operational.append("컴플라이언스 요구")

    if operational:
        constraints.append(f"[운영제약] {', '.join(operational)}")

    return constraints
