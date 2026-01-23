"""
Requirements Extractor

요구사항 항목 추출기:
- "Must have", "Nice to have", "필수", "있으면 좋음" 섹션 감지
- 콤마(,), "and", "및", "이고" 기준으로 분리
- 전체 문장이 아닌 개별 항목 리스트로 반환

지원 형식:
- "Must have 기능은 A, B 이고"
- "Must have: A, B, C."
- "Nice to have로는 C, D가 있으면 좋겠습니다"
- "Nice to have: D, E."
- "필수: A, B, C"
- "선택: X 및 Y"

섹션 종료 조건:
- 다음 섹션 키워드 (Nice to have:, Constraints:, 등)
- 개행 후 bullet 시작 ("\\n- ")
"""

import re
from dataclasses import dataclass
from typing import Optional

from src.observation.extractors.base import BaseExtractor, ExtractResult
from src.observation.extractors.utils import format_evidence


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

    # 섹션 종료 키워드 (이후 내용은 캡처하지 않음)
    SECTION_TERMINATORS = [
        r'\n\s*-\s',  # bullet point
        r'\nConstraints?:',
        r'\nNice\s+to\s+have:',
        r'\nMust\s+have:',
        r'\n제약',
        r'\n선택',
        r'\n필수',
    ]

    # === Must Have 시작 패턴 ===
    MUST_HAVE_STARTERS = [
        # "Must have: X, Y, Z." 형식 (콜론 형식)
        re.compile(r'[Mm]ust[\s\-]?have\s*:', re.IGNORECASE),
        # "Must have features are X and Y" 형식 (영어)
        re.compile(r'[Mm]ust[\s\-]?have\s+(?:features?|requirements?)\s+(?:is|are)', re.IGNORECASE),
        # "Must have 기능은" 형식 (한영 혼합)
        re.compile(r'[Mm]ust[\s\-]?have[^\n:]*?(?:는|은|기능은)', re.IGNORECASE),
        # "Core requirement is" 형식
        re.compile(r'[Cc]ore\s+requirement[s]?\s+(?:is|are)', re.IGNORECASE),
        # "필수 기능:" 또는 "필수:" 형식
        re.compile(r'필수(?:\s*기능)?[은는]?\s*[:：]?', re.IGNORECASE),
        # "핵심 기능은" 형식
        re.compile(r'핵심\s*기능[은는]?\s*[:：]?', re.IGNORECASE),
    ]

    # === Nice to Have 시작 패턴 ===
    NICE_TO_HAVE_STARTERS = [
        # "Nice to have: X, Y." 형식 (콜론 형식)
        re.compile(r'[Nn]ice[\s\-]?to[\s\-]?have\s*:', re.IGNORECASE),
        # "Nice to have 로는" 형식 (한영 혼합)
        re.compile(r'[Nn]ice[\s\-]?to[\s\-]?have[^\n:]*?(?:로는|로|는|은)', re.IGNORECASE),
        # "Nice features include" 형식
        re.compile(r'[Nn]ice\s+features?\s+include[s]?', re.IGNORECASE),
        # "Optional:" 형식
        re.compile(r'[Oo]ptional\s*[:：]', re.IGNORECASE),
        # "있으면 좋은 기능" 형식
        re.compile(r'있으면\s*좋[은겠]?\s*(?:기능)?[은는]?\s*[:：]?', re.IGNORECASE),
        # "선택 기능:" 형식
        re.compile(r'선택(?:\s*기능)?[은는]?\s*[:：]?', re.IGNORECASE),
    ]

    # === 항목 분리 패턴 ===
    ITEM_SPLIT_PATTERN = re.compile(
        r'\s*(?:,|、|，|\s+and\s+|\s+및\s+|\s+이고\s*|\s+하고\s*)\s*',
        re.IGNORECASE
    )

    # === 항목 종료 패턴 (라인 내) ===
    ITEM_END_PATTERN = re.compile(
        r'(?:\s+이고|\s+하고|입니다|가\s*있으면|있으면\s*좋겠습니다|\.(?:\s|$)|\n)',
        re.IGNORECASE
    )

    def extract(self, normalized_text: str, sentences: list[str]) -> Optional[ExtractResult]:
        """
        텍스트에서 must_have와 nice_to_have 항목을 추출한다.
        """
        result = RequirementsResult(
            must_have=[],
            nice_to_have=[]
        )

        # Must Have 추출
        must_have_items, must_have_evidence = self._extract_section(
            normalized_text,
            self.MUST_HAVE_STARTERS,
            exclude_starters=self.NICE_TO_HAVE_STARTERS
        )
        if must_have_items:
            result.must_have = must_have_items
            result.must_have_evidence = must_have_evidence

        # Nice to Have 추출
        nice_to_have_items, nice_to_have_evidence = self._extract_section(
            normalized_text,
            self.NICE_TO_HAVE_STARTERS,
            exclude_starters=self.MUST_HAVE_STARTERS
        )
        if nice_to_have_items:
            result.nice_to_have = nice_to_have_items
            result.nice_to_have_evidence = nice_to_have_evidence

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

    def _extract_section(
        self,
        text: str,
        starters: list[re.Pattern],
        exclude_starters: list[re.Pattern]
    ) -> tuple[list[str], str]:
        """
        섹션 시작 패턴을 찾고, 섹션 종료 조건까지의 내용을 추출한다.

        Returns:
            (items_list, evidence_string)
        """
        for starter in starters:
            match = starter.search(text)
            if not match:
                continue

            start_pos = match.end()
            section_start = match.group(0)

            # 섹션 종료 위치 찾기
            end_pos = len(text)

            # 1. 섹션 종료 키워드 확인
            for terminator in self.SECTION_TERMINATORS:
                term_match = re.search(terminator, text[start_pos:], re.IGNORECASE)
                if term_match:
                    candidate_end = start_pos + term_match.start()
                    if candidate_end < end_pos:
                        end_pos = candidate_end

            # 2. 다른 섹션 시작 키워드 확인 (Nice to have가 Must have 내용에 포함되지 않도록)
            for exclude_starter in exclude_starters:
                exclude_match = exclude_starter.search(text[start_pos:])
                if exclude_match:
                    candidate_end = start_pos + exclude_match.start()
                    if candidate_end < end_pos:
                        end_pos = candidate_end

            # 3. 라인 내 종료 패턴 확인 (마침표, "이고" 등)
            section_text = text[start_pos:end_pos]
            end_match = self.ITEM_END_PATTERN.search(section_text)
            if end_match:
                section_text = section_text[:end_match.start()]

            # 항목 추출
            items = self._split_items(section_text)
            if items:
                evidence = format_evidence(section_start + section_text.strip())
                return items, evidence

        return [], ""

    def _split_items(self, text: str) -> list[str]:
        """
        텍스트를 개별 항목으로 분리한다.
        """
        if not text:
            return []

        # 분리
        items = self.ITEM_SPLIT_PATTERN.split(text)

        # 정리
        cleaned = []
        for item in items:
            item = item.strip()

            # 빈 항목 스킵
            if not item:
                continue

            # 너무 긴 항목은 문장으로 간주하여 제외 (60자 이상)
            if len(item) > 60:
                continue

            # 괄호 내용 제거 (예: "(Korean/English)" 제거)
            item = re.sub(r'\s*\([^)]*\)\s*$', '', item).strip()

            # 끝에 붙은 마침표 제거
            item = item.rstrip('.')

            if item:
                cleaned.append(item)

        return cleaned
