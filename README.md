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
- 맥락이 부족할 때 명확화 질문(unknowns) 생성

## Agent가 하지 않는 일

- 개발자 대신 최종 결정 내리기
- 승인 없이 코드 자동 실행 또는 파일 수정
- 누락된 맥락이나 요구사항 임의로 가정
- 테스트 없이 로직을 변경하기

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
| **Observe** | 사용자 입력에서 정량화된 구조 데이터 추출 (rule-based) | `ObservationResult` |
| **Reason** | 트레이드오프 분석 및 가정/제약 정리 | `Analysis` |
| **Propose** | 선택지와 추천 생성 (**최종 결정은 인간**) | `Recommendation` |

---

## Observer v2 파이프라인 (Rule-based Only)

Observer는 자연어 입력을 정량화된 구조 데이터로 변환하는 파이프라인입니다.  
**LLM 없이 규칙 기반(rule-based)으로만 동작합니다.**

### 파이프라인 구조(개념)

```
┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐
│ Normalize │ → │  Segment  │ → │  Extract  │ → │ Quantify  │ → │ Validate  │
└───────────┘   └───────────┘   └───────────┘   └───────────┘   └───────────┘
     ↓               ↓               ↓               ↓               ↓
  형태 정리        문장/섹션      필드별 추출     점수/수치화    unknowns 생성
```

> 구현은 `src/observation/observer.py`가 오케스트레이션을 담당하고,  
> `src/observation/extractors/*`가 필드별 단일 책임 추출을 담당합니다.

### 지원 필드(현재)

- **기간/일정**: `deadline_days`
- **팀 인원**: `team_size` 또는 범위(`team_size_min`, `team_size_max`)
- **요구사항**: `must_have`, `nice_to_have` (섹션 기반 파싱)
- **플랫폼**: `platform` (Windows/Linux/WSL 등)
- **언어/기술 스택**: `stack` (Python/C#/C++ 등)
- **금지 항목**: `forbidden` (예: `LLM`)
- **품질/불확실성**: `ambiguity_score`, `unknowns`
- **추출 근거/신뢰도**: `extractions` (extractor 이름/값/근거(evidence)/confidence)

---

## Deadline(기간) 추출

| 형식 | 예시 | 변환 결과(일수) |
|------|------|----------------|
| 년+개월 복합(한글) | `1년 6개월` | 545일 (1*365 + 6*30) |
| 년+개월 복합(영문) | `1 year and 3 months` | 455일 |
| 년 단위 | `2년`, `2 years` | 730일 |
| 개월 단위 | `3개월`, `3 months` | 90일 |
| 주 단위 | `2주`, `2 weeks` | 14일 |
| 일 단위 | `10일`, `10 days` | 10일 |
| D±N 형식 | `D+14`, `D-7` | 14일, 7일 |

---

## Team Size(팀 인원) 추출

| 형식 | 예시 | 변환 결과 |
|------|------|----------|
| 단일값 | `팀은 3명`, `5 developers`, `5 ppl` | `team_size=3/5` |
| 범위 | `2~3명`, `2-4 people` | `team_size_min=2, team_size_max=4` |

> 범위 입력은 **unknowns 질문**을 통해 “초기 기준 인원 확정”을 유도합니다.  
> 입력에 `ideally / preferred / 선호` 등이 있으면 질문에 반영합니다.

---

## Requirements(Must/Nice) 추출

다음 형식을 우선적으로 지원합니다.

- `Must have 기능은 X, Y 이고 ...`
- `Nice to have 로는 A, B ...`
- `Must have: X, Y, Z.`
- `Nice to have: A, B.`
- `Core requirement is ...`
- `Nice features include ...`

항목 분리 기준(대표):
- `,` / `and` / `및` / `이고` 등

---

## 출력 스키마(요약)

실제 스키마는 `src/observation/schema.py`에 있습니다. 여기서는 핵심 필드만 요약합니다.

```python
@dataclass
class ObservationResult:
    raw_input: str

    # 정량화된 필드
    deadline_days: Optional[int]
    team_size: Optional[int]
    team_size_min: Optional[int]
    team_size_max: Optional[int]

    # 요구사항
    must_have: list[str]
    nice_to_have: list[str]

    # 환경/스택/금지
    platform: Optional[str]
    stack: list[str]
    forbidden: list[str]

    # 점수/미확인 정보
    ambiguity_score: int              # 0~100
    unknowns: list[Unknown]

    # 추출 근거(신뢰도/증거 문자열 포함)
    extractions: list[ExtractResult]
```

### Analysis (Reason 단계 출력)

```python
@dataclass
class Analysis:
    pros: list[str]          # 장점
    cons: list[str]          # 단점
    assumptions: list[str]   # 가정
    constraints: list[str]   # 제약
    warnings: list[str]      # 경고 (낮은 신뢰도 등)
```

### Proposal (Propose 단계 출력)

```python
@dataclass
class Proposal:
    recommendation: str          # 추천 내용
    rationale: str               # 추천 근거
    next_considerations: list[str]  # 다음 고려사항
    human_decision_note: str     # "최종 결정은 인간" 고지
```

---

## Unknowns 자동 생성 키워드

입력에 다음 키워드가 포함되면 해당 질문이 `unknowns`에 자동 추가됩니다:

| 키워드 | 생성되는 질문 |
|--------|--------------|
| `레거시`, `legacy` | 레거시 시스템과의 통합이 필요한가요? |
| `확장`, `scalab`, `scale` | 향후 확장 규모 예상치가 있나요? |
| `성능`, `performance` | 구체적인 성능 요구사항(응답시간, TPS 등)이 있나요? |
| `보안`, `security` | 보안 등급이나 인증 요구사항이 있나요? |
| `마이그레이션`, `migration` | 마이그레이션 전략이나 병행 운영 기간이 정해져 있나요? |

---

## 사용 예시

### 1) CLI 실행

```bash
.venv/bin/python -m src.main
```

### 2) Observer v2 단독 호출

```python
from src.observation.observer import observe_v2

result = observe_v2("인원은 2명이고 기간은 1년 6개월")
print(result.team_size)       # 2
print(result.deadline_days)   # 545
print(result.unknowns)        # []
```

### 3) JSON 시나리오 테스트 러너

`test.py`는 `tests/fixtures/test_inputs.json`을 읽어서 실행 결과를 출력하고,
`tests/fixtures/test_results.json`에 저장합니다.

```bash
.venv/bin/python test.py
```

---

## 프로젝트 구조 (업데이트됨)

```
dev-agent-lab/
├── CLAUDE.md                          # AI 어시스턴트 가이드라인(헌법)
├── README.md                          # 프로젝트 문서
├── test.py                            # JSON 기반 시나리오 테스트 러너
│
├── src/
│   ├── main.py                        # CLI 진입점 및 출력 포맷터
│   ├── observation/                   # 관찰 단계 (v2 파이프라인)
│   │   ├── normalizer.py              # 보존적 텍스트 정규화 (Lossless)
│   │   ├── schema.py                  # ObservationResult/Unknown/ExtractResult 스키마
│   │   ├── observer.py                # 파이프라인 통합 + ambiguity/unknowns
│   │   └── extractors/                # 필드별 추출기(단일 책임)
│   │       ├── base.py
│   │       ├── utils.py
│   │       ├── deadline_extractor.py
│   │       ├── team_extractor.py
│   │       ├── requirements_extractor.py
│   │       ├── platform_extractor.py
│   │       ├── stack_extractor.py
│   │       └── forbidden_extractor.py
│   ├── reasoning/                     # 판단 단계
│   │   ├── reasoner.py                # Pros/Cons/Assumptions/Constraints/Warnings 분석
│   │   └── rules/                     # Rule Engine Lite
│   │       ├── base.py                # Rule Protocol, RuleContext
│   │       ├── engine.py              # RuleEngine (규칙 순차 실행)
│   │       └── budget_rule.py         # BudgetConstraintRule
│   └── proposal/
│       └── proposer.py                # 추천/근거/다음고려사항 생성
│
└── tests/
    ├── test_policy.py                 # 정책(헌법) 테스트
    ├── test_observer_v2.py            # Observer v2 유닛 테스트
    └── fixtures/
        ├── test_inputs.json           # 시나리오 입력(test_1~test_4 등)
        └── test_results.json          # 시나리오 결과 저장
```

---

## 테스트

> **WSL + venv 기준으로 실행을 고정**합니다. (`python`/`python3` 혼용 금지)

```bash
# 전체 테스트 실행
.venv/bin/python -m pytest -v

# Observer v2 테스트만 실행
.venv/bin/python -m pytest tests/test_observer_v2.py -v

# JSON 시나리오 테스트 실행
.venv/bin/python test.py
```

### 테스트 커버리지(대표)

| 카테고리 | 테스트 항목 |
|----------|-------------|
| Deadline | 한글/영어/복합 형식, D±N |
| Team Size | 단일값/범위, 영문/혼합 |
| Requirements | Must/Nice 섹션 기반 추출 |
| Platform/Stack/Forbidden | 환경/스택/금지 항목 추출 |
| Unknowns | 범위/누락 입력에서 질문 생성 |
| Ambiguity | 0~100 범위 및 상대 비교 |
| Policy | “최종 결정은 인간” 등 헌법 준수 |

---

## 기술 스택

- Python 3.12+
- 표준 라이브러리 선호
- pytest (테스트)
- **LLM 미사용** (규칙 기반)

## 핵심 원칙

> 확신이 없을 때는 속도나 완성도보다 **명확성과 설명**을 우선하세요.

---

## v2.0 변경 요약

| 변경 | 설명 |
|------|------|
| ObservationResult 단일화 | Reasoning/Proposal이 ObservationResult 타입만 사용 |
| Rule Engine Lite | Reasoning 단계에 규칙 엔진 도입 (BudgetConstraintRule) |
| Analysis.warnings | 신뢰도 기반 경고 필드 추가 |
| Low-confidence 경고 | `confidence < 0.7` → assumptions, `< 0.8` → warnings |

### v2.0 Current Status
- Version: v1.1
- Rule-based Agent (LLM not connected yet)
- Observation: constraint extraction (team size, timeline, volatility) implemented
- Policy tests passing

## Roadmap

- [ ] ScopeVolatilityRule (범위 변동성 규칙)
- [ ] TeamUncertaintyRule (팀 불확실성 규칙)
- [ ] scope_volatility_score 계산 로직
- [ ] Reasoning 단위 테스트 추가

## 라이선스

추후 결정
