# dev-agent-lab

의사결정 지원 Agent를 만들기 위한 학습 프로젝트입니다.

## 목적

이 프로젝트는 개발자가 소프트웨어 아키텍처 결정을 스스로 판단할 수 있도록 돕는
Agent를 만드는 방법을 탐구합니다. 결정을 자동화하는 것이 아니라,
구조화된 추론과 트레이드오프 분석에 초점을 맞춥니다.

## Agent가 하는 일

- 아키텍처 트레이드오프 평가 지원 (예: 모놀리스 vs 마이크로서비스)
- 장점, 단점, 가정, 제약조건과 함께 선택지 제시
- 명확한 근거와 함께 추천 제공
- 맥락이 부족할 때 명확화 질문

## Agent가 하지 않는 일

- 개발자 대신 최종 결정 내리기
- 코드 자동 실행 또는 파일 수정
- 누락된 맥락이나 요구사항 임의로 가정

---

## 아키텍처 개요

Agent는 3단계 파이프라인으로 동작합니다:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Observe   │ → │   Reason    │ → │   Propose   │
│ (맥락 수집)  │    │ (분석/추론)  │    │ (추천 생성)  │
└─────────────┘    └─────────────┘    └─────────────┘
```

| 단계 | 역할 | 출력 |
|------|------|------|
| **Observe** | 사용자 입력에서 정량화된 구조 데이터 추출 | `ObservationResult` |
| **Reason** | 트레이드오프 분석 및 가정/제약 정리 | `Analysis` |
| **Propose** | 선택지와 추천 생성 (최종 결정은 인간에게) | `Recommendation` |

---

## Observer v2 파이프라인

Observer는 자연어 입력을 정량화된 구조 데이터로 변환하는 5단계 파이프라인입니다.
**LLM 없이 규칙 기반(rule-based)으로만 동작합니다.**

### 파이프라인 구조

```
┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐
│ Normalize │ → │  Segment  │ → │  Extract  │ → │ Quantify  │ → │ Validate  │
└───────────┘   └───────────┘   └───────────┘   └───────────┘   └───────────┘
     ↓               ↓               ↓               ↓               ↓
  한영 정규화      문장 분리       필드별 추출     점수/수치화    unknowns 생성
```

### 각 단계 설명

| 단계 | 설명 | 예시 |
|------|------|------|
| **Normalize** | 동의어 사전으로 한영 표현 통일 (번역 X) | "deadline" → `DEADLINE`, "마감" → `DEADLINE` |
| **Segment** | 문장/불릿/섹션 분리 | "A입니다. B입니다" → `["A입니다", "B입니다"]` |
| **Extract** | 플러그인 추출기로 필드별 값 추출 | "3개월" → `deadline_days=90` |
| **Quantify** | 모호성 점수 계산 (0~100) | unknowns 많으면 점수 ↑ |
| **Validate** | 누락/충돌 감지 → unknowns 생성 | deadline 없음 → "마감일이 언제인가요?" |

### 지원 필드

#### 일정 (Deadline)

| 형식 | 예시 | 변환 결과 |
|------|------|----------|
| 년+개월 복합 | "1년 6개월" | 545일 |
| 년 단위 | "2년", "2 years" | 730일 |
| 개월 단위 | "3개월", "3 months" | 90일 |
| 주 단위 | "2주", "2 weeks" | 14일 |
| 일 단위 | "10일", "10 days" | 10일 |
| D+N 형식 | "D+14", "D-7" | 14일, 7일 |

#### 팀 인원 (Team Size)

| 형식 | 예시 | 변환 결과 |
|------|------|----------|
| 인원 형식 | "인원은 5명" | 5 |
| 팀 형식 | "팀 3명", "팀은 3명" | 3 |
| 개발자 형식 | "개발자 5명" | 5 |
| 영어 형식 | "team of 4", "5 developers" | 4, 5 |
| 약어 형식 | "5 ppl" | 5 |

### 출력 스키마

```python
@dataclass
class ObservationResult:
    raw_input: str                    # 원본 입력
    lang_mix_ratio: float             # 한영 혼합 비율 (0.0~1.0)
    tokens_estimate: int              # 토큰 수 추정

    # 정량화된 필드
    deadline_days: Optional[int]      # 일정 (일수)
    team_size: Optional[int]          # 팀 인원 (명)

    # 요구사항
    must_have: list[str]              # 필수 요구사항

    # 점수
    ambiguity_score: int              # 모호성 점수 (0~100)

    # 미확인 정보
    unknowns: list[Unknown]           # 자동 생성된 질문
    extractions: list[ExtractResult]  # 추출 결과 (신뢰도 포함)
```

### 사용 예시

```python
from src.observation.observer import observe_v2

# 한영 혼합 입력
result = observe_v2("인원은 2명이고 기간은 1년 6개월")

print(result.team_size)        # 2
print(result.deadline_days)    # 545 (1*365 + 6*30)
print(result.ambiguity_score)  # 0 (명확한 입력)
print(result.unknowns)         # [] (누락 없음)

# 모호한 입력
result = observe_v2("아마 웹사이트를 만들어야 할 것 같아요")

print(result.team_size)        # None
print(result.deadline_days)    # None
print(result.ambiguity_score)  # 높음 (필수 정보 누락)
print(result.unknowns)         # [Unknown(question="마감일이..."), ...]
```

### Legacy 호환성

기존 코드와의 호환성을 위해 `observe()` 함수도 유지됩니다:

```python
from src.observation.observer import observe

# Legacy 방식 (v0/v1 호환)
result = observe("인원은 2명이고 기간은 1년 6개월")

print(result.constraints)  # ['[인력] 팀 2명', '[일정] 1년 6개월']
print(result.unknowns)     # []
```

---

## 프로젝트 구조

```
dev-agent-lab/
├── src/
│   ├── observation/
│   │   ├── observer.py           # 파이프라인 오케스트레이터
│   │   ├── schema.py             # ObservationResult, Unknown, ExtractResult
│   │   ├── normalizer.py         # 동의어 사전 + 한영 정규화
│   │   └── extractors/
│   │       ├── base.py           # BaseExtractor 인터페이스
│   │       ├── deadline_extractor.py   # 일정 추출기
│   │       └── team_extractor.py       # 팀 인원 추출기
│   ├── reasoning/
│   │   └── reasoner.py           # 트레이드오프 분석
│   └── proposal/
│       └── proposer.py           # 추천 생성
├── tests/
│   ├── test_policy.py            # 정책 테스트 (v0)
│   └── test_observer_v2.py       # Observer v2 테스트 (24개)
├── CLAUDE.md                     # AI 어시스턴트 가이드라인
└── README.md
```

---

## 테스트

```bash
# 가상환경 활성화
source .venv/bin/activate

# 전체 테스트 실행
pytest -v

# Observer v2 테스트만 실행
pytest tests/test_observer_v2.py -v
```

### 테스트 커버리지

| 카테고리 | 테스트 항목 |
|----------|-------------|
| Deadline 추출 | 한글/영어/복합 형식, D+N 형식 |
| Team Size 추출 | 인원/팀/개발자/ppl 형식 |
| 한영 혼합 | 동시 추출 정확도 |
| Unknowns 생성 | 필수 필드 누락 시 자동 질문 |
| Ambiguity Score | 0~100 범위, 명확/모호 입력 구분 |
| Legacy 호환성 | observe() 함수 동작 확인 |

---

## 기술 스택

- Python 3.12+
- 표준 라이브러리 선호
- pytest (테스트)
- **LLM 미사용** (규칙 기반)

## 핵심 원칙

> 확신이 없을 때는 속도나 완성도보다 명확성과 설명을 우선하세요.

## 라이선스

추후 결정
