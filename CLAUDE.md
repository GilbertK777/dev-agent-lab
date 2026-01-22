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

## 프로젝트 구조

```
dev-agent-lab/
├── CLAUDE.md                          # AI 어시스턴트 가이드라인
├── README.md                          # 프로젝트 문서
├── test.py                            # JSON 기반 테스트 러너
│
├── src/
│   ├── main.py                        # CLI 진입점 및 출력 포맷터
│   │
│   ├── observation/                   # 관찰 단계 (v2 파이프라인)
│   │   ├── __init__.py
│   │   ├── normalizer.py              # 보존적 텍스트 정규화 (Lossless)
│   │   ├── observer.py                # 관찰 파이프라인 조율
│   │   ├── schema.py                  # ObservationResult 스키마
│   │   └── extractors/                # 정보 추출기
│   │       ├── __init__.py
│   │       ├── base.py                # BaseExtractor 추상 클래스
│   │       ├── deadline_extractor.py  # 일정/기간 추출 (문장 스캔 + 합산)
│   │       └── team_extractor.py      # 팀 인원 추출 (단일값/범위)
│   │
│   ├── reasoning/                     # 판단 단계
│   │   ├── __init__.py
│   │   └── reasoner.py                # 트레이드오프 분석
│   │
│   └── proposal/                      # 제안 단계
│       ├── __init__.py
│       └── proposer.py                # 추천 및 다음 고려사항 생성
│
└── tests/
    ├── test_observer_v2.py            # Observer v2 유닛 테스트 (39개)
    ├── test_policy.py                 # 정책 통합 테스트
    └── fixtures/
        ├── test_inputs.json           # 테스트 입력 데이터
        └── test_results.json          # 테스트 실행 결과
```

### 핵심 파이프라인

```
사용자 입력 → Normalizer → Extractors → Observer → Reasoner → Proposer → 출력
                 │              │
                 │              ├── DeadlineExtractor (일정)
                 │              └── TeamExtractor (인원)
                 │
                 └── Lossless 정규화 (형태 정리, 의미 보존)
```

### 주요 모듈 설명

| 모듈 | 역할 |
|------|------|
| `normalizer.py` | 텍스트 형태 정리 (공백, 숫자-단위 분리). 단어 치환 금지. |
| `deadline_extractor.py` | 년/월/주/일 개별 스캔 후 합산. "1 year and 3 months" → 455일 |
| `team_extractor.py` | 단일값(5명) 또는 범위(2~3명) 추출 |
| `observer.py` | 추출기 결과 통합, unknowns 자동 생성, ambiguity 점수 계산 |
| `reasoner.py` | Pros/Cons/Assumptions/Constraints 분석 |
| `proposer.py` | 추천, 근거, 다음 고려사항, 인간 결정 안내 생성 |

