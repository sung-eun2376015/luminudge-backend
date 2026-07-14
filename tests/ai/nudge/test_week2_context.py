import json
from pathlib import Path

from ai.nudge.caption_slicer import build_caption_context


def load_timeline():
    timeline_path = Path("tests/fixtures/nudge/timeline.json")

    with timeline_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def print_context_test_result(context, expected):
    actual = context["suggested_context_source"]
    is_passed = actual == expected

    print("=" * 60)
    print(f"current_time: {context['current_time']}초")
    print(f"expected: {expected}")
    print(f"actual: {actual}")
    print(f"result: {'PASS' if is_passed else 'FAIL'}")
    print()
    print("[current_text]")
    print(context["current_text"])
    print()
    print("[previous_text]")
    print(context["previous_text"])
    print()
    print("[selected_context_text]")
    print(context["selected_context_text"])
    print("=" * 60)
    print()


def main():
    captions = load_timeline()

    test_cases = [
        {
            "current_time": 22,
            "previous_window_sec": 24,
            "expected": "previous",
        },
        {
            "current_time": 25,
            "previous_window_sec": 24,
            "expected": "current",
        },
        {
            "current_time": 70,
            "previous_window_sec": 10,
            "expected": "generic",
        },
    ]

    passed_count = 0

    for test_case in test_cases:
        context = build_caption_context(
            captions=captions,
            current_time=test_case["current_time"],
            current_window_sec=6,
            previous_window_sec=test_case["previous_window_sec"],
        )

        print_context_test_result(
            context=context,
            expected=test_case["expected"],
        )

        if context["suggested_context_source"] == test_case["expected"]:
            passed_count += 1

    print(f"총 {len(test_cases)}개 중 {passed_count}개 통과")


if __name__ == "__main__":
    main()
