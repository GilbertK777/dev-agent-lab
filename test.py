"""
Observer v2 테스트 러너

JSON 파일에서 테스트 케이스를 로드하고 결과를 JSON으로 저장합니다.

사용법:
    python test.py                          # 기본 실행
    python test.py --input custom.json      # 커스텀 입력 파일
    python test.py --output results.json    # 커스텀 출력 파일
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
from dataclasses import asdict

from src.observation.observer import observe_v2


# 기본 경로
DEFAULT_INPUT = Path(__file__).parent / "tests" / "fixtures" / "test_inputs.json"
DEFAULT_OUTPUT = Path(__file__).parent / "tests" / "fixtures" / "test_results.json"


def load_test_cases(input_path: Path) -> list[dict]:
    """JSON 파일에서 테스트 케이스 로드"""
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("test_cases", [])


def _serialize_extraction_value(value):
    """추출 값을 JSON 직렬화 가능한 형태로 변환"""
    if hasattr(value, '__dataclass_fields__'):
        # dataclass인 경우 (RequirementsResult 등)
        return asdict(value)
    elif isinstance(value, dict):
        return value
    else:
        return value


def run_single_test(test_case: dict) -> dict:
    """단일 테스트 케이스 실행"""
    result = observe_v2(test_case["input"])

    # ObservationResult를 dict로 변환
    return {
        "id": test_case["id"],
        "name": test_case["name"],
        "input": test_case["input"],
        "expected": test_case.get("expected", {}),
        "actual": {
            "team_size": result.team_size,
            "team_size_min": result.team_size_min,
            "team_size_max": result.team_size_max,
            "deadline_days": result.deadline_days,
            "ambiguity_score": result.ambiguity_score,
            "lang_mix_ratio": result.lang_mix_ratio,
            "tokens_estimate": result.tokens_estimate,
            "must_have": result.must_have,
            "nice_to_have": result.nice_to_have,
            "unknowns": [
                {
                    "question": u.question,
                    "reason": u.reason,
                    "evidence": u.evidence
                }
                for u in result.unknowns
            ],
            "extractions": [
                {
                    "extractor": e.extractor,
                    "value": _serialize_extraction_value(e.value),
                    "confidence": e.confidence,
                    "evidence": e.evidence
                }
                for e in result.extractions
            ],
        },
    }


def save_results(results: dict, output_path: Path) -> None:
    """테스트 결과를 JSON 파일로 저장"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def run_tests(input_path: Path, output_path: Path) -> dict:
    """모든 테스트 실행 및 결과 저장"""
    test_cases = load_test_cases(input_path)

    results = {
        "metadata": {
            "input_file": str(input_path),
            "output_file": str(output_path),
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(test_cases),
        },
        "results": [],
    }

    print(f"테스트 입력: {input_path}")
    print(f"테스트 개수: {len(test_cases)}개")
    print("=" * 60)

    for test_case in test_cases:
        print(f"\n[{test_case['id']}] {test_case['name']}")
        print("-" * 40)

        result = run_single_test(test_case)
        results["results"].append(result)

        # 콘솔 출력
        actual = result["actual"]
        expected = result["expected"]

        # 팀 인원 출력 (단일값 또는 범위)
        if actual['team_size'] is not None:
            print(f"  team_size: {actual['team_size']} (expected: {expected.get('team_size', 'N/A')})")
        elif actual['team_size_min'] is not None:
            print(f"  team_size: {actual['team_size_min']}~{actual['team_size_max']}명 (범위)")
        else:
            print(f"  team_size: None")

        print(f"  deadline_days: {actual['deadline_days']} (expected: {expected.get('deadline_days', 'N/A')})")
        print(f"  ambiguity_score: {actual['ambiguity_score']}")
        print(f"  unknowns: {len(actual['unknowns'])}개")

        if actual["extractions"]:
            print(f"  extractions:")
            for e in actual["extractions"]:
                print(f"    - {e['extractor']}: {e['value']} (conf: {e['confidence']:.2f})")

    # 결과 저장
    save_results(results, output_path)
    print("\n" + "=" * 60)
    print(f"결과 저장: {output_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Observer v2 테스트 러너")
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help="테스트 입력 JSON 파일 경로"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="테스트 결과 JSON 파일 경로"
    )
    args = parser.parse_args()

    run_tests(args.input, args.output)


if __name__ == "__main__":
    main()
