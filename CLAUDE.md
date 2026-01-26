# CLAUDE.md

이 파일은 이 프로젝트에서 작업하는 Claude(또는 AI 어시스턴트)를 위한 가이드라인입니다.

## 프로젝트 개요

**dev-agent-lab**은 의사결정 지원 Agent를 만들기 위한 학습 프로젝트입니다.

목표는 개발자가 소프트웨어 아키텍처 결정을 스스로 판단할 수 있도록 돕는 것이며,
코딩을 자동화하거나 개발자 대신 결정을 내리는 것이 아닙니다.

## Agent의 목적

Agent는 개발자를 위한 **소프트웨어 아키텍처 결정** 맥락에서 동작합니다.

다음과 같은 아키텍처 트레이드오프를 돕습니다:
- 모놀리스 vs 마이크로서비스 선택
- 경계나 추상화를 어디에 도입할지 결정
- 맥락에 따른 패턴의 장단점 평가

Agent는 개발자가 **선택지를 스스로 검토**할 수 있도록 돕습니다. 자동으로 답을 선택하지 않습니다.

## Agent의 경계

### Agent가 해서는 안 되는 것:
- 개발자 대신 최종 결정을 내리기
- 승인 없이 코드를 자동 실행하거나 파일을 수정하기
- 누락된 맥락이나 요구사항을 임의로 가정하기
- 테스트가 없는 로직 변경을 제안하거나 수행하기

### Agent가 해야 하는 것:
- 명확한 근거와 함께 추천 제시하기
- 최종 결정권이 사람에게 있음을 명시하기
- 중요한 맥락이 누락되었을 때 명확화 질문하기
- 맥락이 충분할 때 가정을 명시한 초기 분석 제공하기

## 출력 가이드라인

### 구조
트레이드오프를 제시할 때 기본적으로 구조화된 형식을 사용합니다:
- 장점
- 단점
- 가정
- 제약조건

상황에 따라 구조가 조정될 수 있지만, 추론은 항상 명확해야 합니다.

### 추천
Agent는 "X를 추천합니다" 또는 "X가 더 적합해 보입니다"라고 말할 수 있지만, 반드시:
- 추천에 대한 근거를 포함해야 합니다
- 최종 결정권이 사람에게 있음을 명확히 해야 합니다

추천은 안내이지, 권위가 아닙니다.

### 불확실성 처리
불확실할 때 Agent는:
- 불확실성을 명시적으로 표현해야 합니다
- 가정과 누락된 정보를 강조해야 합니다
- 적절한 경우 신뢰도 수준을 표시해야 합니다
- 과신하는 답변을 피해야 합니다

---

## 작업 원칙 (Claude Code / AI 어시스턴트)

### 작업 범위 제한 (중요)
- **repo 내부만 작업**합니다. 상위 디렉토리/루트 스캔(예: `/home`, `/`)은 금지합니다.
- 파일 탐색은 필요한 경로만 최소로 읽습니다.

### 변경 규율
- “테스트 추가/수정 → 구현 수정 → 전체 테스트 실행 → 결과 요약” 순서를 지킵니다.
- **커밋은 사용자가 명시적으로 요청할 때만** 수행합니다.
- 기존 테스트(test_1~test_4 포함)는 기본적으로 유지하며, 회귀를 막습니다.

### 실행 환경 고정 (WSL + venv)
- Python 실행은 **반드시 venv(.venv) 우선**:
  - `.venv/bin/python -m pytest -v`
  - `.venv/bin/python test.py`
  - `.venv/bin/python -m src.main`
- 시스템 Python(`/usr/bin/python3`)과 혼용하지 않습니다.

---

## 프로젝트 구조 (업데이트됨)

```
dev-agent-lab/
├── CLAUDE.md                          # AI 어시스턴트 가이드라인
├── README.md                          # 프로젝트 문서
├── test.py                            # JSON 기반 시나리오 테스트 러너
│
├── src/
│   ├── main.py                        # CLI 진입점 및 출력 포맷터
│   │
│   ├── observation/                   # 관찰 단계 (v2 파이프라인)
│   │   ├── __init__.py
│   │   ├── normalizer.py              # 보존적 텍스트 정규화 (Lossless)
│   │   ├── schema.py                  # ObservationResult/Extraction/Unknown 스키마
│   │   ├── observer.py                # 파이프라인 오케스트레이터 + ambiguity/unknowns
│   │   └── extractors/                # 정보 추출기 (단일 책임)
│   │       ├── __init__.py
│   │       ├── base.py                # BaseExtractor 추상 클래스
│   │       ├── utils.py               # 공통 유틸(항목 분리/정리 등)
│   │       ├── deadline_extractor.py  # 일정/기간 추출 (일수 변환)
│   │       ├── team_extractor.py      # 팀 인원 추출 (단일값/범위)
│   │       ├── requirements_extractor.py # Must/Nice 섹션 기반 요구사항 추출
│   │       ├── platform_extractor.py  # OS/플랫폼 추출 (Windows/Linux/WSL 등)
│   │       ├── stack_extractor.py     # 언어/기술 스택 추출 (Python/C#/C++ 등)
│   │       └── forbidden_extractor.py # 금지(Forbidden) 항목 추출 (예: LLM)
│   │
│   ├── reasoning/                     # 판단 단계
│   │   ├── __init__.py
│   │   ├── reasoner.py                # Pros/Cons/Assumptions/Constraints/Warnings 생성
│   │   └── rules/                     # Rule Engine Lite
│   │       ├── base.py                # Rule Protocol, RuleContext
│   │       ├── engine.py              # RuleEngine (규칙 순차 실행)
│   │       └── budget_rule.py         # BudgetConstraintRule (예산 제약 규칙)
│   │
│   └── proposal/                      # 제안 단계
│       ├── __init__.py
│       └── proposer.py                # 추천/근거/다음 고려사항 생성
│
└── tests/
    ├── test_observer_v2.py            # Observer v2 유닛 테스트
    ├── test_policy.py                 # 정책(헌법) 통합 테스트
    └── fixtures/
        ├── test_inputs.json           # 테스트 입력 데이터 (test_1~test_4)
        └── test_results.json          # 테스트 실행 결과
```

### 핵심 파이프라인 (v2)

```
사용자 입력 → observe_v2() → reason() → propose() → 출력
                  │              │
                  │              └── RuleEngine Lite
                  │                   ├── BudgetConstraintRule
                  │                   └── (추가 규칙 확장 가능)
                  │
                  ├── Normalizer (Lossless)
                  └── Extractors
                       ├── DeadlineExtractor (일정)
                       ├── TeamExtractor (인원)
                       ├── RequirementsExtractor (Must/Nice)
                       ├── PlatformExtractor (플랫폼)
                       ├── StackExtractor (스택)
                       └── ForbiddenExtractor (금지)
```

- Normalizer는 **형태만 정리**하고 의미는 보존합니다.
- Extractors는 문맥을 해석하지 않으며, 규칙에 따라 신호만 추출합니다.
- Observer는 결과를 통합하고 **unknowns / ambiguity**를 계산합니다.
- Reasoner는 **RuleEngine Lite**를 통해 규칙 기반 분석을 수행합니다.
- Proposer는 **결정을 강요하지 않습니다.**

---

## 주요 모듈 설명

| 모듈 | 역할 |
|------|------|
| `normalizer.py` | 텍스트 형태 정리 (공백, 숫자-단위 분리). **단어 치환/의미 변형 최소화** |
| `schema.py` | ObservationResult / Extraction / Unknown 등 결과 스키마 |
| `deadline_extractor.py` | 년/월/주/일 스캔 → 일수 변환 및 합산 |
| `team_extractor.py` | 단일값(5명) 또는 범위(2~4명) 추출 |
| `requirements_extractor.py` | Must/Nice/Core requirement 섹션 감지 후 항목 리스트 추출 |
| `platform_extractor.py` | OS/환경(Windows/Linux/WSL) 추출 |
| `stack_extractor.py` | 언어/기술 스택(Python/C#/C++) 추출 |
| `forbidden_extractor.py` | 금지 항목(예: LLM forbidden) 추출 |
| `observer.py` | 추출 결과 통합, unknowns 자동 생성, ambiguity 점수 계산 |
| `reasoner.py` | Pros/Cons/Assumptions/Constraints/Warnings 분석 |
| `proposer.py` | 추천, 근거, 다음 고려사항, "최종 결정은 인간" 고지 |
| `rules/base.py` | Rule Protocol, RuleContext 정의 |
| `rules/engine.py` | RuleEngine (규칙 순차 실행) |
| `rules/budget_rule.py` | BudgetConstraintRule (예산 제약 규칙) |

---

## (추가) Low-Confidence 경고 정책

추출 결과의 신뢰도(confidence)에 따라 경고를 생성합니다:

| 조건 | 동작 |
|------|------|
| `confidence < 0.7` | `Analysis.assumptions`에 구체 경고 (추출기 이름 명시) |
| `confidence < 0.8` | `Analysis.warnings`에 요약 경고 |

예시:
- assumptions: `"[주의] 일부 추출 결과(deadline)의 신뢰도가 낮아 확인이 필요합니다."`
- warnings: `"일부 추출 결과의 신뢰도가 낮습니다. 추가 확인이 필요합니다."`

---

## (추가) 작업 규칙 (diff 기반)

- **diff 기반 작업**: 전체 파일을 읽지 말고, 변경이 필요한 부분만 최소로 수정합니다.
- **한 커밋 = 한 목적**: 여러 목적의 변경을 하나의 커밋에 섞지 않습니다.
- **전체 리딩 금지**: 탐색은 필요한 범위만 최소로 수행합니다.

---

## (추가) Rule-based 시스템에 대한 명시적 원칙

이 프로젝트는 **자연어를 완벽히 이해하는 것을 목표로 하지 않습니다.**

- Rule 기반으로 확정 가능한 것만 확정합니다.
- 확정할 수 없는 것은 **unknowns로 남깁니다.**
- 테스트 없이 로직을 수정하는 것은 금지합니다.
- 복잡한 입력은 **섹션 기반(Must / Nice / Constraints)** 으로 점진적 처리합니다.
- ambiguity는 입력 자체의 모호함 수준을 의미합니다.
- unknowns는 판단을 위해 반드시 확인해야 할 질문 목록입니다.

---

## (추가) Evidence 문자열 품질 원칙 (표현만 개선)

목표:
- must_have_evidence / nice_to_have_evidence / forbidden_evidence의
  공백·개행 깨짐을 정리하여 사람이 읽기 자연스럽게 만듭니다.

규칙:
- **추출 로직(무엇을 잡는지)은 변경하지 말고**, evidence 저장 직전에만 후처리합니다.
- 다음을 만족해야 합니다:
  - `:` 뒤에는 항상 공백 1칸
  - 아래 토큰 뒤에는 공백 1칸(붙어 있으면 분리)
    - 한글 조사/연결: `은/는/이/가/을/를/과/와/및/또는/그리고/이고/이며/로/으로/로는/으로는`
    - 영어 연결/동사: `is/are/was/were/be/been/being/has/have/had`
    - 영어 포함/열거: `include/includes/included/including`
  - 연속 공백은 1칸으로 축소
  - 줄바꿈은 제거하거나 1줄로 정리

예시:
- ❌ `Core requirement isrule-based analysis`
- ✅ `Core requirement is rule-based analysis`

---

## (추가) ambiguity_score 설계 원칙

목표:
- 점수가 특정 값으로 몰리지 않도록(예: 44/60 고정) 분산되며,
  상대 비교가 가능해야 합니다.

기본 방향:
- 불확실성 키워드는 유지하되, 보너스/가중치에 상한을 두고,
  구조화된 요구사항이 잘 잡힌 입력은 **감점(안정화)** 할 수 있습니다.
- 점수 범위는 0~100을 유지합니다.
- (예시 기대) `test_2 > test_4 > test_1`

---

## (추가) team_size 범위 unknowns 질문 원칙

목표:
- team_size가 범위로 주어질 때 입력의 뉘앙스를 반영한 자연스러운 확인 질문을 생성합니다.

규칙:
- team_extractor(범위 추출) 로직은 변경하지 않습니다.
- unknowns 질문 생성부만 개선합니다.
- 입력에 `ideally / preferred / 선호` 등이 있으면 질문에 반드시 반영합니다.

예시:
- 입력: `team size is 2~4, ideally 3`
- 질문:
  `팀 인원은 2~4명 범위로 보이며, 이상적으로는 3명을 선호하는 것으로 보입니다. 초기 기준 인원을 3명으로 확정해도 될까요?`

---

## (추가) 프로젝트 완료 기준 (Definition of Done – v1.0)

다음 조건을 만족하면 `dev-agent-lab v1.0`으로 간주합니다:

- Observation 단계는 Rule-based로만 구현하며, LLM에 의존하지 않음
- 요구사항 구조화 안정화
- platform / stack / forbidden 추출 안정화
- ambiguity / unknowns 질문 생성 가능
- 복합 입력(test_4 수준)에서 must/nice/constraints가 섞이지 않고 분리됨
- 모든 테스트 통과
- “연습용”이 아닌 **참고 구현(reference)** 으로 설명 가능

---

## 마지막 원칙

이 프로젝트의 성공 기준은 다음과 같습니다:

> “모든 입력을 완벽히 처리하는 것”이 아니라  
> **어디까지 Rule로 가능하고, 어디서 인간 판단이 필요한지를 명확히 드러내는 것**
