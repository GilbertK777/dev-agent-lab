"""
Base Extractor 인터페이스

모든 Extractor는 이 인터페이스를 따른다.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ExtractResult:
    """추출 결과"""
    value: Any                      # 추출된 값 (None이면 추출 실패)
    confidence: float               # 신뢰도 (0.0 ~ 1.0)
    evidence: str                   # 추출 근거 (원문에서 매칭된 부분)
    extractor: str = ""             # 추출기 이름


class BaseExtractor(ABC):
    """
    추출기 기본 클래스

    모든 추출기는 이 클래스를 상속받아 extract 메서드를 구현한다.
    """

    name: str = "base"

    @abstractmethod
    def extract(self, normalized_text: str, sentences: list[str]) -> Optional[ExtractResult]:
        """
        텍스트에서 값을 추출한다.

        Args:
            normalized_text: 정규화된 전체 텍스트
            sentences: 분리된 문장 리스트

        Returns:
            ExtractResult 또는 None (추출 실패 시)
        """
        pass
