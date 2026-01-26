"""
Rule 인터페이스 정의

모든 규칙은 이 Protocol을 따라야 합니다.
"""

from dataclasses import dataclass, field
from typing import Protocol

from src.observation.schema import ObservationResult


@dataclass
class RuleContext:
    """
    규칙 실행 컨텍스트

    규칙이 읽고 쓸 수 있는 공유 상태입니다.
    각 규칙은 이 컨텍스트를 수정하여 결과를 누적합니다.
    """
    result: ObservationResult
    ambiguity_level: str = "LOW"  # HIGH / MEDIUM / LOW

    # 분석 결과 (규칙들이 채워감)
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)


class Rule(Protocol):
    """
    규칙 인터페이스 (Protocol)

    모든 규칙은 다음을 구현해야 합니다:
    - name: 규칙 이름 (디버깅/로깅용)
    - applies(): 이 규칙이 적용되는지 판단
    - apply(): 규칙을 적용하여 컨텍스트 수정
    """

    @property
    def name(self) -> str:
        """규칙 이름"""
        ...

    def applies(self, ctx: RuleContext) -> bool:
        """
        이 규칙이 현재 컨텍스트에 적용되는지 판단

        Returns:
            True면 apply()가 호출됨
        """
        ...

    def apply(self, ctx: RuleContext) -> None:
        """
        규칙을 적용하여 컨텍스트를 수정

        ctx의 pros, cons, assumptions, constraints를 직접 수정합니다.
        """
        ...
