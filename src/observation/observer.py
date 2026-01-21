"""
관찰(Observation) 모듈

사용자 입력에서 핵심 정보를 추출합니다.
- 핵심 요구사항
- 명시된 제약 조건
- 불명확하거나 추가 질문이 필요한 부분
"""

from dataclasses import dataclass, field


@dataclass
class Observation:
    """사용자 입력에서 추출한 관찰 결과"""

    raw_input: str
    requirements: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    unclear_points: list[str] = field(default_factory=list)


def observe(user_input: str) -> Observation:
    """
    사용자 입력을 분석하여 구조화된 관찰 결과를 반환합니다.

    현재는 간단한 키워드 기반 추출을 수행합니다.
    실제 Agent에서는 더 정교한 분석이 필요할 수 있습니다.
    """
    lines = user_input.strip().split('\n')

    requirements: list[str] = []
    constraints: list[str] = []
    unclear_points: list[str] = []

    # 키워드 기반 분류
    constraint_keywords = ['must', 'cannot', 'should not', 'required', '필수', '제약', '금지', '안 됨', '불가']
    question_keywords = ['?', '어떻게', '무엇', '왜', '확실하지', '불명확', '모르', 'unclear', 'unsure']

    for line in lines:
        line = line.strip()
        if not line:
            continue

        lower_line = line.lower()

        # 제약 조건 감지
        if any(keyword in lower_line for keyword in constraint_keywords):
            constraints.append(line)
        # 불명확한 부분 감지
        elif any(keyword in lower_line for keyword in question_keywords):
            unclear_points.append(line)
        # 나머지는 요구사항으로 분류
        else:
            requirements.append(line)

    # 입력이 있지만 분류된 내용이 없으면 전체를 요구사항으로 간주
    if user_input.strip() and not requirements and not constraints:
        requirements.append(user_input.strip())

    # 불명확한 점이 없어도, 맥락이 부족하면 기본 질문 추가
    if not unclear_points and requirements:
        unclear_points.append("구체적인 기술 스택이나 팀 상황에 대한 추가 정보가 있으면 더 정확한 분석이 가능합니다.")

    return Observation(
        raw_input=user_input,
        requirements=requirements,
        constraints=constraints,
        unclear_points=unclear_points,
    )
