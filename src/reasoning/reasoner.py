"""
판단(Reasoning) 모듈

관찰 결과를 바탕으로 구조화된 트레이드오프 분석을 수행합니다.
- Pros (장점)
- Cons (단점)
- Assumptions (가정)
- Constraints (제약)
"""

from dataclasses import dataclass, field

from src.observation.observer import Observation


@dataclass
class Analysis:
    """트레이드오프 분석 결과"""

    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)


def reason(observation: Observation) -> Analysis:
    """
    관찰 결과를 분석하여 트레이드오프 구조를 생성합니다.

    현재는 템플릿 기반의 분석을 수행합니다.
    실제 Agent에서는 LLM이나 규칙 엔진을 활용할 수 있습니다.
    """
    pros: list[str] = []
    cons: list[str] = []
    assumptions: list[str] = []
    constraints: list[str] = []

    # 관찰된 제약 조건을 분석 제약에 포함
    constraints.extend(observation.constraints)

    # 요구사항이 있으면 기본 분석 수행
    if observation.requirements:
        # 장점: 요구사항을 충족하면 얻을 수 있는 이점
        pros.append("요구사항이 명확하게 정의되어 있어 목표 설정이 가능합니다.")

        # 단점: 잠재적 위험이나 비용
        cons.append("추가적인 맥락 없이는 최적의 선택을 판단하기 어렵습니다.")

        # 가정: 분석의 전제 조건
        assumptions.append("현재 제공된 정보가 의사결정에 충분하다고 가정합니다.")

    # 미확인 정보가 있으면 추가 분석
    if observation.unknowns:
        cons.append("미확인 정보가 있어 추가 확인이 필요합니다.")
        assumptions.append("미확인 정보는 추후 확인될 것으로 가정합니다.")

    # 제약이 없으면 기본 제약 추가
    if not constraints:
        constraints.append("현재 명시된 기술적/비즈니스적 제약이 없습니다.")

    return Analysis(
        pros=pros,
        cons=cons,
        assumptions=assumptions,
        constraints=constraints,
    )
