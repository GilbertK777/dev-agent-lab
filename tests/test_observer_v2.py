"""
Observer v2 Pipeline 테스트

테스트 항목:
1. 한글 입력 deadline 추출
2. 영어 입력 deadline 추출
3. 한영 혼합 입력
4. team_size 추출 정확도
5. unknowns 자동 생성
6. ambiguity_score 범위 검증
"""

import pytest

from src.observation.observer import observe_v2, observe
from src.observation.schema import ObservationResult


class TestDeadlineExtraction:
    """Deadline 추출 테스트"""

    def test_korean_deadline_months(self):
        """한글 개월 단위 추출"""
        result = observe_v2("프로젝트 기간은 3개월입니다")
        assert result.deadline_days == 90  # 3 * 30

    def test_korean_deadline_weeks(self):
        """한글 주 단위 추출"""
        result = observe_v2("마감까지 2주 남았습니다")
        assert result.deadline_days == 14  # 2 * 7

    def test_korean_deadline_year_month_combo(self):
        """한글 복합 기간 (1년 6개월) 추출"""
        result = observe_v2("인원은 2명이고 기간은 1년 6개월")
        assert result.deadline_days == 545  # 1*365 + 6*30 = 545

    def test_english_deadline_weeks(self):
        """영어 주 단위 추출"""
        result = observe_v2("deadline is 2 weeks")
        assert result.deadline_days == 14

    def test_english_deadline_months(self):
        """영어 개월 단위 추출"""
        result = observe_v2("we have 3 months to complete this")
        assert result.deadline_days == 90

    def test_d_plus_format(self):
        """D+N 형식 추출"""
        result = observe_v2("마감 D+14")
        assert result.deadline_days == 14


class TestTeamSizeExtraction:
    """Team Size 추출 테스트"""

    def test_korean_team_size_inwin(self):
        """'인원은 N명' 형식"""
        result = observe_v2("인원은 5명입니다")
        assert result.team_size == 5

    def test_korean_team_size_team(self):
        """'팀 N명' 형식"""
        result = observe_v2("팀은 3명이에요")
        assert result.team_size == 3

    def test_english_team_size(self):
        """영어 team size 추출"""
        result = observe_v2("team of 4 developers")
        assert result.team_size == 4

    def test_ppl_format(self):
        """'N ppl' 형식"""
        result = observe_v2("we have 5 ppl")
        assert result.team_size == 5


class TestMixedLanguageInput:
    """한영 혼합 입력 테스트"""

    def test_mixed_deadline_and_team(self):
        """한영 혼합: deadline과 team_size 모두 추출"""
        result = observe_v2("인원은 2명이고 기간은 1년 6개월")
        assert result.team_size == 2
        assert result.deadline_days == 545  # 1*365 + 6*30

    def test_mixed_english_korean(self):
        """영어 deadline + 한글 team"""
        result = observe_v2("deadline 3 weeks, 팀 4명")
        assert result.deadline_days == 21
        assert result.team_size == 4


class TestUnknownsGeneration:
    """Unknowns 자동 생성 테스트"""

    def test_unknowns_when_deadline_missing(self):
        """deadline 누락 시 unknown 생성"""
        result = observe_v2("팀은 3명입니다")
        assert result.team_size == 3
        assert result.deadline_days is None

        # deadline 관련 unknown이 생성되어야 함
        deadline_unknown = [u for u in result.unknowns if "마감" in u.question or "기간" in u.question]
        assert len(deadline_unknown) > 0

    def test_unknowns_when_team_missing(self):
        """team_size 누락 시 unknown 생성"""
        result = observe_v2("프로젝트 기간은 2개월")
        assert result.deadline_days == 60
        assert result.team_size is None

        # team 관련 unknown이 생성되어야 함
        team_unknown = [u for u in result.unknowns if "인원" in u.question or "팀" in u.question]
        assert len(team_unknown) > 0

    def test_unknowns_when_both_missing(self):
        """둘 다 누락 시 2개의 unknown 생성"""
        result = observe_v2("간단한 웹사이트를 만들고 싶어요")
        assert result.deadline_days is None
        assert result.team_size is None
        assert len(result.unknowns) >= 2


class TestAmbiguityScore:
    """Ambiguity Score 테스트"""

    def test_ambiguity_score_range(self):
        """ambiguity_score는 0~100 범위"""
        result = observe_v2("아마 2주 정도? 인원은 미정")
        assert 0 <= result.ambiguity_score <= 100

    def test_low_ambiguity_for_clear_input(self):
        """명확한 입력은 낮은 ambiguity"""
        result = observe_v2("인원은 5명이고 기간은 3개월입니다")
        # 모든 필수 정보가 있으므로 낮은 점수
        assert result.ambiguity_score < 50

    def test_high_ambiguity_for_vague_input(self):
        """모호한 입력은 높은 ambiguity"""
        result = observe_v2("아마 뭔가 만들어야 할 것 같은데 글쎄요")
        # 필수 정보 누락 + 불확실 키워드
        assert result.ambiguity_score > 30


class TestEmptyInput:
    """빈 입력 처리 테스트"""

    def test_empty_string(self):
        """빈 문자열 처리"""
        result = observe_v2("")
        assert len(result.unknowns) > 0
        assert "입력" in result.unknowns[0].question

    def test_whitespace_only(self):
        """공백만 있는 입력 처리"""
        result = observe_v2("   \n\t  ")
        assert len(result.unknowns) > 0


class TestLegacyCompatibility:
    """Legacy observe() 함수 호환성 테스트"""

    def test_legacy_observe_returns_observation(self):
        """observe()는 Observation 객체 반환"""
        result = observe("인원은 3명이고 기간은 2개월")
        # Legacy Observation 클래스의 필드 확인
        assert hasattr(result, "raw_input")
        assert hasattr(result, "requirements")
        assert hasattr(result, "constraints")
        assert hasattr(result, "unknowns")

    def test_legacy_constraints_format(self):
        """Legacy constraints 형식 확인"""
        result = observe("인원은 3명이고 기간은 2개월")
        # constraints에 [인력], [일정] 태그가 있어야 함
        constraint_text = " ".join(result.constraints)
        assert "[인력]" in constraint_text or "[일정]" in constraint_text


class TestExtractionConfidence:
    """추출 신뢰도 테스트"""

    def test_extractions_have_confidence(self):
        """추출 결과에 신뢰도 포함"""
        result = observe_v2("인원은 5명, 기간 3개월")
        assert len(result.extractions) > 0
        for extraction in result.extractions:
            assert 0.0 <= extraction.confidence <= 1.0

    def test_high_confidence_for_explicit_format(self):
        """명시적 형식은 높은 신뢰도"""
        result = observe_v2("인원은 5명입니다")
        team_extraction = [e for e in result.extractions if e.extractor == "team_size"]
        assert len(team_extraction) > 0
        assert team_extraction[0].confidence >= 0.9


class TestEnglishCompoundDeadline:
    """영어 복합 기간 테스트 (P0-A)"""

    def test_english_year_and_months(self):
        """'1 year and 3 months' 형식"""
        result = observe_v2("The expected timeline is 1 year and 3 months.")
        assert result.deadline_days is not None
        assert result.deadline_days > 400  # 1*365 + 3*30 = 455
        assert result.deadline_days == 455

    def test_english_year_months_no_and(self):
        """'2 years 6 months' 형식 (and 없음)"""
        result = observe_v2("Project duration is 2 years 6 months")
        assert result.deadline_days is not None
        assert result.deadline_days == 910  # 2*365 + 6*30

    def test_english_short_format(self):
        """'1yr 3mo' 축약 형식"""
        result = observe_v2("timeline: 1yr 3mo")
        assert result.deadline_days is not None
        assert result.deadline_days == 455


class TestNormalizerLossless:
    """Normalizer 보존적 정규화 테스트"""

    def test_no_uppercase_tokens_in_normalized(self):
        """정규화 결과에 대문자 토큰(YEARS, MONTHS 등)이 없어야 함"""
        from src.observation.normalizer import normalize

        text = "The timeline is 1 year and 3 months with a team of 5 people"
        result = normalize(text)

        # 대문자 토큰이 없어야 함
        assert "YEARS" not in result.normalized
        assert "MONTHS" not in result.normalized
        assert "TEAM" not in result.normalized
        assert "DEADLINE" not in result.normalized

    def test_original_text_preserved(self):
        """원문이 유지되어야 함"""
        from src.observation.normalizer import normalize

        text = "Project takes 6 months"
        result = normalize(text)

        # 원문 단어가 유지되어야 함
        assert "months" in result.normalized.lower()
        assert "6" in result.normalized

    def test_number_unit_spacing(self):
        """숫자와 단위 사이 공백 정리"""
        from src.observation.normalizer import normalize

        text = "timeline is 1year and 3months"
        result = normalize(text)

        # 숫자와 단위 사이 공백이 있어야 함
        assert "1 year" in result.normalized
        assert "3 months" in result.normalized


class TestTeamSizeRange:
    """팀 인원 범위 테스트 (P0-B)"""

    def test_korean_range_tilde(self):
        """'인원은 2~3명' 형식"""
        result = observe_v2("인원은 2~3명 정도로 flexible 하고")
        assert result.team_size is None  # 범위이므로 단일값 없음
        assert result.team_size_min == 2
        assert result.team_size_max == 3

    def test_korean_range_dash(self):
        """'2-3명' 형식"""
        result = observe_v2("팀은 2-3명입니다")
        assert result.team_size is None
        assert result.team_size_min == 2
        assert result.team_size_max == 3

    def test_english_range(self):
        """'2 to 3 people' 형식"""
        result = observe_v2("team size is 2 to 3 people")
        assert result.team_size is None
        assert result.team_size_min == 2
        assert result.team_size_max == 3

    def test_range_generates_unknown(self):
        """범위 입력 시 확정 질문 unknown 생성"""
        result = observe_v2("인원은 2~3명 정도입니다")
        assert result.team_size is None
        assert result.team_size_min == 2
        assert result.team_size_max == 3

        # 팀 규모 확정 관련 unknown이 생성되어야 함
        team_unknowns = [u for u in result.unknowns if "확정" in u.question or "결정" in u.question]
        assert len(team_unknowns) > 0

    def test_single_value_no_range(self):
        """단일값은 team_size에 저장, min/max는 None"""
        result = observe_v2("팀은 5명입니다")
        assert result.team_size == 5
        assert result.team_size_min is None
        assert result.team_size_max is None


class TestLegacyTeamRange:
    """Legacy observe()의 팀 범위 처리 테스트"""

    def test_legacy_range_constraint(self):
        """Legacy observe()에서 범위가 '확정 필요'로 표시"""
        result = observe("인원은 2~3명입니다")
        constraint_text = " ".join(result.constraints)
        assert "2~3명" in constraint_text
        assert "확정 필요" in constraint_text


class TestFullScenarios:
    """전체 시나리오 테스트 (3개 테스트 케이스)"""

    def test_scenario_1_semiconductor(self):
        """테스트 케이스 1: 반도체 장비 제어 소프트웨어"""
        input_text = """이번 프로젝트는 반도체 장비 제어 소프트웨어입니다.
팀은 3명 정도이고 기간은 about 6 months 정도 생각하고 있습니다.
Must have 기능은 Motion control, TCP/IP communication 이고
Nice to have 로는 logging, monitoring UI 가 있으면 좋겠습니다.
Platform은 Windows 기반이고 Python, C# 혼용을 고려 중입니다."""

        result = observe_v2(input_text)
        assert result.team_size == 3
        assert result.deadline_days == 180  # 6 months

    def test_scenario_2_automation_ambiguous(self):
        """테스트 케이스 2: Automation system (모호한 입력)"""
        input_text = """We are planning a small automation system.
인원은 2~3명 정도로 flexible 하고,
기간은 1년 이내면 좋겠습니다 (maybe shorter).
요구사항은 아직 evolving 중이고
추후 scope change 가능성이 큽니다.
Budget은 tight 합니다."""

        result = observe_v2(input_text)

        # 팀 인원이 범위로 처리되어야 함 (확정 금지)
        assert result.team_size is None
        assert result.team_size_min == 2
        assert result.team_size_max == 3

        # 모호성 점수가 높아야 함
        assert result.ambiguity_score >= 30

    def test_scenario_3_decision_agent(self):
        """테스트 케이스 3: Decision-support agent"""
        input_text = """This is a decision-support agent development project.
Team size will be 4 people.
The expected timeline is 1 year and 3 months.
Core requirement is rule-based analysis (LLM is forbidden).
Nice features include reporting dashboard and export 기능.
Target environment is Linux (WSL) and Python only."""

        result = observe_v2(input_text)
        assert result.team_size == 4
        assert result.deadline_days == 455  # 1*365 + 3*30


class TestRequirementsExtraction:
    """요구사항 항목 추출 테스트 (STEP 1)"""

    def test_must_have_items_korean_mixed(self):
        """test_1: Must have 항목이 리스트로 추출되어야 함"""
        input_text = """이번 프로젝트는 반도체 장비 제어 소프트웨어입니다.
팀은 3명 정도이고 기간은 about 6 months 정도 생각하고 있습니다.
Must have 기능은 Motion control, TCP/IP communication 이고
Nice to have 로는 logging, monitoring UI 가 있으면 좋겠습니다.
Platform은 Windows 기반이고 Python, C# 혼용을 고려 중입니다."""

        result = observe_v2(input_text)

        # Must have 항목이 개별 항목으로 추출
        assert "Motion control" in result.must_have
        assert "TCP/IP communication" in result.must_have
        # 전체 문장이 아닌 항목 리스트
        assert len(result.must_have) <= 5

    def test_nice_to_have_items_korean_mixed(self):
        """test_1: Nice to have 항목이 리스트로 추출되어야 함"""
        input_text = """Must have 기능은 Motion control, TCP/IP communication 이고
Nice to have 로는 logging, monitoring UI 가 있으면 좋겠습니다."""

        result = observe_v2(input_text)

        # Nice to have 항목이 개별 항목으로 추출
        assert "logging" in result.nice_to_have
        assert "monitoring UI" in result.nice_to_have
        assert len(result.nice_to_have) == 2

    def test_english_core_requirement(self):
        """test_3: Core requirement 형식 추출"""
        input_text = """Core requirement is rule-based analysis (LLM is forbidden).
Nice features include reporting dashboard and export 기능."""

        result = observe_v2(input_text)

        # Core requirement가 must_have로 추출
        assert "rule-based analysis" in result.must_have

    def test_english_nice_features(self):
        """test_3: Nice features 형식 추출"""
        input_text = """Core requirement is rule-based analysis.
Nice features include reporting dashboard and export 기능."""

        result = observe_v2(input_text)

        # Nice features가 nice_to_have로 추출
        assert "reporting dashboard" in result.nice_to_have
        assert "export 기능" in result.nice_to_have

    def test_korean_only_requirements(self):
        """한글 전용 요구사항 추출"""
        input_text = """필수 기능은 데이터 수집, 분석 리포트 이고
있으면 좋은 기능은 알림, 대시보드 입니다."""

        result = observe_v2(input_text)

        assert "데이터 수집" in result.must_have
        assert "분석 리포트" in result.must_have
        assert "알림" in result.nice_to_have or "대시보드" in result.nice_to_have

    def test_no_requirements_fallback_to_sentences(self):
        """요구사항 키워드 없으면 문장으로 fallback"""
        input_text = """인원은 5명이고 기간은 3개월입니다."""

        result = observe_v2(input_text)

        # must_have가 문장으로 채워짐
        assert len(result.must_have) > 0
        # nice_to_have는 비어 있음
        assert len(result.nice_to_have) == 0

    def test_items_split_by_and(self):
        """'and'로 분리된 항목 추출"""
        input_text = """Must have features are authentication and authorization and logging."""

        result = observe_v2(input_text)

        # and로 분리된 항목들
        assert len(result.must_have) >= 2

    def test_items_split_by_korean_connector(self):
        """'및'으로 분리된 항목 추출"""
        input_text = """필수 기능: API 연동 및 데이터 저장"""

        result = observe_v2(input_text)

        assert "API 연동" in result.must_have
        assert "데이터 저장" in result.must_have
