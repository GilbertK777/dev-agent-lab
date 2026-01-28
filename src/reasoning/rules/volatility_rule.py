"""
Volatility Rule (변동성 규칙)

요구사항 변동성이 높은 경우:
- scope_volatility_score >= 50 또는 키워드 탐지
- 재작업 리스크 경고 + 아키텍처 유연성 가정 추가
"""

from src.reasoning.rules.base import RuleContext


# 변동성 임계값
VOLATILITY_THRESHOLD = 50

# 변동성 키워드
VOLATILITY_KEYWORDS = [
    "evolving", "flexible", "may change", "subject to change",
    "변경 가능", "유동적", "변할 수 있", "바뀔 수 있",
]


class VolatilityRule:
    """
    변동성 규칙

    적용 조건:
    1. scope_volatility_score >= 50
    2. 변동성 키워드 탐지 (score가 0인 경우 fallback)
    """

    @property
    def name(self) -> str:
        return "volatility"

    def applies(self, ctx: RuleContext) -> bool:
        """변동성이 높거나 키워드가 있을 때 적용"""
        result = ctx.result

        # 케이스 1: 점수 기반
        if result.scope_volatility_score >= VOLATILITY_THRESHOLD:
            return True

        # 케이스 2: 키워드 기반 (fallback)
        text_lower = result.raw_input.lower()
        if any(kw in text_lower for kw in VOLATILITY_KEYWORDS):
            return True

        return False

    def apply(self, ctx: RuleContext) -> None:
        """변동성 관련 cons와 assumptions 추가"""
        # Cons 추가
        ctx.cons.append("요구사항 변경 가능성 높아 재작업 리스크 존재")

        # Assumptions 추가 (중복 방지)
        assumption = "아키텍처 유연성 확보 필요"
        if not any("아키텍처" in a and "유연성" in a for a in ctx.assumptions):
            ctx.assumptions.append(assumption)
