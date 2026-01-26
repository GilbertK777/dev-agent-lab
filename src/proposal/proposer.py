"""
제안(Proposal) 모듈

분석 결과를 바탕으로 추천을 생성합니다.
- 근거가 명확한 추천 제시
- 최종 결정은 인간이 한다는 점을 명시
- 다음에 고려할 사항 제안
"""

from dataclasses import dataclass, field

from src.observation.schema import ObservationResult
from src.reasoning.reasoner import Analysis


@dataclass
class Proposal:
    """제안 결과"""

    recommendation: str
    reasoning: str
    human_decision_note: str
    next_considerations: list[str] = field(default_factory=list)


# 핵심 원칙: 최종 결정은 인간의 몫
HUMAN_DECISION_STATEMENT = (
    "이 추천은 참고용입니다. 최종 결정은 인간이 내려야 하며, "
    "팀의 상황과 맥락을 고려하여 판단해 주세요."
)


def propose(result: ObservationResult, analysis: Analysis) -> Proposal:
    """
    관찰과 분석 결과를 바탕으로 추천을 생성합니다.

    Agent는 절대 최종 결정을 내리지 않습니다.
    항상 근거를 제시하고, 인간이 결정해야 함을 명확히 합니다.
    """
    # 추천 생성
    if result.must_have:
        recommendation = "제시된 요구사항을 바탕으로 검토를 진행하시기 바랍니다."
    else:
        recommendation = "추가 정보가 필요합니다. 요구사항을 더 구체적으로 설명해 주세요."

    # 추천 근거 정리
    reasoning_parts = []
    if analysis.pros:
        reasoning_parts.append(f"장점: {', '.join(analysis.pros)}")
    if analysis.cons:
        reasoning_parts.append(f"단점: {', '.join(analysis.cons)}")
    reasoning = " | ".join(reasoning_parts) if reasoning_parts else "분석할 정보가 부족합니다."

    # 다음 고려사항
    next_considerations: list[str] = []

    # 미확인 정보를 다음 고려사항에 포함 (Unknown 객체의 question 사용)
    for unknown in result.unknowns:
        next_considerations.append(f"확인 필요: [미확인] {unknown.question}")

    # 기본 다음 단계 제안
    next_considerations.append("팀과 함께 트레이드오프를 논의해 보세요.")
    next_considerations.append("프로토타입이나 PoC로 가설을 검증하는 것을 고려해 보세요.")

    return Proposal(
        recommendation=recommendation,
        reasoning=reasoning,
        human_decision_note=HUMAN_DECISION_STATEMENT,
        next_considerations=next_considerations,
    )
