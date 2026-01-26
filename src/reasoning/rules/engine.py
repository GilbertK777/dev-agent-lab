"""
Rule Engine Lite

여러 규칙을 순서대로 적용하는 간단한 엔진입니다.
"""

from src.reasoning.rules.base import Rule, RuleContext


class RuleEngine:
    """
    규칙 엔진

    등록된 규칙들을 순서대로 실행합니다.
    각 규칙은 applies()가 True를 반환할 때만 apply()됩니다.
    """

    def __init__(self) -> None:
        self._rules: list[Rule] = []

    def register(self, rule: Rule) -> "RuleEngine":
        """
        규칙 등록

        Returns:
            self (체이닝 가능)
        """
        self._rules.append(rule)
        return self

    def run(self, ctx: RuleContext) -> RuleContext:
        """
        모든 규칙을 순서대로 실행

        Args:
            ctx: 규칙 실행 컨텍스트

        Returns:
            수정된 컨텍스트
        """
        for rule in self._rules:
            if rule.applies(ctx):
                rule.apply(ctx)

        return ctx

    @property
    def rules(self) -> list[Rule]:
        """등록된 규칙 목록 (읽기 전용)"""
        return list(self._rules)
