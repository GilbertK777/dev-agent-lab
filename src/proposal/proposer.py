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


def propose(obs: ObservationResult, analysis: Analysis) -> Proposal:
    """
    관찰과 분석 결과를 바탕으로 추천을 생성합니다.

    Agent는 절대 최종 결정을 내리지 않습니다.
    항상 근거를 제시하고, 인간이 결정해야 함을 명확히 합니다.
    """
    # 추천 생성
    has_explicit_requirements = any(e.extractor == "requirements" for e in obs.extractions)

    if obs.ambiguity_score >= 50:
        recommendation = "입력의 모호성이 높습니다. 먼저 미확인 사항(Unknowns)을 명확히 하는 것을 추천합니다."
    elif not has_explicit_requirements:
        recommendation = "핵심 요구사항이 파악되지 않았습니다. 필수 기능(Must-have)을 먼저 정의해야 합니다."
    else:
        recommendation = "정의된 요구사항과 제약조건을 바탕으로 아키텍처 설계를 시작하는 것을 추천합니다."

    # 추천 근거 정리
    reasoning_parts = []
    if analysis.pros:
        summary_pros = ", ".join(analysis.pros[:2])
        reasoning_parts.append(f"긍정적 요인으로 '{summary_pros}' 등이 있습니다.")
    if analysis.cons:
        summary_cons = ", ".join(analysis.cons[:2])
        reasoning_parts.append(f"반면, '{summary_cons}' 등은 리스크 요인입니다.")

    reasoning = " ".join(reasoning_parts) if reasoning_parts else "추가 분석을 위해 더 많은 정보가 필요합니다."

    # 다음 고려사항
    next_considerations: list[str] = []
    if obs.unknowns:
        next_considerations.append("가장 먼저 미확인 사항(Unknowns)에 대한 답변을 찾아야 합니다.")
    if "유연하고 확장 가능한 아키텍처" in " ".join(analysis.cons):
        next_considerations.append("요구사항 변경에 대응하기 쉬운 모듈형 설계를 고려해 보세요.")
    if "예산 제약" in " ".join(analysis.cons):
        next_considerations.append("오픈소스 솔루션이나 관리형 서비스(Managed Service)를 활용하여 비용 효율성을 높이는 방안을 검토해 보세요.")

    next_considerations.append("팀과 함께 분석 결과를 리뷰하고, 아키텍처 설계 원칙을 수립하세요.")
    next_considerations.append("주요 기능에 대한 기술 검증(PoC)을 진행하여 리스크를 조기에 식별하세요.")

    unique_considerations = list(dict.fromkeys(next_considerations))

    return Proposal(
        recommendation=recommendation,
        reasoning=reasoning,
        human_decision_note=HUMAN_DECISION_STATEMENT,
        next_considerations=unique_considerations[:3],  # 상위 3개
    )
