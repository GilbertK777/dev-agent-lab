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
from src.observation.extractors.utils import format_evidence, truncate_at_word_boundary


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
    # 주의: 정규화 후 개행이 공백으로 바뀌므로 \s 패턴 사용
    SECTION_TERMINATORS = [
        r'(?:\n|\s)Constraints?:',
        r'(?:\n|\s)Nice\s+to\s+have:',
        r'(?:\n|\s)Must\s+have:',
        r'(?:\n|\s)제약',
        r'(?:\n|\s)선택',
        r'(?:\n|\s)필수',
        r'(?:\n|\s)Ask:',
        r'(?:\n|\s)Timeline',
        r'(?:\n|\s)Team',
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
        # "있으면 좋은 기능" 형식 (반드시 "기능" 또는 콜론 필요)
        re.compile(r'있으면\s*좋[은겠]?\s*기능[은는]?\s*[:：]?', re.IGNORECASE),
        # "선택 기능:" 형식
        re.compile(r'선택(?:\s*기능)?[은는]?\s*[:：]?', re.IGNORECASE),
    ]

    # === 항목 분리 패턴 ===
    # bullet point (\n- 또는 정규화된 " - "), 콤마, and, 및 등으로 분리
    # 주의: " - " 패턴은 단어 경계에서만 분리 (SECS-GEM 같은 하이픈 용어 보존)
    ITEM_SPLIT_PATTERN = re.compile(
        r'\s*(?:\n\s*-\s*|\s+-\s+|,|、|，|\s+and\s+|\s+및\s+|\s+이고\s*|\s+하고\s*)\s*',
        re.IGNORECASE
    )

    # === 항목 종료 패턴 (라인 내) ===
    # "가 있으면", "이 있으면" 등 종료 조건
    ITEM_END_PATTERN = re.compile(
        r'(?:\s+이고(?:\s|$)|\s+하고(?:\s|$)|입니다|[가이]\s*있으면|있으면\s*좋겠습니다|\.(?:\s|$))',
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
        여러 섹션이 있으면 모두 수집한다 (예: "Must have:" + "필수 기능:")

        Returns:
            (items_list, evidence_string)
        """
        all_items: list[str] = []
        all_evidence: list[str] = []

        for starter in starters:
            # 모든 매칭을 찾음 (finditer)
            for match in starter.finditer(text):
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

                # 2. 다른 섹션 시작 키워드 확인
                for exclude_starter in exclude_starters:
                    exclude_match = exclude_starter.search(text[start_pos:])
                    if exclude_match:
                        candidate_end = start_pos + exclude_match.start()
                        if candidate_end < end_pos:
                            end_pos = candidate_end

                # 3. 같은 타입의 다른 섹션 시작 확인 (중복 방지)
                for other_starter in starters:
                    if other_starter != starter:
                        other_match = other_starter.search(text[start_pos:])
                        if other_match:
                            candidate_end = start_pos + other_match.start()
                            if candidate_end < end_pos:
                                end_pos = candidate_end

                section_text = text[start_pos:end_pos]

                # 라인 내 종료 패턴 확인 (마침표, "가 있으면" 등)
                end_match = self.ITEM_END_PATTERN.search(section_text)
                if end_match:
                    section_text = section_text[:end_match.start()]

                # 항목 추출
                items = self._split_items(section_text)
                if items:
                    # 중복 제거하며 추가
                    for item in items:
                        if item not in all_items:
                            all_items.append(item)
                    # evidence: 줄바꿈/불릿을 공백으로 정리, 단어 경계에서 자르기
                    evidence_text = section_start + section_text.strip()
                    evidence_text = re.sub(r'\s*-\s*', ' ', evidence_text)  # 불릿 정리
                    evidence_text = format_evidence(evidence_text)
                    all_evidence.append(truncate_at_word_boundary(evidence_text, 100))

        if all_items:
            return all_items, " | ".join(all_evidence)

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

            # 앞에 붙은 ": - " 또는 "- " 제거
            item = re.sub(r'^[:\-\s]+', '', item).strip()

            # 빈 항목 스킵 (정리 후)
            if not item:
                continue

            # " + " 분리 (단, "C++" 등 언어명은 제외)
            # "A (...) + B" -> ["A (...)", "B"]
            if ' + ' in item and 'C++' not in item and '++' not in item:
                sub_items = [s.strip() for s in item.split(' + ') if s.strip()]
                for sub in sub_items:
                    sub = self._clean_item(sub)
                    if sub:
                        cleaned.append(sub)
            else:
                item = self._clean_item(item)
                if item:
                    cleaned.append(item)

        return cleaned

    def _clean_item(self, item: str) -> str:
        """개별 항목 정리"""
        if not item:
            return ""

        # 너무 긴 항목은 문장으로 간주하여 제외 (60자 이상)
        if len(item) > 60:
            return ""

        # 괄호 내용 제거 (예: "(Korean/English)" 제거)
        item = re.sub(r'\s*\([^)]*\)\s*$', '', item).strip()

        # 끝에 붙은 마침표 제거
        item = item.rstrip('.')

        return item
