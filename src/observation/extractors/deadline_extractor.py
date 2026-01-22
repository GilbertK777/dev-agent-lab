"""
Deadline Extractor (문장 단위 스캔 + 합산 방식)

일정/기간 정보를 추출하여 일수(days)로 변환한다.
각 문장에서 년/월/주/일을 개별 스캔하고 합산한다.

지원 형식:
- "1 year and 3 months" → 455일
- "2 weeks", "3주", "10d", "D+14"
- "2개월", "1달", "3 months"
- "1년", "2 years"
- "1년 6개월" (복합)
"""

import re
from typing import Optional
from dataclasses import dataclass

from src.observation.extractors.base import BaseExtractor, ExtractResult


@dataclass
class TimeComponents:
    """시간 구성 요소"""
    years: int = 0
    months: int = 0
    weeks: int = 0
    days: int = 0
    evidence: str = ""

    def to_days(self) -> int:
        """총 일수로 변환"""
        return (
            self.years * 365 +
            self.months * 30 +
            self.weeks * 7 +
            self.days
        )

    def is_empty(self) -> bool:
        return self.years == 0 and self.months == 0 and self.weeks == 0 and self.days == 0


class DeadlineExtractor(BaseExtractor):
    """일정/기간 추출기 (문장 단위 스캔 + 합산)"""

    name = "deadline"

    # 단위별 일수 변환 상수
    DAYS_PER_WEEK = 7
    DAYS_PER_MONTH = 30
    DAYS_PER_YEAR = 365

    # === 단위 패턴 (개별 스캔용) ===

    # 년 단위: "1년", "2 years", "1yr"
    YEAR_PATTERN = re.compile(
        r'(\d+)\s*(?:년|year|years|yr|yrs)\b',
        re.IGNORECASE
    )

    # 월 단위: "3개월", "6 months", "2달", "3mo"
    # 한글은 단어 경계가 다르므로 별도 처리
    MONTH_PATTERN = re.compile(
        r'(\d+)\s*(?:개월|달|month|months|mo|mos)(?:\b|(?=[^a-zA-Z]))',
        re.IGNORECASE
    )

    # 주 단위: "2주", "3 weeks", "2w", "3wk"
    WEEK_PATTERN = re.compile(
        r'(\d+)\s*(?:주|week|weeks|wk|wks|w)\b',
        re.IGNORECASE
    )

    # 일 단위: "10일", "5 days", "3d"
    DAY_PATTERN = re.compile(
        r'(\d+)\s*(?:일|day|days|d)(?!\w)',
        re.IGNORECASE
    )

    # D+N 형식: "D+14", "D-7", "D-day" (단어 경계 필요)
    # 주의: "and 3"의 "d 3"와 혼동 방지를 위해 반드시 + 또는 - 필요
    D_PLUS_PATTERN = re.compile(
        r'(?:^|[\s\(])([dD][+\-]\s*\d+)',
        re.IGNORECASE
    )

    def extract(self, normalized_text: str, sentences: list[str]) -> Optional[ExtractResult]:
        """
        텍스트에서 일정/기간 정보를 추출한다.

        전략:
        1. 각 문장에서 년/월/주/일을 개별 스캔
        2. 같은 문장 내 발견된 값들을 합산
        3. 가장 완전한 결과 반환
        """
        best_result: Optional[ExtractResult] = None
        best_days = 0

        # 문장별로 스캔
        for sentence in sentences:
            result = self._extract_from_sentence(sentence)
            if result and result.value > best_days:
                best_result = result
                best_days = result.value

        # 전체 텍스트에서도 시도 (문장 분리가 안 된 경우 대비)
        full_result = self._extract_from_sentence(normalized_text)
        if full_result and full_result.value > best_days:
            best_result = full_result

        return best_result

    def _extract_from_sentence(self, text: str) -> Optional[ExtractResult]:
        """단일 문장에서 시간 구성 요소를 추출하고 합산"""

        # D+N 형식 우선 처리
        d_plus_result = self._extract_d_plus(text)
        if d_plus_result:
            return d_plus_result

        # 년/월/주/일 개별 스캔 및 합산
        components = self._scan_time_components(text)

        if components.is_empty():
            return None

        total_days = components.to_days()

        # 신뢰도 계산
        confidence = self._calculate_confidence(components)

        return ExtractResult(
            value=total_days,
            confidence=confidence,
            evidence=components.evidence,
            extractor=self.name
        )

    def _scan_time_components(self, text: str) -> TimeComponents:
        """문장에서 모든 시간 구성 요소를 스캔"""
        components = TimeComponents()
        evidence_parts: list[str] = []

        # 년 스캔
        year_match = self.YEAR_PATTERN.search(text)
        if year_match:
            components.years = int(year_match.group(1))
            evidence_parts.append(year_match.group())

        # 월 스캔
        month_match = self.MONTH_PATTERN.search(text)
        if month_match:
            components.months = int(month_match.group(1))
            evidence_parts.append(month_match.group())

        # 주 스캔
        week_match = self.WEEK_PATTERN.search(text)
        if week_match:
            components.weeks = int(week_match.group(1))
            evidence_parts.append(week_match.group())

        # 일 스캔
        day_match = self.DAY_PATTERN.search(text)
        if day_match:
            components.days = int(day_match.group(1))
            evidence_parts.append(day_match.group())

        # evidence 조합
        if evidence_parts:
            components.evidence = " + ".join(evidence_parts)

        return components

    def _extract_d_plus(self, text: str) -> Optional[ExtractResult]:
        """D+N 형식 추출"""
        match = self.D_PLUS_PATTERN.search(text)
        if match:
            # 그룹 1에서 D+숫자 부분 추출
            d_part = match.group(1)
            # 숫자만 추출
            num_match = re.search(r'\d+', d_part)
            if num_match:
                days = int(num_match.group())
                return ExtractResult(
                    value=days,
                    confidence=0.9,
                    evidence=d_part.strip(),
                    extractor=self.name
                )
        return None

    def _calculate_confidence(self, components: TimeComponents) -> float:
        """구성 요소에 따른 신뢰도 계산"""
        # 복합 형식(년+월)이면 높은 신뢰도
        component_count = sum([
            1 if components.years > 0 else 0,
            1 if components.months > 0 else 0,
            1 if components.weeks > 0 else 0,
            1 if components.days > 0 else 0,
        ])

        if component_count >= 2:
            return 0.95  # 복합 형식
        elif components.years > 0:
            return 0.85
        elif components.months > 0:
            return 0.85
        elif components.weeks > 0:
            return 0.85
        elif components.days > 0:
            return 0.8
        else:
            return 0.7
