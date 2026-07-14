import argparse
import json
from pathlib import Path

from ai.nudge.caption_slicer import build_caption_context
from ai.nudge.mission_generator import generate_mission


def load_timeline():
    timeline_path = Path("tests/fixtures/nudge/timeline.json")

    with timeline_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_result(result, current_time):
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / f"week2_time_{current_time}_result.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print(f"저장 완료: {output_path.resolve()}")


def get_previous_window_sec(current_time):
    """
    테스트 편의를 위한 window 설정.
    70초 generic 테스트에서는 이전 명확한 장면이 잡히지 않도록 짧게 둔다.
    """

    if current_time >= 60:
        return 10

    return 24


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--time",
        type=float,
        default=22,
        help="미션을 생성할 현재 영상 시간(초)",
    )
    args = parser.parse_args()

    captions = load_timeline()
    current_time = args.time
    previous_window_sec = get_previous_window_sec(current_time)

    caption_context = build_caption_context(
        captions=captions,
        current_time=current_time,
        current_window_sec=6,
        previous_window_sec=previous_window_sec,
    )

    print("[caption_context]")
    print(f"current_time: {caption_context['current_time']}")
    print(f"suggested_context_source: {caption_context['suggested_context_source']}")
    print(f"current_text: {caption_context['current_text']}")
    print(f"previous_text: {caption_context['previous_text']}")
    print(f"selected_context_text: {caption_context['selected_context_text']}")
    print()

    result = generate_mission(
        child_tier="all",
        current_captions=caption_context["current_captions"],
        previous_captions=caption_context["previous_captions"],
        current_text=caption_context["current_text"],
        previous_text=caption_context["previous_text"],
        selected_context_text=caption_context["selected_context_text"],
        suggested_context_source=caption_context["suggested_context_source"],
    )

    print("[mission_result]")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    save_result(result, current_time)


if __name__ == "__main__":
    main()
