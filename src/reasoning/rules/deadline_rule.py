"""
Deadline Rule (일정 규칙)

일정이 미정이거나 촉박한 경우:
- 미정: MVP 범위/마일스톤 설정 불가 경고
- 촉박(<14일): 품질/범위 트레이드오프 필요 안내
"""

from src.reasoning.rules.base import RuleContext


# 촉박 기준: 14일 미만
TIGHT_DEADLINE_DAYS = 14


class DeadlineRule:
    """
    일정 규칙

    케이스 1 - 미정: deadline_days=None
    케이스 2 - 촉박: deadline_days < 14

    14일 이상 확정 일정이면 적용 안 함
    """

    @property
    def name(self) -> str:
        return "deadline"

    def applies(self, ctx: RuleContext) -> bool:
        """일정이 미정이거나 촉박할 때 적용"""
        deadline = ctx.result.deadline_days

        # 케이스 1: 미정
        if deadline is None:
            return True

        # 케이스 2: 촉박
        if deadline < TIGHT_DEADLINE_DAYS:
            return True

        return False

    def apply(self, ctx: RuleContext) -> None:
        """일정 관련 cons와 constraints 추가"""
        deadline = ctx.result.deadline_days

        # 케이스 1: 미정
        if deadline is None:
            ctx.cons.append("일정 미정으로 MVP 범위 및 마일스톤 설정 불가")
            if not any("[일정]" in c and "미정" in c for c in ctx.constraints):
                ctx.constraints.append("[일정] 미정 (확정 필요)")
            return

        # 케이스 2: 촉박
        if deadline < TIGHT_DEADLINE_DAYS:
            ctx.cons.append(f"촉박한 일정({deadline}일)으로 품질/범위 트레이드오프 필요")
            constraint = f"[일정] {deadline}일 (촉박)"
            if not any("[일정]" in c for c in ctx.constraints):
                ctx.constraints.append(constraint)
