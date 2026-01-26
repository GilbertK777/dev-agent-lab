"""
정책 테스트 (Policy Tests)

이 테스트는 "정답"이 아니라 "행동 규칙"을 검증합니다.
Agent가 반드시 지켜야 할 정책을 확인합니다.
"""

import sys
from pathlib import Path

# src 모듈을 import할 수 있도록 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.observation.observer import observe_v2, observe
from src.reasoning.reasoner import reason
from src.proposal.proposer import propose
from src.main import format_output_v2


class TestOutputStructurePolicy:
    """출력 구조 정책 테스트"""

    def test_output_contains_pros_section(self) -> None:
        """출력에 Pros(장점) 섹션이 포함되어야 합니다."""
        result = observe_v2("마이크로서비스 vs 모놀리스 어떤 것을 선택해야 할까요?")
        analysis = reason(result)
        proposal = propose(result, analysis)
        output = format_output_v2(result, analysis, proposal)

        assert "Pros" in output, "출력에 'Pros' 섹션이 포함되어야 합니다"

    def test_output_contains_cons_section(self) -> None:
        """출력에 Cons(단점) 섹션이 포함되어야 합니다."""
        result = observe_v2("마이크로서비스 vs 모놀리스 어떤 것을 선택해야 할까요?")
        analysis = reason(result)
        proposal = propose(result, analysis)
        output = format_output_v2(result, analysis, proposal)

        assert "Cons" in output, "출력에 'Cons' 섹션이 포함되어야 합니다"

    def test_output_contains_assumptions_section(self) -> None:
        """출력에 Assumptions(가정) 섹션이 포함되어야 합니다."""
        result = observe_v2("마이크로서비스 vs 모놀리스 어떤 것을 선택해야 할까요?")
        analysis = reason(result)
        proposal = propose(result, analysis)
        output = format_output_v2(result, analysis, proposal)

        assert "Assumptions" in output, "출력에 'Assumptions' 섹션이 포함되어야 합니다"

    def test_output_contains_constraints_section(self) -> None:
        """출력에 Constraints(제약) 섹션이 포함되어야 합니다."""
        result = observe_v2("마이크로서비스 vs 모놀리스 어떤 것을 선택해야 할까요?")
        analysis = reason(result)
        proposal = propose(result, analysis)
        output = format_output_v2(result, analysis, proposal)

        assert "Constraints" in output, "출력에 'Constraints' 섹션이 포함되어야 합니다"


class TestHumanDecisionPolicy:
    """인간 결정 정책 테스트"""

    def test_output_states_human_makes_final_decision(self) -> None:
        """출력에 '최종 결정은 인간이 한다'는 의미의 문장이 포함되어야 합니다."""
        result = observe_v2("어떤 아키텍처를 선택해야 할까요?")
        analysis = reason(result)
        proposal = propose(result, analysis)
        output = format_output_v2(result, analysis, proposal)

        # 인간이 결정한다는 표현이 포함되어 있는지 확인
        human_decision_keywords = ["최종 결정은 인간", "인간이 내려야", "사람이 결정"]
        has_human_decision_statement = any(
            keyword in output for keyword in human_decision_keywords
        )

        assert has_human_decision_statement, (
            "출력에 '최종 결정은 인간이 한다'는 의미의 문장이 포함되어야 합니다. "
            f"현재 출력에서 다음 키워드를 찾지 못했습니다: {human_decision_keywords}"
        )

    def test_proposal_always_includes_human_decision_note(self) -> None:
        """제안에는 항상 인간 결정 안내가 포함되어야 합니다."""
        result = observe_v2("테스트 입력")
        analysis = reason(result)
        proposal = propose(result, analysis)

        assert proposal.human_decision_note, "제안에 human_decision_note가 비어있으면 안 됩니다"
        assert "인간" in proposal.human_decision_note or "사람" in proposal.human_decision_note, (
            "human_decision_note에 인간/사람이 결정한다는 내용이 포함되어야 합니다"
        )


class TestObservationConstraintExtractionPolicy:
    """
    관찰 단계 제약 추출 정책 테스트

    NOTE: 이 테스트는 deprecated된 observe() 함수와 Observation 타입을 테스트합니다.
    하위 호환성 검증 용도로 유지합니다.
    """

    def test_observation_extracts_team_size_with_number(self) -> None:
        """팀 규모 정보가 인원수와 함께 제약 조건으로 추출되어야 합니다."""
        # deprecated observe() 사용 - 하위 호환성 테스트
        observation = observe("팀은 3명이고 출시까지는 2개월 정도 남았는데, 요구사항 변경이 많음")

        # 인력 관련 제약이 포함되어 있는지 확인 (숫자 3 포함)
        has_team_constraint = any(
            "인력" in constraint and "3" in constraint
            for constraint in observation.constraints
        )

        assert has_team_constraint, (
            f"Observation의 constraints에 인력(팀 규모) 관련 제약과 '3명'이 포함되어야 합니다. "
            f"현재 constraints: {observation.constraints}"
        )

    def test_observation_extracts_timeline_with_duration(self) -> None:
        """일정 정보가 기간과 함께 제약 조건으로 추출되어야 합니다."""
        # deprecated observe() 사용 - 하위 호환성 테스트
        observation = observe("팀은 3명이고 출시까지는 2개월 정도 남았는데, 요구사항 변경이 많음")

        # 일정 관련 제약이 포함되어 있는지 확인 (숫자 2와 개월 포함)
        has_timeline_constraint = any(
            "일정" in constraint and "2" in constraint and "개월" in constraint
            for constraint in observation.constraints
        )

        assert has_timeline_constraint, (
            f"Observation의 constraints에 일정 관련 제약과 '2개월'이 포함되어야 합니다. "
            f"현재 constraints: {observation.constraints}"
        )


class TestLowConfidenceWarningPolicy:
    """낮은 신뢰도 경고 정책 테스트"""

    def test_low_confidence_warning_in_assumptions(self) -> None:
        """신뢰도가 낮은 추출 결과가 있으면 Assumptions에 경고가 포함되어야 합니다."""
        # 낮은 신뢰도를 유발하는 입력 (모호한 일정 표현)
        result = observe_v2("프로젝트 기간은 대략 반년쯤? 팀은 아마 3명")
        analysis = reason(result)

        # 낮은 신뢰도 추출이 있는지 확인
        low_conf_extractions = [e for e in result.extractions if e.confidence < 0.7]

        if low_conf_extractions:
            # 경고 문구가 assumptions에 포함되어야 함
            has_warning = any("주의" in a and "신뢰도" in a for a in analysis.assumptions)
            assert has_warning, (
                f"낮은 신뢰도 추출이 있으면 assumptions에 경고가 포함되어야 합니다. "
                f"low_conf: {[e.extractor for e in low_conf_extractions]}, "
                f"assumptions: {analysis.assumptions}"
            )

    def test_analysis_has_warnings_field(self) -> None:
        """Analysis에 warnings 필드가 존재해야 합니다."""
        result = observe_v2("팀 3명, 6개월")
        analysis = reason(result)

        assert hasattr(analysis, "warnings"), "Analysis에 warnings 필드가 존재해야 합니다"
        assert isinstance(analysis.warnings, list), "warnings는 list 타입이어야 합니다"
