"""
Budget Constraint Rule (예산 제약 규칙)

예산 제약이 감지되면:
- Cons에 예산 관련 리스크 추가
- Constraints에 예산 제약 추가
"""

from src.reasoning.rules.base import Rule, RuleContext


# 예산 제약 키워드
BUDGET_TIGHT_KEYWORDS = [
    "tight budget", "limited budget", "budget constraint",
    "예산 제약", "예산 부족", "비용 절감", "저예산", "tight"
]


class BudgetConstraintRule:
    """
    예산 제약 규칙

    입력 텍스트에서 예산 제약 신호를 감지하면:
    1. Cons에 예산 관련 리스크 2개 추가
    2. Constraints에 예산 제약 태그 추가 (중복 방지)
    """

    @property
    def name(self) -> str:
        return "budget_constraint"

    def applies(self, ctx: RuleContext) -> bool:
        """예산 제약 키워드가 있으면 적용"""
        text_lower = ctx.result.raw_input.lower()
        return any(kw in text_lower for kw in BUDGET_TIGHT_KEYWORDS)

    def apply(self, ctx: RuleContext) -> None:
        """예산 제약 관련 cons와 constraints 추가"""
        # Cons 추가
        ctx.cons.append("예산 제약으로 인해 범위 조정 또는 우선순위 재정립이 필요합니다.")
        ctx.cons.append("비용 효율적인 기술 선택이 중요합니다.")

        # Constraints 추가 (중복 방지)
        if not any("예산" in c for c in ctx.constraints):
            ctx.constraints.append("[예산] 제한적 (비용 효율성 중시)")
