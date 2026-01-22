"""
Requirements Extractor

요구사항 항목 추출기:
- "Must have", "Nice to have", "필수", "있으면 좋음" 섹션 감지
- 콤마(,), "and", "및", "이고" 기준으로 분리
- 전체 문장이 아닌 개별 항목 리스트로 반환

지원 형식:
- "Must have 기능은 A, B 이고"
- "Nice to have로는 C, D가 있으면 좋겠습니다"
- "필수: A, B, C"
- "선택: X 및 Y"
"""

import re
from dataclasses import dataclass
from typing import Optional

from src.observation.extractors.base import BaseExtractor, ExtractResult


@dataclass
class RequirementsResult:
    """요구사항 추출 결과"""
    must_have: list[str]
    nice_to_have: list[str]
    must_have_evidence: str = ""
    nice_to_have_evidence: str = ""


class RequirementsExtractor(BaseExtractor):
    """요구사항 항목 추출기"""

    name = "requirements"

    # === Must Have 패턴 ===
    # "Must have", "필수", "Core requirement", "핵심 기능"
    MUST_HAVE_PATTERNS = [
        # "Must have 기능은 X, Y 이고" 형식 (한영 혼합)
        re.compile(
            r'[Mm]ust[\s\-]?have[^\n]*?(?:는|은|기능은|:：)\s*([^.\n]+?)(?:\s+이고|\s+하고|입니다|\.|\n|$)',
            re.IGNORECASE
        ),
        # "Must have features are X and Y" 형식 (영어)
        re.compile(
            r'[Mm]ust[\s\-]?have\s+(?:features?|requirements?)\s+(?:is|are)\s+([^.\n]+?)(?:\.|\n|$)',
            re.IGNORECASE
        ),
        # "Core requirement is X" 형식
        re.compile(
            r'[Cc]ore\s+requirement[s]?\s+(?:is|are)\s+([^.\n]+?)(?:\.|\n|$)',
            re.IGNORECASE
        ),
        # "필수 기능: X, Y" 또는 "필수: X, Y" 형식
        re.compile(
            r'필수(?:\s*기능)?[은는]?\s*[:：]?\s*([^.\n]+?)(?:\s+이고|\s+하고|입니다|\.|\n|$)',
            re.IGNORECASE
        ),
        # "핵심 기능은 X" 형식
        re.compile(
            r'핵심\s*기능[은는]?\s*[:：]?\s*([^.\n]+?)(?:\s+이고|\s+하고|입니다|\.|\n|$)',
            re.IGNORECASE
        ),
    ]

    # === Nice to Have 패턴 ===
    # "Nice to have", "있으면 좋음", "Optional", "선택"
    NICE_TO_HAVE_PATTERNS = [
        # "Nice to have 로는 X, Y 가 있으면 좋겠습니다" 형식 (한영 혼합)
        re.compile(
            r'[Nn]ice[\s\-]?to[\s\-]?have[^\n]*?(?:로는|로|는|은|:：)\s*([^.\n]+?)\s*(?:가\s*있으면|있으면)',
            re.IGNORECASE
        ),
        # "Nice features include X and Y" 형식
        re.compile(
            r'[Nn]ice\s+features?\s+include[s]?\s+([^.\n]+?)(?:\.|\n|$)',
            re.IGNORECASE
        ),
        # "Optional: X, Y" 형식
        re.compile(
            r'[Oo]ptional\s*[:：]\s*([^.\n]+?)(?:\.|\n|$)',
            re.IGNORECASE
        ),
        # "있으면 좋은 기능: X" 형식
        re.compile(
            r'있으면\s*좋[은겠]?\s*(?:기능)?[은는]?\s*[:：]?\s*([^.\n]+?)(?:입니다|\.|\n|$)',
            re.IGNORECASE
        ),
        # "선택 기능: X" 형식
        re.compile(
            r'선택(?:\s*기능)?[은는]?\s*[:：]?\s*([^.\n]+?)(?:\s+이고|\s+하고|입니다|\.|\n|$)',
            re.IGNORECASE
        ),
    ]

    # === 항목 분리 패턴 ===
    # 콤마, "and", "및", "이고", "하고"
    ITEM_SPLIT_PATTERN = re.compile(
        r'\s*(?:,|、|，|\s+and\s+|\s+및\s+|\s+이고\s*|\s+하고\s*)\s*',
        re.IGNORECASE
    )

    def extract(self, normalized_text: str, sentences: list[str]) -> Optional[ExtractResult]:
        """
        텍스트에서 must_have와 nice_to_have 항목을 추출한다.

        Returns:
            ExtractResult with value=RequirementsResult
        """
        result = RequirementsResult(
            must_have=[],
            nice_to_have=[]
        )

        # 전체 텍스트에서 추출
        full_text = normalized_text

        # Must Have 추출
        for pattern in self.MUST_HAVE_PATTERNS:
            match = pattern.search(full_text)
            if match:
                items_text = match.group(1).strip()
                result.must_have_evidence = match.group(0).strip()
                items = self._split_items(items_text)
                if items:
                    result.must_have = items
                    break

        # Nice to Have 추출
        for pattern in self.NICE_TO_HAVE_PATTERNS:
            match = pattern.search(full_text)
            if match:
                items_text = match.group(1).strip()
                result.nice_to_have_evidence = match.group(0).strip()
                items = self._split_items(items_text)
                if items:
                    result.nice_to_have = items
                    break

        # 아무것도 추출되지 않았으면 None 반환
        if not result.must_have and not result.nice_to_have:
            return None

        # evidence 조합
        evidence_parts = []
        if result.must_have_evidence:
            evidence_parts.append(f"must_have: {result.must_have_evidence}")
        if result.nice_to_have_evidence:
            evidence_parts.append(f"nice_to_have: {result.nice_to_have_evidence}")

        return ExtractResult(
            value=result,
            confidence=0.9,
            evidence=" | ".join(evidence_parts),
            extractor=self.name
        )

    def _split_items(self, text: str) -> list[str]:
        """
        텍스트를 개별 항목으로 분리한다.

        Args:
            text: "Motion control, TCP/IP communication"

        Returns:
            ["Motion control", "TCP/IP communication"]
        """
        if not text:
            return []

        # 분리
        items = self.ITEM_SPLIT_PATTERN.split(text)

        # 정리: 빈 문자열 제거, 앞뒤 공백 제거
        cleaned = []
        for item in items:
            item = item.strip()
            # 너무 긴 항목은 문장으로 간주하여 제외 (50자 이상)
            if item and len(item) <= 50:
                # 괄호 내용 제거 (예: "(LLM is forbidden)" 제거)
                item = re.sub(r'\s*\([^)]*\)\s*$', '', item).strip()
                if item:
                    cleaned.append(item)

        return cleaned
