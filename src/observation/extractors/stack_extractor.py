"""
Stack Extractor

기술 스택/언어 정보 추출기:
- Python, C#, C++, Java, JavaScript 등 감지
- 여러 언어가 언급되면 모두 추출

지원 형식:
- "Python, C# 혼용을 고려 중입니다"
- "Python only"
- "기술 스택: React, Node.js"
"""

import re
from typing import Optional

from src.observation.extractors.base import BaseExtractor, ExtractResult


class StackExtractor(BaseExtractor):
    """기술 스택/언어 추출기"""

    name = "stack"

    # 언어/프레임워크 키워드 (정규화된 이름으로 매핑)
    STACK_MAP = {
        # Python
        "python": "Python",
        "파이썬": "Python",
        "py": "Python",
        # C#
        "c#": "C#",
        "csharp": "C#",
        "c샵": "C#",
        # C++
        "c++": "C++",
        "cpp": "C++",
        # C
        "c언어": "C",
        # Java
        "java": "Java",
        "자바": "Java",
        # JavaScript
        "javascript": "JavaScript",
        "js": "JavaScript",
        "자바스크립트": "JavaScript",
        # TypeScript
        "typescript": "TypeScript",
        "ts": "TypeScript",
        # Go
        "golang": "Go",
        "go": "Go",
        # Rust
        "rust": "Rust",
        "러스트": "Rust",
        # Ruby
        "ruby": "Ruby",
        "루비": "Ruby",
        # PHP
        "php": "PHP",
        # Swift
        "swift": "Swift",
        # Kotlin
        "kotlin": "Kotlin",
        "코틀린": "Kotlin",
        # React
        "react": "React",
        "리액트": "React",
        # Node.js
        "node.js": "Node.js",
        "node": "Node.js",
        "nodejs": "Node.js",
        # .NET
        ".net": ".NET",
        "dotnet": ".NET",
    }

    # 스택 컨텍스트 패턴 (여러 언어 추출용)
    STACK_CONTEXT_PATTERN = re.compile(
        r'(?:기술\s*스택|stack|language|언어)[^:：.\n]*[:：]?\s*([^.\n]+)',
        re.IGNORECASE
    )

    def extract(self, normalized_text: str, sentences: list[str]) -> Optional[ExtractResult]:
        """텍스트에서 기술 스택 정보를 추출한다."""

        found_stacks: list[str] = []
        evidence_parts: list[str] = []
        text_lower = normalized_text.lower()

        # 우선순위가 높은 패턴 (명시적 언어 지정)
        # "Python only", "Python, C# 혼용"
        only_pattern = re.compile(r'(\w+)\s+only\b', re.IGNORECASE)
        only_match = only_pattern.search(normalized_text)
        if only_match:
            candidate = only_match.group(1).lower()
            if candidate in self.STACK_MAP:
                found_stacks.append(self.STACK_MAP[candidate])
                evidence_parts.append(only_match.group(0))

        # 모든 키워드 스캔
        for keyword, stack in self.STACK_MAP.items():
            # 이미 추가된 스택은 건너뛰기
            if stack in found_stacks:
                continue

            # 키워드 검색 (단어 경계 고려)
            if self._keyword_exists(keyword, text_lower, normalized_text):
                found_stacks.append(stack)
                # evidence 찾기
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                match = pattern.search(normalized_text)
                if match:
                    evidence_parts.append(match.group(0))

        if not found_stacks:
            return None

        return ExtractResult(
            value=found_stacks,
            confidence=0.9,
            evidence=", ".join(evidence_parts),
            extractor=self.name
        )

    def _keyword_exists(self, keyword: str, text_lower: str, original_text: str) -> bool:
        """키워드가 텍스트에 존재하는지 확인 (단어 경계 고려)"""

        # 특수문자가 포함된 키워드 (c#, c++, .net 등)
        if any(c in keyword for c in ['#', '+', '.']):
            return keyword in text_lower

        # 한글 키워드는 단순 포함 여부 확인 (단어 경계 개념이 다름)
        if any('\uac00' <= c <= '\ud7a3' for c in keyword):
            return keyword in text_lower

        # 영문 키워드는 단어 경계 확인
        # "py"가 "python"의 일부로 매칭되지 않도록
        pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
        return bool(pattern.search(original_text))
