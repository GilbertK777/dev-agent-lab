# dev-agent-lab v2.0 설계 스펙

> 이 문서는 v2.0의 "설계 계약서"입니다. 구현 전 합의된 범위와 제약을 명시합니다.

---

## 1. Core Invariants (절대 불변 조건)

다음 조건은 v2.0에서도 **절대 변경하지 않습니다**:

| 항목 | 불변 조건 |
|------|-----------|
| 파이프라인 | `Observe → Reason → Propose` 3단계 순서 유지 |
| LLM 의존성 | Observer는 **rule-based only** (LLM 호출 금지) |
| 정규화 원칙 | Normalizer는 **lossless** (단어 의미 변경 금지, 형식만 정리) |
| 최종 결정권 | 모든 출력에 "최종 결정은 사람이 합니다" 명시 |
| 테스트 호환 | 기존 pytest 70개 테스트 100% 통과 유지 |

---

## 2. v2.0 핵심 설계 포인트 (3가지)

### 2.1 정량 기반 추출 강화
- **목표**: 사용자 입력에서 정량 데이터를 더 정확하게 추출
- **범위**: deadline, team_size, platform, stack, forbidden, requirements
- **지표**: ambiguity_score로 입력 품질 수치화

### 2.2 키워드 기반 Unknowns 자동 생성
- **목표**: 도메인 특화 키워드 감지 시 확인 질문 자동 생성
- **키워드 예**: SECS/GEM, traceability, audit logging, compliance, offline
- **출력**: 3~8개 수준의 맥락적 Unknowns

### 2.3 Constraints 출력 통합
- **목표**: Step2 추출값 + 운영제약을 Constraints 섹션에 통합 표시
- **포맷**: `[플랫폼]`, `[스택]`, `[금지]`, `[운영제약]` 태그 사용
- **원칙**: 추출 로직 변경 없이 표시(UI)만 개선

---

## 3. v1.x → v2.0 마이그레이션 단계

| 단계 | 작업 | 상태 |
|------|------|------|
| Step 1 | requirements를 항목 리스트로 추출 (must_have/nice_to_have) | 완료 |
| Step 2 | platform/stack/forbidden 추출기 추가 | 완료 |
| Step 2 보완 | evidence 후처리, ambiguity 스케일링, unknowns 템플릿 | 완료 |
| Step 3 | Constraints 출력 통합, 키워드 기반 Unknowns | 완료 |
| Step 4 | 문서화 및 최종 검증 | 완료 |

---

## 4. v2.0 Done Definition

v2.0 완료 조건 체크리스트:

- [x] pytest 72개 테스트 100% 통과
- [x] test_1 ~ test_5 모두 expected와 actual 일치
- [x] ambiguity_score 순서: test_5 > test_4 > test_1
- [x] Constraints 출력에 플랫폼/스택/금지/운영제약 포함
- [x] Unknowns 3개 이상 자동 생성 (도메인 키워드 기반)
- [x] Observer에 LLM 호출 없음 (rule-based only)
- [x] 모든 출력에 "최종 결정은 사람이 합니다" 문구 포함
- [x] docs/v2_plan.md 최종 확정
- [x] CLAUDE.md 프로젝트 구조 최신화 (Step 4에서)

---

*문서 버전: v2.0-final | 작성일: 2026-01-26*
