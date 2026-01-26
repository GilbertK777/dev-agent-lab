"""
E2E 테스트: 전체 파이프라인 통합 검증
"""

import json
from pathlib import Path

import pytest

from src.observation.observer import observe_v2
from src.reasoning.reasoner import reason
from src.proposal.proposer import propose

# 테스트 데이터 로드
TEST_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "test_inputs.json"
with open(TEST_FIXTURE_PATH, "r", encoding="utf-8") as f:
    test_cases = json.load(f)["test_cases"]

# test_1: 명확한 케이스
clear_case_input = next(c["input"] for c in test_cases if c["id"] == "test_1")

# test_2: 모호한 케이스
ambiguous_case_input = next(c["input"] for c in test_cases if c["id"] == "test_2")


def test_pipeline_full_run_does_not_raise_error():
    """
    전체 파이프라인이 어떤 입력에 대해서도 예외를 발생시키지 않고 실행되는지 확인
    """
    for case in test_cases:
        # 1. Observe
        observation_result = observe_v2(case["input"])
        assert observation_result is not None

        # 2. Reason
        analysis_result = reason(observation_result)
        assert analysis_result is not None

        # 3. Propose
        proposal_result = propose(observation_result, analysis_result)
        assert proposal_result is not None


def test_pipeline_clear_case():
    """
    [E2E] test_1 (명확한 입력)에 대한 파이프라인 결과 검증
    """
    # 1. Observe
    obs = observe_v2(clear_case_input)
    assert obs.ambiguity_score < 30  # 모호성 점수가 낮아야 함
    assert not obs.unknowns  # 미확인 정보가 없어야 함

    # 2. Reason
    analysis = reason(obs)
    assert "요구사항이 명확" in " ".join(analysis.pros)
    assert "팀 규모가 확정" in " ".join(analysis.pros)

    # 3. Propose
    proposal = propose(obs, analysis)
    assert "설계를 시작" in proposal.recommendation


def test_pipeline_ambiguous_case():
    """
    [E2E] test_2 (모호한 입력)에 대한 파이프라인 결과 검증
    """
    # 1. Observe
    obs = observe_v2(ambiguous_case_input)
    assert obs.ambiguity_score > 30  # 모호성 점수가 높아야 함
    assert len(obs.unknowns) > 0  # 미확인 정보가 있어야 함

    # 2. Reason
    analysis = reason(obs)
    assert "불확실성" in " ".join(analysis.cons) or "리스크" in " ".join(analysis.cons)
    assert "팀 규모가 확정되지 않아" in " ".join(analysis.cons)

    # 3. Propose
    proposal = propose(obs, analysis)
    assert "핵심 요구사항" in proposal.recommendation and "정의해야" in proposal.recommendation
