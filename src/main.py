"""
의사결정 지원 Agent CLI

사용법:
    python -m src.main

표준 입력에서 여러 줄의 텍스트를 EOF(Ctrl+D)까지 읽고,
관찰 → 판단 → 제안 순서로 처리한 결과를 출력합니다.
"""

import sys

from src.observation.observer import Observation, observe
from src.reasoning.reasoner import Analysis, reason
from src.proposal.proposer import Proposal, propose


def format_output(observation: Observation, analysis: Analysis, proposal: Proposal) -> str:
    """분석 결과를 사람이 읽기 쉬운 형식으로 포맷합니다."""
    lines: list[str] = []

    # 구분선
    separator = "=" * 60

    # 헤더
    lines.append(separator)
    lines.append("🔍 의사결정 지원 Agent 분석 결과")
    lines.append(separator)
    lines.append("")

    # 1. 관찰 결과
    lines.append("## 관찰 (Observation)")
    lines.append("")
    lines.append("### 요구사항")
    for req in observation.requirements:
        lines.append(f"  - {req}")
    if observation.constraints:
        lines.append("")
        lines.append("### 제약 조건")
        for con in observation.constraints:
            lines.append(f"  - {con}")
    lines.append("")

    # 2. 분석 결과 (트레이드오프)
    lines.append("## 분석 (Analysis)")
    lines.append("")

    lines.append("### Pros (장점)")
    for pro in analysis.pros:
        lines.append(f"  ✓ {pro}")
    lines.append("")

    lines.append("### Cons (단점)")
    for con in analysis.cons:
        lines.append(f"  ✗ {con}")
    lines.append("")

    lines.append("### Assumptions (가정)")
    for assumption in analysis.assumptions:
        lines.append(f"  → {assumption}")
    lines.append("")

    lines.append("### Constraints (제약)")
    for constraint in analysis.constraints:
        lines.append(f"  ⚠ {constraint}")
    lines.append("")

    # 3. 제안
    lines.append("## 제안 (Proposal)")
    lines.append("")
    lines.append(f"**추천:** {proposal.recommendation}")
    lines.append("")
    lines.append(f"**근거:** {proposal.reasoning}")
    lines.append("")

    lines.append("### 다음 고려사항")
    for consideration in proposal.next_considerations:
        lines.append(f"  • {consideration}")
    lines.append("")

    # 4. 인간 결정 안내 (핵심)
    lines.append(separator)
    lines.append(f"⚡ {proposal.human_decision_note}")
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

    # 관찰 → 판단 → 제안
    observation = observe(user_input)
    analysis = reason(observation)
    proposal = propose(observation, analysis)

    # 결과 출력
    print()
    print(format_output(observation, analysis, proposal))


if __name__ == "__main__":
    main()
