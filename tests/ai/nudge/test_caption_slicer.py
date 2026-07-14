import json
from pathlib import Path

from ai.nudge.caption_slicer import build_caption_context


def load_timeline():
    timeline_path = Path("tests/fixtures/nudge/timeline.json")

    with timeline_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def print_context_result(context):
    print("=" * 60)
    print(f"current_time: {context['current_time']}초")
    print(f"suggested_context_source: {context['suggested_context_source']}")
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

    test_times = [
        18,  # 마지막 자막이 "우와!"라 애매함 → previous
        22,  # 마지막 자막이 "다음에는 무엇이 나올까요?"라 애매함 → previous
        26,  # 마지막 자막이 "파란 새"라 명확함 → current
        38,  # 마지막 자막이 "멋지다!"라 애매함 → previous
        50,  # 마지막 자막이 숫자/사과라 명확함 → current
    ]

    for current_time in test_times:
        context = build_caption_context(
            captions=captions,
            current_time=current_time,
            current_window_sec=6,
            previous_window_sec=24,
        )

        print_context_result(context)


if __name__ == "__main__":
    main()
