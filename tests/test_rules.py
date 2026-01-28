"""
규칙 테스트 (Rule Tests)

TDD: 이 테스트들은 규칙 구현 전에 작성되었습니다.
새로운 규칙들이 구현되면 이 테스트들이 통과해야 합니다.

테스트 대상 규칙:
- TeamSizeRule: 팀 규모 미정 또는 범위로 주어진 경우
- DeadlineRule: 일정 미정 또는 촉박한 경우
- VolatilityRule: 요구사항 변동성이 높은 경우
"""

import sys
from pathlib import Path

import pytest

# src 모듈을 import할 수 있도록 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.observation.schema import ObservationResult
from src.reasoning.rules.base import RuleContext

# pytest.importorskip: 모듈 미구현 시 해당 테스트 자동 skip
team_size_rule = pytest.importorskip("src.reasoning.rules.team_size_rule")
TeamSizeRule = team_size_rule.TeamSizeRule

deadline_rule = pytest.importorskip("src.reasoning.rules.deadline_rule")
DeadlineRule = deadline_rule.DeadlineRule

volatility_rule = pytest.importorskip("src.reasoning.rules.volatility_rule")
VolatilityRule = volatility_rule.VolatilityRule


class TestTeamSizeRule:
    """팀 규모 규칙 테스트"""

    def test_applies_when_team_size_unknown(self) -> None:
        """팀 규모가 미정(None)일 때 규칙이 적용되어야 합니다."""
        result = ObservationResult(
            raw_input="프로젝트 진행 예정",
            team_size=None,
            team_size_min=None,
            team_size_max=None,
        )
        ctx = RuleContext(result=result)
        rule = TeamSizeRule()

        assert rule.applies(ctx) is True, "팀 규모가 None일 때 applies()는 True여야 합니다"

    def test_applies_when_team_size_range(self) -> None:
        """팀 규모가 범위로 주어졌을 때 규칙이 적용되어야 합니다."""
        result = ObservationResult(
            raw_input="팀은 3~5명 정도",
            team_size=None,
            team_size_min=3,
            team_size_max=5,
        )
        ctx = RuleContext(result=result)
        rule = TeamSizeRule()

        assert rule.applies(ctx) is True, "팀 규모가 범위일 때 applies()는 True여야 합니다"

    def test_not_applies_when_team_size_fixed(self) -> None:
        """팀 규모가 확정되었을 때 규칙이 적용되지 않아야 합니다."""
        result = ObservationResult(
            raw_input="팀은 4명입니다",
            team_size=4,
            team_size_min=None,
            team_size_max=None,
        )
        ctx = RuleContext(result=result)
        rule = TeamSizeRule()

        assert rule.applies(ctx) is False, "팀 규모가 확정되면 applies()는 False여야 합니다"

    def test_not_applies_when_range_equals(self) -> None:
        """팀 규모 범위가 동일할 때(min=max) 규칙이 적용되지 않아야 합니다."""
        result = ObservationResult(
            raw_input="팀은 4명입니다",
            team_size=None,
            team_size_min=4,
            team_size_max=4,
        )
        ctx = RuleContext(result=result)
        rule = TeamSizeRule()

        assert rule.applies(ctx) is False, "팀 규모 min=max일 때 applies()는 False여야 합니다"

    def test_apply_adds_cons_and_constraint_for_unknown(self) -> None:
        """팀 규모 미정 시 cons와 constraint가 추가되어야 합니다."""
        result = ObservationResult(
            raw_input="프로젝트 진행 예정",
            team_size=None,
            team_size_min=None,
            team_size_max=None,
        )
        ctx = RuleContext(result=result)
        rule = TeamSizeRule()

        rule.apply(ctx)

        # cons 확인
        assert any("팀 규모 미정" in c for c in ctx.cons), (
            f"팀 규모 미정일 때 cons에 관련 내용이 포함되어야 합니다. 현재 cons: {ctx.cons}"
        )
        assert any("역할 분담" in c or "일정 추정" in c for c in ctx.cons), (
            f"팀 규모 미정일 때 cons에 역할 분담/일정 추정 불가 내용이 포함되어야 합니다. 현재 cons: {ctx.cons}"
        )

        # constraint 확인
        assert any("[인력]" in c and "미정" in c for c in ctx.constraints), (
            f"팀 규모 미정일 때 constraints에 '[인력] 미정' 관련 내용이 포함되어야 합니다. "
            f"현재 constraints: {ctx.constraints}"
        )

    def test_apply_adds_range_message_for_range(self) -> None:
        """팀 규모가 범위일 때 범위 관련 메시지가 추가되어야 합니다."""
        result = ObservationResult(
            raw_input="팀은 3~5명 정도",
            team_size=None,
            team_size_min=3,
            team_size_max=5,
        )
        ctx = RuleContext(result=result)
        rule = TeamSizeRule()

        rule.apply(ctx)

        # cons 확인
        assert any("범위" in c for c in ctx.cons), (
            f"팀 규모 범위일 때 cons에 범위 관련 내용이 포함되어야 합니다. 현재 cons: {ctx.cons}"
        )

        # constraint 확인: "[인력] 3~5명" 형태
        assert any("[인력]" in c and "3" in c and "5" in c for c in ctx.constraints), (
            f"팀 규모 범위일 때 constraints에 '[인력] 3~5명' 관련 내용이 포함되어야 합니다. "
            f"현재 constraints: {ctx.constraints}"
        )


class TestDeadlineRule:
    """일정 규칙 테스트"""

    def test_applies_when_deadline_unknown(self) -> None:
        """일정이 미정(None)일 때 규칙이 적용되어야 합니다."""
        result = ObservationResult(
            raw_input="프로젝트 진행 예정",
            deadline_days=None,
        )
        ctx = RuleContext(result=result)
        rule = DeadlineRule()

        assert rule.applies(ctx) is True, "일정이 None일 때 applies()는 True여야 합니다"

    def test_applies_when_deadline_tight(self) -> None:
        """일정이 촉박할 때(10일) 규칙이 적용되어야 합니다."""
        result = ObservationResult(
            raw_input="10일 내 완료 필요",
            deadline_days=10,
        )
        ctx = RuleContext(result=result)
        rule = DeadlineRule()

        assert rule.applies(ctx) is True, "일정이 촉박할 때 applies()는 True여야 합니다"

    def test_not_applies_when_deadline_ok(self) -> None:
        """일정이 여유로울 때(30일) 규칙이 적용되지 않아야 합니다."""
        result = ObservationResult(
            raw_input="한 달 정도 여유 있습니다",
            deadline_days=30,
        )
        ctx = RuleContext(result=result)
        rule = DeadlineRule()

        assert rule.applies(ctx) is False, "일정이 여유로울 때 applies()는 False여야 합니다"

    def test_apply_adds_cons_and_constraint_for_unknown(self) -> None:
        """일정 미정 시 cons와 constraint가 추가되어야 합니다."""
        result = ObservationResult(
            raw_input="프로젝트 진행 예정",
            deadline_days=None,
        )
        ctx = RuleContext(result=result)
        rule = DeadlineRule()

        rule.apply(ctx)

        # cons 확인
        assert any("일정 미정" in c for c in ctx.cons), (
            f"일정 미정일 때 cons에 관련 내용이 포함되어야 합니다. 현재 cons: {ctx.cons}"
        )

        # constraint 확인
        assert any("[일정]" in c and "미정" in c for c in ctx.constraints), (
            f"일정 미정일 때 constraints에 '[일정] 미정' 관련 내용이 포함되어야 합니다. "
            f"현재 constraints: {ctx.constraints}"
        )

    def test_apply_adds_cons_and_constraint_for_tight(self) -> None:
        """일정이 촉박할 때 cons와 constraint가 추가되어야 합니다."""
        result = ObservationResult(
            raw_input="10일 내 완료 필요",
            deadline_days=10,
        )
        ctx = RuleContext(result=result)
        rule = DeadlineRule()

        rule.apply(ctx)

        # cons 확인
        assert any("촉박" in c for c in ctx.cons), (
            f"일정이 촉박할 때 cons에 촉박 관련 내용이 포함되어야 합니다. 현재 cons: {ctx.cons}"
        )

        # constraint 확인
        assert any("[일정]" in c and "촉박" in c for c in ctx.constraints), (
            f"일정이 촉박할 때 constraints에 '[일정] ... (촉박)' 관련 내용이 포함되어야 합니다. "
            f"현재 constraints: {ctx.constraints}"
        )


class TestVolatilityRule:
    """요구사항 변동성 규칙 테스트"""

    def test_applies_when_high_volatility(self) -> None:
        """변동성 점수가 높을 때(60) 규칙이 적용되어야 합니다."""
        result = ObservationResult(
            raw_input="프로젝트 진행 예정",
            scope_volatility_score=60,
        )
        ctx = RuleContext(result=result)
        rule = VolatilityRule()

        assert rule.applies(ctx) is True, "변동성 점수가 높을 때 applies()는 True여야 합니다"

    def test_applies_when_keywords(self) -> None:
        """변동성 관련 키워드가 있을 때 규칙이 적용되어야 합니다."""
        result = ObservationResult(
            raw_input="requirements are flexible and may change",
            scope_volatility_score=0,
        )
        ctx = RuleContext(result=result)
        rule = VolatilityRule()

        assert rule.applies(ctx) is True, "변동성 키워드가 있을 때 applies()는 True여야 합니다"

    def test_not_applies_when_low_volatility(self) -> None:
        """변동성이 낮고 키워드가 없을 때 규칙이 적용되지 않아야 합니다."""
        result = ObservationResult(
            raw_input="프로젝트 진행 예정",
            scope_volatility_score=30,
        )
        ctx = RuleContext(result=result)
        rule = VolatilityRule()

        assert rule.applies(ctx) is False, "변동성이 낮을 때 applies()는 False여야 합니다"

    def test_apply_adds_cons_and_assumptions(self) -> None:
        """변동성이 높을 때 cons와 assumptions가 추가되어야 합니다."""
        result = ObservationResult(
            raw_input="요구사항이 자주 변경될 수 있습니다",
            scope_volatility_score=60,
        )
        ctx = RuleContext(result=result)
        rule = VolatilityRule()

        rule.apply(ctx)

        # cons 확인: 변경 가능성, 재작업 리스크
        assert any("요구사항 변경" in c or "변경 가능성" in c for c in ctx.cons), (
            f"변동성이 높을 때 cons에 요구사항 변경 관련 내용이 포함되어야 합니다. "
            f"현재 cons: {ctx.cons}"
        )
        assert any("재작업" in c or "리스크" in c for c in ctx.cons), (
            f"변동성이 높을 때 cons에 재작업 리스크 관련 내용이 포함되어야 합니다. "
            f"현재 cons: {ctx.cons}"
        )

        # assumptions 확인: 아키텍처 유연성
        assert any("아키텍처" in a and "유연성" in a for a in ctx.assumptions), (
            f"변동성이 높을 때 assumptions에 아키텍처 유연성 관련 내용이 포함되어야 합니다. "
            f"현재 assumptions: {ctx.assumptions}"
        )
