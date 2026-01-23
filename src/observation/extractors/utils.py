"""
Extractor 공통 유틸리티

evidence 문자열 후처리 등 추출기 공통 기능
"""

import re


def format_evidence(text: str) -> str:
    """
    Evidence 문자열을 사람이 읽기 자연스럽게 후처리한다.

    추출 로직은 변경하지 않고, 표시용 문자열만 정리한다.

    규칙:
    1) 구두점(: ; , ) ] }) 뒤에 공백 1칸 (연속 구두점/문장끝 제외)
    2) 한글 조사/연결어 뒤에 공백이 없고 다음이 글자면 공백 1칸 삽입
    3) 영문 동사/구문 뒤에 공백이 없고 다음이 영문자면 공백 1칸 삽입
    4) 개행은 공백으로 통일, 연속 공백은 1칸, trim
    """
    if not text:
        return text

    result = text

    # 4) 개행을 공백으로 치환
    result = result.replace('\n', ' ')

    # 1) 구두점 뒤 공백 보장: :, ;, ,, ), ], }
    # 구두점 뒤에 공백이 없고 다음이 글자/숫자면 공백 삽입
    # lookahead로 "공백 없이 글자가 오는 경우"만 처리
    result = re.sub(r'([:;,\)\]\}])(?=[^\s\.:;,\)\]\}])', r'\1 ', result)

    # 2) 한글 조사/연결어 뒤 공백 보장 (lookaround 기반)
    # 조사 뒤에 공백 없이 바로 글자(한글/영문/숫자)가 오면 공백 삽입
    korean_particles = [
        '그리고', '하지만', '또는', '에서', '으로', '이고', '이며', '로는',
        '은', '는', '이', '가', '을', '를', '에', '로', '과', '와', '및'
    ]
    # 긴 패턴부터 매칭 (로는 before 로, 에서 before 에)
    for particle in korean_particles:
        # 조사 뒤에 공백 없이 글자가 바로 오는 경우
        pattern = rf'({re.escape(particle)})(?=[가-힣a-zA-Z0-9])'
        result = re.sub(pattern, r'\1 ', result)

    # 3) 영문 동사/구문 뒤 공백 보장 (lookaround 기반)
    # 단어 경계(\b) 대신 lookaround 사용: 앞에 영문자가 없어야 하고, 뒤에 영문자가 바로 오면 공백 삽입
    # 단, 일반적인 접미사(ment, ments, s, d, ing 등)가 바로 오면 단어 내부로 판단하여 제외
    english_connectors = [
        'includes', 'included', 'include',
        'requires', 'required', 'require',
        'indicates', 'means',
        'being', 'been', 'were', 'was', 'are', 'is', 'be'
    ]
    for connector in english_connectors:
        # 앞에 영문자 없음 + connector + 접미사가 아닌 영문자
        # 접미사 패턴: ment/ments (requirement), s/d/ed/ing, tion/tions, able/ible/ly
        pattern = rf'(?<![a-zA-Z])({connector})(?!(?:ment|ments|s|d|ed|ing|tion|tions|able|ible|ly)(?:[^a-zA-Z]|$))(?=[a-zA-Z])'
        result = re.sub(pattern, r'\1 ', result, flags=re.IGNORECASE)

    # 숫자-단위 붙임 분리 (표시용): 6months → 6 months
    result = re.sub(r'(\d)(?=[a-zA-Z])', r'\1 ', result)

    # 4) 연속 공백을 1칸으로 축소
    result = re.sub(r'\s+', ' ', result)

    # 4) 앞뒤 공백 trim
    result = result.strip()

    return result
