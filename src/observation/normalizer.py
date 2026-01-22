"""
Normalizer 모듈 (Lossless Normalization)

한/영 혼용 입력을 보존적으로 정규화한다.
- 원문 의미를 바꾸지 않음
- 대문자 토큰 치환 금지 (YEARS, MONTHS 등 금지)
- 형태만 정리: 소문자화, 공백 정리, 숫자-단위 분리
"""

import re
from dataclasses import dataclass
from typing import Literal


@dataclass
class Token:
    """토큰 정보"""
    text: str
    start: int
    end: int
    kind: Literal["word", "number", "unit", "symbol"]


@dataclass
class NormalizeResult:
    """정규화 결과"""
    original: str              # 원문 텍스트
    normalized: str            # 보존적 정규화 문자열
    sentences: list[str]       # 분리된 문장들
    tokens: list[Token]        # 토큰 목록
    lang_mix_ratio: float      # 영어 비율 (0.0 ~ 1.0)
    tokens_estimate: int       # 추정 토큰 수


# === 단위 키워드 (참조용, extractor에서 사용) ===
# normalizer에서는 치환하지 않고, extractor가 이 목록을 참조하여 인식

UNIT_KEYWORDS = {
    "time_year": ["year", "years", "yr", "yrs", "년"],
    "time_month": ["month", "months", "mo", "mos", "개월", "달"],
    "time_week": ["week", "weeks", "wk", "wks", "주"],
    "time_day": ["day", "days", "d", "일"],
    "people": ["명", "ppl", "people", "person", "persons"],
}


def _calculate_lang_mix_ratio(text: str) -> float:
    """
    텍스트의 영어/한글 비율을 계산한다.
    0.0 = 전부 한글, 1.0 = 전부 영어
    """
    if not text:
        return 0.0

    korean_chars = len(re.findall(r'[가-힣]', text))
    english_chars = len(re.findall(r'[a-zA-Z]', text))

    total = korean_chars + english_chars
    if total == 0:
        return 0.0

    return english_chars / total


def _estimate_tokens(text: str) -> int:
    """토큰 수를 추정한다."""
    words = re.findall(r'\b\w+\b', text)
    return len(words)


def _segment_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리한다."""
    sentences = re.split(r'[.\n!?]+', text)
    return [s.strip() for s in sentences if s.strip()]


def _normalize_text(text: str) -> str:
    """
    보존적 정규화: 형태만 정리하고 의미는 유지

    허용:
    - 소문자화
    - 연속 공백 정리
    - 숫자와 단위 사이 공백 추가 (1year → 1 year)

    금지:
    - 단어 치환 (year → YEARS 금지)
    - 의미 변경
    """
    result = text

    # 1. 숫자와 영문 단위 사이 공백 추가 (1year → 1 year, 3months → 3 months)
    result = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', result)

    # 2. 영문 단위와 숫자 사이 공백 추가 (year3 → year 3) - 드문 케이스
    result = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', result)

    # 3. 연속 공백 정리
    result = re.sub(r'\s+', ' ', result)

    # 4. 앞뒤 공백 제거
    result = result.strip()

    return result


def _tokenize(text: str) -> list[Token]:
    """텍스트를 토큰으로 분리한다."""
    tokens: list[Token] = []

    # 토큰 패턴: 숫자, 단어(한글/영문), 기호
    pattern = re.compile(r'(\d+)|([가-힣]+)|([a-zA-Z]+)|([^\s\w])')

    for match in pattern.finditer(text):
        start = match.start()
        end = match.end()
        matched_text = match.group()

        if match.group(1):  # 숫자
            kind = "number"
        elif match.group(2):  # 한글
            # 한글 단위인지 확인
            if matched_text in ["년", "개월", "달", "주", "일", "명"]:
                kind = "unit"
            else:
                kind = "word"
        elif match.group(3):  # 영문
            # 영문 단위인지 확인
            lower_text = matched_text.lower()
            is_unit = any(
                lower_text in units
                for units in UNIT_KEYWORDS.values()
            )
            kind = "unit" if is_unit else "word"
        else:  # 기호
            kind = "symbol"

        tokens.append(Token(
            text=matched_text,
            start=start,
            end=end,
            kind=kind
        ))

    return tokens


def normalize(text: str) -> NormalizeResult:
    """
    텍스트를 보존적으로 정규화한다.

    원칙:
    - 원문 의미 유지 (단어 치환 금지)
    - 형태만 정리 (공백, 숫자-단위 분리)
    - evidence 추출을 위해 원문 매핑 가능
    """
    if not text or not text.strip():
        return NormalizeResult(
            original=text,
            normalized="",
            sentences=[],
            tokens=[],
            lang_mix_ratio=0.0,
            tokens_estimate=0
        )

    lang_mix_ratio = _calculate_lang_mix_ratio(text)
    tokens_estimate = _estimate_tokens(text)
    sentences = _segment_sentences(text)
    normalized = _normalize_text(text)
    tokens = _tokenize(text)

    return NormalizeResult(
        original=text,
        normalized=normalized,
        sentences=sentences,
        tokens=tokens,
        lang_mix_ratio=lang_mix_ratio,
        tokens_estimate=tokens_estimate
    )
