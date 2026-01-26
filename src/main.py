"""
의사결정 지원 Agent CLI

사용법:
    python -m src.main

표준 입력에서 여러 줄의 텍스트를 EOF(Ctrl+D)까지 읽고,
관찰 → 판단 → 제안 순서로 처리한 결과를 출력합니다.
"""

import sys

from src.observation.observer import Observation, observe, observe_v2
from src.observation.schema import ObservationResult
from src.reasoning.reasoner import Analysis, reason
from src.proposal.proposer import Proposal, propose


def format_output(observation: Observation, analysis: Analysis, proposal: Proposal) -> str:
    """
    [Legacy] 분석 결과를 사람이 읽기 쉬운 형식으로 포맷합니다.

    하위 호환성을 위해 유지. 내부적으로 v2 결과를 사용.
    """
    # v2 결과 생성
    result = observe_v2(observation.raw_input)
    return format_output_v2(result, analysis, proposal)


def format_deadline(days: int) -> str:
    """일수를 사람이 읽기 쉬운 형식으로 변환"""
    if days >= 365:
        years = days // 365
        months = (days % 365) // 30
        if months > 0:
            return f"{years}년 {months}개월 (≈ {days}일)"
        else:
            return f"{years}년 (≈ {days}일)"
    elif days >= 30:
        months = days // 30
        return f"{months}개월 (≈ {days}일)"
    elif days >= 7:
        weeks = days // 7
        return f"{weeks}주 (≈ {days}일)"
    else:
        return f"{days}일"


def format_team_size(result: ObservationResult) -> str:
    """팀 인원을 형식화"""
    if result.team_size is not None:
        return f"팀 {result.team_size}명"
    elif result.team_size_min is not None and result.team_size_max is not None:
        return f"팀 {result.team_size_min}~{result.team_size_max}명 (확정 필요)"
    else:
        return "미정"


def format_output_v2(
    result: ObservationResult,
    analysis: Analysis,
    proposal: Proposal
) -> str:
    """분석 결과를 사람이 읽기 쉬운 형식으로 포맷합니다. (v2)"""
    lines: list[str] = []

    # 구분선
    separator = "=" * 60

    # 헤더
    lines.append(separator)
    lines.append("의사결정 지원 Agent 분석 결과")
    lines.append(separator)
    lines.append("")

    # 1. 정량 데이터 (v2 신규)
    lines.append("## 정량 분석 (Quantified Data)")
    lines.append("")

    # 일정
    if result.deadline_days is not None:
        lines.append(f"  - 일정: {format_deadline(result.deadline_days)}")
    else:
        lines.append("  - 일정: 미정")

    # 팀 인원
    lines.append(f"  - 인력: {format_team_size(result)}")

    # 모호성 점수
    if result.ambiguity_score >= 60:
        ambiguity_desc = "높음 (명확화 필요)"
    elif result.ambiguity_score >= 30:
        ambiguity_desc = "중간"
    else:
        ambiguity_desc = "낮음 (명확함)"
    lines.append(f"  - 모호성 점수: {result.ambiguity_score}/100 ({ambiguity_desc})")

    lines.append("")

    # 2. 미확인 사항 (unknowns)
    if result.unknowns:
        lines.append("## 미확인 사항 (Unknowns)")
        lines.append("")
        for i, unknown in enumerate(result.unknowns, 1):
            lines.append(f"  {i}. {unknown.question}")
            lines.append(f"     이유: {unknown.reason}")
        lines.append("")

    # 3. 요구사항 (간략화)
    lines.append("## 요구사항 요약")
    lines.append("")
    for req in result.must_have[:5]:  # 최대 5개
        lines.append(f"  - {req}")
    if len(result.must_have) > 5:
        lines.append(f"  ... 외 {len(result.must_have) - 5}개")
    lines.append("")

    # 4. 분석 결과 (트레이드오프)
    lines.append("## 분석 (Analysis)")
    lines.append("")

    lines.append("### Pros (장점)")
    for pro in analysis.pros:
        lines.append(f"  + {pro}")
    lines.append("")

    lines.append("### Cons (단점)")
    for con in analysis.cons:
        lines.append(f"  - {con}")
    lines.append("")

    lines.append("### Assumptions (가정)")
    for assumption in analysis.assumptions:
        lines.append(f"  > {assumption}")
    lines.append("")

    lines.append("### Constraints (제약)")
    for constraint in analysis.constraints:
        lines.append(f"  ! {constraint}")
    lines.append("")

    # 5. 제안
    lines.append("## 제안 (Proposal)")
    lines.append("")
    lines.append(f"추천: {proposal.recommendation}")
    lines.append("")
    lines.append(f"근거: {proposal.reasoning}")
    lines.append("")

    lines.append("### 다음 고려사항")
    for consideration in proposal.next_considerations:
        lines.append(f"  * {consideration}")
    lines.append("")

    # 6. 인간 결정 안내 (핵심)
    lines.append(separator)
    lines.append(f">> {proposal.human_decision_note}")
    lines.append(separator)

    return "\n".join(lines)


def main() -> None:
    """CLI 진입점"""
    print("의사결정 지원 Agent")
    print("질문이나 상황을 입력하세요. (입력 완료: Ctrl+D)")
    print("-" * 40)

    # 표준 입력에서 EOF까지 읽기
    user_input = sys.stdin.read()

    if not user_input.strip():
        print("입력이 없습니다. 분석할 내용을 입력해 주세요.")
        return

    # v2 파이프라인 사용
    result = observe_v2(user_input)

    # Legacy observe()도 호출 (Reasoner/Proposer 연동용)
    observation = observe(user_input)
    analysis = reason(observation)
    proposal = propose(observation, analysis)

    # 결과 출력 (v2 포맷)
    print()
    print(format_output_v2(result, analysis, proposal))


if __name__ == "__main__":
    main()
