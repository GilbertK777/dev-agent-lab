"""
Team Size Rule (팀 규모 규칙)

팀 규모가 미정이거나 범위로 주어진 경우:
- 미정: 역할 분담/일정 추정 불가 경고
- 범위: 범위 기반 계획 수립 필요 안내
"""

from src.reasoning.rules.base import RuleContext


class TeamSizeRule:
    """
    팀 규모 규칙

    케이스 1 - 미정: team_size=None AND team_size_min=None
    케이스 2 - 범위: team_size_min != team_size_max

    단일값 확정(team_size 존재 OR min==max)이면 적용 안 함
    """

    @property
    def name(self) -> str:
        return "team_size"

    def applies(self, ctx: RuleContext) -> bool:
        """팀 규모가 미정이거나 범위일 때 적용"""
        result = ctx.result

        # 케이스 1: 완전 미정
        if result.team_size is None and result.team_size_min is None:
            return True

        # 케이스 2: 범위로 주어짐 (min != max)
        if (
            result.team_size_min is not None
            and result.team_size_max is not None
            and result.team_size_min != result.team_size_max
        ):
            return True

        return False

    def apply(self, ctx: RuleContext) -> None:
        """팀 규모 관련 cons와 constraints 추가"""
        result = ctx.result

        # 케이스 1: 완전 미정
        if result.team_size is None and result.team_size_min is None:
            ctx.cons.append("팀 규모 미정으로 역할 분담/일정 추정 불가")
            if not any("[인력]" in c and "미정" in c for c in ctx.constraints):
                ctx.constraints.append("[인력] 미정 (확정 필요)")
            return

        # 케이스 2: 범위로 주어짐
        if (
            result.team_size_min is not None
            and result.team_size_max is not None
            and result.team_size_min != result.team_size_max
        ):
            ctx.cons.append("팀 규모가 범위로 주어져 범위 기반 계획 수립 필요")
            constraint = f"[인력] {result.team_size_min}~{result.team_size_max}명 (범위 확인)"
            if not any("[인력]" in c for c in ctx.constraints):
                ctx.constraints.append(constraint)
