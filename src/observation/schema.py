"""
Observer 정량 데이터 스키마

이 스키마는 Observer 파이프라인의 출력 계약(contract)이다.
Reasoner/Proposer는 이 구조 데이터만 사용한다.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Unknown:
    """미확인 정보 항목"""
    question: str      # 사용자에게 물어볼 질문
    reason: str        # 왜 필요한지
    evidence: str      # 입력 중 관련 문장/근거


@dataclass
class ExtractResult:
    """개별 추출기의 결과"""
    value: any                     # 추출된 값
    confidence: float              # 0.0 ~ 1.0
    evidence: str                  # 추출 근거 (원문)
    extractor: str = ""            # 추출기 이름


@dataclass
class ObservationResult:
    """
    Observer 파이프라인의 최종 출력 스키마

    이 스키마는 이후 단계에서도 절대 깨지지 않는 계약(interface)이다.
    """

    # === Meta ===
    raw_input: str                           # 원본 입력
    lang_mix_ratio: float = 0.0              # 0.0(전부 한글) ~ 1.0(전부 영어)
    tokens_estimate: int = 0                 # 추정 토큰 수

    # === Project ===
    domain: Optional[str] = None             # 프로젝트 도메인
    deadline_days: Optional[int] = None      # 마감까지 남은 일수
    team_size: Optional[int] = None          # 팀 인원 (단일값)
    team_size_min: Optional[int] = None      # 팀 인원 최소 (범위 입력 시)
    team_size_max: Optional[int] = None      # 팀 인원 최대 (범위 입력 시)
    budget_level: Optional[str] = None       # LOW / MID / HIGH

    # === Requirements ===
    must_have: list[str] = field(default_factory=list)       # 필수 요구사항
    nice_to_have: list[str] = field(default_factory=list)    # 선택 요구사항
    interfaces: list[str] = field(default_factory=list)      # 연동/인터페이스

    # === Constraints ===
    platform: Optional[str] = None                           # 플랫폼 제약
    language_stack: list[str] = field(default_factory=list)  # 기술 스택
    forbidden: list[str] = field(default_factory=list)       # 금지 사항

    # === Risk Signals (0~100) ===
    ambiguity_score: int = 0                 # 모호성 점수
    scope_volatility_score: int = 0          # 범위 변동성 점수
    integration_complexity_score: int = 0    # 연동 복잡도 점수

    # === Unknowns ===
    unknowns: list[Unknown] = field(default_factory=list)

    # === Extraction Details (디버깅/추적용) ===
    extractions: list[ExtractResult] = field(default_factory=list)
