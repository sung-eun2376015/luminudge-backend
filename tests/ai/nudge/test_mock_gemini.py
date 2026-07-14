import json
from pathlib import Path

from ai.nudge.caption_slicer import build_caption_context
from ai.nudge.mission_generator import generate_mission


BACKEND_DIR = Path(__file__).resolve().parents[3]
SUBTITLE_PATH = BACKEND_DIR / "mock_data" / "subtitle_pinkfong.json"


def main() -> None:
    with SUBTITLE_PATH.open(encoding="utf-8") as file:
        captions = json.load(file)

    current_time = 60

    context = build_caption_context(
        captions=captions,
        current_time=current_time,
    )

    print("[선택된 자막 맥락]")
    print(context["selected_context_text"])
    print()

    mission = generate_mission(
        current_captions=context["current_captions"],
        previous_captions=context["previous_captions"],
        current_text=context["current_text"],
        previous_text=context["previous_text"],
        selected_context_text=context["selected_context_text"],
        suggested_context_source=context["suggested_context_source"],
        child_tier="all",
    )

    print("[Gemini 미션 결과]")
    print(json.dumps(mission, ensure_ascii=False, indent=2))

    assert isinstance(mission, dict)
    assert "missions" in mission

    print()
    print("PASS: 실제 mock_data로 Gemini 미션을 생성했습니다.")


if __name__ == "__main__":
    main()