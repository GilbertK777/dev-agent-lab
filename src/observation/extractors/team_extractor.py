"""
Team Size Extractor

팀 인원 정보를 추출하여 숫자로 변환한다.

지원 형식:
- 단일값: "5명", "3 ppl", "team of 5"
- 범위: "2~3명", "2-3 people", "2 to 3 people"
- "인원은 2명", "팀은 3명"
- "개발자 5명", "developers: 3"
"""

import re
from typing import Optional, Union

from src.observation.extractors.base import BaseExtractor, ExtractResult


class TeamSizeExtractor(BaseExtractor):
    """팀 인원 추출기"""

    name = "team_size"

    # === 범위 패턴 (우선순위 높음) ===
    RANGE_PATTERNS = [
        # "인원은 2~3명", "인원 2-3명"
        (
            re.compile(r"인원[은이가]?\s*(\d+)\s*[~\-]\s*(\d+)\s*명", re.IGNORECASE),
            lambda m: {"min": int(m.group(1)), "max": int(m.group(2))},
            "inwin_range"
        ),

        # "팀 2~3명", "팀은 2-3명"
        (
            re.compile(r"팀[은이가]?\s*(\d+)\s*[~\-]\s*(\d+)\s*명", re.IGNORECASE),
            lambda m: {"min": int(m.group(1)), "max": int(m.group(2))},
            "team_range"
        ),

        # "2~3명", "2-3명" (일반)
        (
            re.compile(r"(\d+)\s*[~\-]\s*(\d+)\s*명", re.IGNORECASE),
            lambda m: {"min": int(m.group(1)), "max": int(m.group(2))},
            "simple_range_ko"
        ),

        # "2 to 3 people", "2-3 people", "2~3 developers"
        (
            re.compile(
                r"(\d+)\s*(?:to|~|\-)\s*(\d+)\s*(?:people|persons?|developers?|engineers?|members?|ppl)",
                re.IGNORECASE
            ),
            lambda m: {"min": int(m.group(1)), "max": int(m.group(2))},
            "range_en"
        ),

        # "team size 2-3", "team of 2~3"
        (
            re.compile(r"team\s+(?:size|of)\s+(\d+)\s*[~\-]\s*(\d+)", re.IGNORECASE),
            lambda m: {"min": int(m.group(1)), "max": int(m.group(2))},
            "team_size_range"
        ),

        # "team is 2~5", "team is 2-5"
        (
            re.compile(r"team\s+is\s+(\d+)\s*[~\-]\s*(\d+)", re.IGNORECASE),
            lambda m: {"min": int(m.group(1)), "max": int(m.group(2))},
            "team_is_range"
        ),
    ]

    # === 단일값 패턴 ===
    SINGLE_PATTERNS = [
        # "인원은 2명", "인원이 3명", "인원 5명"
        (
            re.compile(r"인원[은이가]?\s*(\d+)\s*명", re.IGNORECASE),
            lambda m: int(m.group(1)),
            "inwin_format"
        ),

        # "팀은 3명", "팀이 5명", "팀 2명"
        (
            re.compile(r"팀[은이가]?\s*(\d+)\s*명", re.IGNORECASE),
            lambda m: int(m.group(1)),
            "team_format"
        ),

        # "개발자 5명", "개발자는 3명"
        (
            re.compile(r"개발자[는은이가]?\s*(\d+)\s*명", re.IGNORECASE),
            lambda m: int(m.group(1)),
            "developer_format"
        ),

        # "team of 5", "team of 3 people"
        (
            re.compile(r"team\s+of\s+(\d+)", re.IGNORECASE),
            lambda m: int(m.group(1)),
            "team_of_format"
        ),

        # "Team size will be 4 people", "team size 5"
        (
            re.compile(r"team\s+size\s+(?:will\s+be\s+|is\s+)?(\d+)", re.IGNORECASE),
            lambda m: int(m.group(1)),
            "team_size_format"
        ),

        # "5 developers", "3 engineers", "2 members", "4 people"
        (
            re.compile(r"(\d+)\s*(?:developers?|engineers?|members?|people|persons?)", re.IGNORECASE),
            lambda m: int(m.group(1)),
            "n_developers_format"
        ),

        # "5 ppl", "3ppl"
        (
            re.compile(r"(\d+)\s*ppl", re.IGNORECASE),
            lambda m: int(m.group(1)),
            "ppl_format"
        ),

        # "5명이고", "3명 정도", "2명으로" (문맥에서 팀 관련일 때)
        (
            re.compile(r"(\d+)\s*명\s*(?:이고|정도|으로|이서|이라)", re.IGNORECASE),
            lambda m: int(m.group(1)),
            "n_myung_context"
        ),

        # 단순 "N명" (앞에 시간 단위가 없을 때만, 부분 투입 제외)
        # "담당 1명", "포함" 등 부분 투입 컨텍스트 제외
        (
            re.compile(r"(?<![\d])(?<!담당\s)(\d+)\s*명(?!\s*(?:개월|달|주|일|년))(?!.*포함)", re.IGNORECASE),
            lambda m: int(m.group(1)),
            "simple_myung"
        ),
    ]

    # 부분 투입/담당 제외 패턴 (이 패턴에 매칭되면 팀 사이즈가 아님)
    EXCLUSION_PATTERNS = [
        re.compile(r"담당\s*\d+\s*명", re.IGNORECASE),
        re.compile(r"\d+\s*명\s*(?:포함|투입|배정|배치)", re.IGNORECASE),
    ]

    # 팀 관련 컨텍스트 키워드
    CONTEXT_KEYWORDS = [
        "팀", "team", "인원", "인력", "개발자", "developer", "engineer",
        "member", "people", "ppl", "명"
    ]

    def extract(self, normalized_text: str, sentences: list[str]) -> Optional[ExtractResult]:
        """
        텍스트에서 팀 인원 정보를 추출한다.

        Returns:
            ExtractResult with:
            - value=int (단일값) 또는
            - value={"min": int, "max": int} (범위)
        """
        # 전체 텍스트에서 먼저 시도 (범위 우선)
        result = self._extract_from_text(normalized_text)
        if result:
            return result

        # 문장별로 시도
        for sentence in sentences:
            result = self._extract_from_text(sentence)
            if result:
                return result

        return None

    def _extract_from_text(self, text: str) -> Optional[ExtractResult]:
        """단일 텍스트에서 추출 시도 (범위 패턴 우선)"""

        # 1. 범위 패턴 먼저 시도 (부분 투입 체크 전에)
        for pattern, converter, pattern_name in self.RANGE_PATTERNS:
            match = pattern.search(text)
            if match:
                try:
                    value = converter(match)

                    # 유효성 검증
                    if not self._validate_range(value):
                        continue

                    confidence = self._calculate_confidence(pattern_name, text, match, is_range=True)

                    return ExtractResult(
                        value=value,
                        confidence=confidence,
                        evidence=match.group(),
                        extractor=self.name
                    )
                except (ValueError, IndexError):
                    continue

        # 2. 부분 투입/담당 패턴이면 단일값 추출 스킵
        for excl_pattern in self.EXCLUSION_PATTERNS:
            if excl_pattern.search(text):
                return None

        # 3. 단일값 패턴 시도
        for pattern, converter, pattern_name in self.SINGLE_PATTERNS:
            match = pattern.search(text)
            if match:
                try:
                    team_size = converter(match)

                    # 비현실적인 값 필터링 (1~1000명)
                    if team_size < 1 or team_size > 1000:
                        continue

                    confidence = self._calculate_confidence(pattern_name, text, match, is_range=False)

                    return ExtractResult(
                        value=team_size,
                        confidence=confidence,
                        evidence=match.group(),
                        extractor=self.name
                    )
                except (ValueError, IndexError):
                    continue

        return None

    def _validate_range(self, value: dict) -> bool:
        """범위 값 유효성 검증"""
        min_val = value.get("min", 0)
        max_val = value.get("max", 0)

        # 기본 검증
        if min_val < 1 or max_val < 1:
            return False
        if min_val > max_val:
            return False
        if max_val > 1000:
            return False

        return True

    def _calculate_confidence(
        self,
        pattern_name: str,
        text: str,
        match,
        is_range: bool
    ) -> float:
        """패턴 유형과 컨텍스트에 따른 신뢰도 계산"""

        if is_range:
            base_confidence = {
                "inwin_range": 0.95,
                "team_range": 0.95,
                "simple_range_ko": 0.85,
                "range_en": 0.9,
                "team_size_range": 0.9,
            }.get(pattern_name, 0.8)
        else:
            base_confidence = {
                "inwin_format": 0.95,
                "team_format": 0.95,
                "developer_format": 0.9,
                "team_of_format": 0.9,
                "team_size_format": 0.95,
                "n_developers_format": 0.85,
                "ppl_format": 0.85,
                "n_myung_context": 0.8,
                "simple_myung": 0.6,
            }.get(pattern_name, 0.5)

        # 컨텍스트 키워드가 있으면 신뢰도 보정
        text_lower = text.lower()
        context_bonus = 0.0
        for keyword in self.CONTEXT_KEYWORDS:
            if keyword in text_lower:
                context_bonus = 0.1
                break

        return min(1.0, base_confidence + context_bonus)
