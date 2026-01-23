"""
Platform Extractor

플랫폼/환경 정보 추출기:
- Windows, Linux, macOS, WSL 등 감지
- "Target environment", "Platform", "플랫폼", "환경" 키워드 기반

지원 형식:
- "Platform은 Windows 기반이고"
- "Target environment is Linux (WSL)"
- "Windows 환경에서 동작"
"""

import re
from typing import Optional

from src.observation.extractors.base import BaseExtractor, ExtractResult


class PlatformExtractor(BaseExtractor):
    """플랫폼/환경 추출기"""

    name = "platform"

    # 플랫폼 키워드 (정규화된 이름으로 매핑)
    PLATFORM_MAP = {
        # Windows
        "windows": "Windows",
        "win": "Windows",
        "윈도우": "Windows",
        "윈도": "Windows",
        # Linux
        "linux": "Linux",
        "리눅스": "Linux",
        "ubuntu": "Linux",
        "centos": "Linux",
        "debian": "Linux",
        # macOS
        "macos": "macOS",
        "mac os": "macOS",
        "osx": "macOS",
        "mac": "macOS",
        "맥": "macOS",
        # WSL (Windows Subsystem for Linux)
        "wsl": "Linux",  # WSL은 Linux로 간주
        # Cross-platform
        "cross-platform": "Cross-platform",
        "크로스플랫폼": "Cross-platform",
        "멀티플랫폼": "Cross-platform",
    }

    # 플랫폼 컨텍스트 패턴
    CONTEXT_PATTERNS = [
        # "Platform은 Windows 기반이고"
        re.compile(
            r'[Pp]latform[은는]?\s+(\w+)',
            re.IGNORECASE
        ),
        # "Target environment is Linux"
        re.compile(
            r'[Tt]arget\s+environment[은는]?\s+(?:is\s+)?(\w+)',
            re.IGNORECASE
        ),
        # "Windows 기반", "Linux 환경"
        re.compile(
            r'(\w+)\s+(?:기반|환경|based|environment)',
            re.IGNORECASE
        ),
        # "on Windows", "on Linux"
        re.compile(
            r'on\s+(\w+)',
            re.IGNORECASE
        ),
    ]

    def extract(self, normalized_text: str, sentences: list[str]) -> Optional[ExtractResult]:
        """텍스트에서 플랫폼 정보를 추출한다."""

        text_lower = normalized_text.lower()

        # 1. 컨텍스트 패턴으로 먼저 시도
        for pattern in self.CONTEXT_PATTERNS:
            match = pattern.search(normalized_text)
            if match:
                candidate = match.group(1).lower()
                if candidate in self.PLATFORM_MAP:
                    return ExtractResult(
                        value=self.PLATFORM_MAP[candidate],
                        confidence=0.95,
                        evidence=match.group(0).strip(),
                        extractor=self.name
                    )

        # 2. 직접 키워드 매칭
        for keyword, platform in self.PLATFORM_MAP.items():
            if keyword in text_lower:
                # evidence 찾기
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                match = pattern.search(normalized_text)
                evidence = match.group(0) if match else keyword

                return ExtractResult(
                    value=platform,
                    confidence=0.85,
                    evidence=evidence,
                    extractor=self.name
                )

        return None
