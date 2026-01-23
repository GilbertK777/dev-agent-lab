"""
Forbidden Extractor

금지 사항 추출기:
- "forbidden", "금지", "not allowed", "사용 불가" 등 감지
- LLM, 외부 API, 특정 기술 금지 여부 추출

지원 형식:
- "LLM is forbidden"
- "LLM 금지"
- "외부 API 사용 불가"
- "X is not allowed"
"""

import re
from typing import Optional

from src.observation.extractors.base import BaseExtractor, ExtractResult
from src.observation.extractors.utils import format_evidence


class ForbiddenExtractor(BaseExtractor):
    """금지 사항 추출기"""

    name = "forbidden"

    # 금지 키워드 패턴 (기술 키워드 우선 캡처)
    FORBIDDEN_PATTERNS = [
        # 괄호 안의 금지 표현: "(LLM is forbidden)" - 우선순위 높음
        re.compile(
            r'\((\w+)\s+(?:is\s+)?forbidden\)',
            re.IGNORECASE
        ),
        # "X usage is forbidden" - X를 캡처 (usage는 무시)
        re.compile(
            r'(\w+)\s+usage\s+is\s+forbidden',
            re.IGNORECASE
        ),
        # "X is forbidden" (단일 단어, usage/access 등 일반명사 제외)
        re.compile(
            r'(\w+)\s+is\s+forbidden',
            re.IGNORECASE
        ),
        # "X forbidden" (is 없이)
        re.compile(
            r'(\w+)\s+forbidden',
            re.IGNORECASE
        ),
        # "X 사용 금지", "X 금지"
        re.compile(
            r'(\w+)\s*(?:사용\s*)?금지',
            re.IGNORECASE
        ),
        # "X usage is not allowed"
        re.compile(
            r'(\w+)\s+usage\s+is\s+not\s+allowed',
            re.IGNORECASE
        ),
        # "X is not allowed"
        re.compile(
            r'(\w+)\s+is\s+not\s+allowed',
            re.IGNORECASE
        ),
        # "X not allowed"
        re.compile(
            r'(\w+)\s+not\s+allowed',
            re.IGNORECASE
        ),
        # "X 불가", "X 사용 불가"
        re.compile(
            r'(\w+)\s+(?:사용\s*)?불가',
            re.IGNORECASE
        ),
        # "without X"
        re.compile(
            r'without\s+(\w+)',
            re.IGNORECASE
        ),
        # "X prohibited"
        re.compile(
            r'(\w+)\s+prohibited',
            re.IGNORECASE
        ),
        # "don't use X"
        re.compile(
            r"(?:don't|do\s+not)\s+use\s+(\w+)",
            re.IGNORECASE
        ),
    ]

    # 일반적인 금지 대상 (정규화용)
    FORBIDDEN_NORMALIZE = {
        "llm": "LLM",
        "llms": "LLM",
        "ai": "AI",
        "gpt": "GPT",
        "chatgpt": "ChatGPT",
        "외부 api": "외부 API",
        "external api": "External API",
        "cloud": "Cloud",
        "클라우드": "Cloud",
    }

    def extract(self, normalized_text: str, sentences: list[str]) -> Optional[ExtractResult]:
        """텍스트에서 금지 사항을 추출한다."""

        forbidden_items: list[str] = []
        evidence_parts: list[str] = []

        # 모든 금지 패턴 스캔
        for pattern in self.FORBIDDEN_PATTERNS:
            for match in pattern.finditer(normalized_text):
                item = match.group(1).strip()
                normalized_item = self._normalize_item(item)

                if normalized_item and normalized_item not in forbidden_items:
                    forbidden_items.append(normalized_item)
                    evidence_parts.append(match.group(0).strip())

        if not forbidden_items:
            return None

        return ExtractResult(
            value=forbidden_items,
            confidence=0.9,
            evidence=format_evidence(" | ".join(evidence_parts)),
            extractor=self.name
        )

    # 무시할 단어 (금지 대상이 아닌 일반 단어)
    IGNORE_WORDS = {
        # 조동사/be동사
        "is", "are", "was", "were", "be", "been", "being",
        # 관사
        "a", "an", "the",
        # 일반 명사 (기술 키워드가 아닌 것)
        "usage", "access", "use", "it", "this", "that",
        "internet", "network",  # 너무 일반적인 단어
    }

    def _normalize_item(self, item: str) -> str:
        """금지 항목 정규화"""
        item_lower = item.lower().strip()

        # 무시할 단어는 건너뛰기
        if item_lower in self.IGNORE_WORDS:
            return ""

        # 너무 짧은 항목은 건너뛰기 (2글자 이하)
        if len(item_lower) <= 2:
            return ""

        # 알려진 항목이면 정규화
        if item_lower in self.FORBIDDEN_NORMALIZE:
            return self.FORBIDDEN_NORMALIZE[item_lower]

        # 그 외는 원본 유지
        if item:
            return item.strip()

        return ""
