import json
from pathlib import Path

from ai.nudge.caption_slicer import build_caption_context


BACKEND_DIR = Path(__file__).resolve().parents[3]
MOCK_DATA_DIR = BACKEND_DIR / "mock_data"


def main() -> None:
    subtitle_files = sorted(MOCK_DATA_DIR.glob("subtitle_*.json"))

    if not subtitle_files:
        raise AssertionError("mock_data에 subtitle_*.json 파일이 없습니다.")

    for subtitle_file in subtitle_files:
        with subtitle_file.open(encoding="utf-8") as file:
            captions = json.load(file)

        assert isinstance(captions, list)
        assert captions, f"{subtitle_file.name}의 자막이 비어 있습니다."

        for caption in captions:
            assert "start" in caption
            assert "end" in caption
            assert "text" in caption

        first_caption = captions[0]
        current_time = (
            float(first_caption["start"]) + float(first_caption["end"])
        ) / 2

        context = build_caption_context(
            captions=captions,
            current_time=current_time,
        )

        assert context["selected_context_text"]

        print(f"PASS: {subtitle_file.name}")
        print(f"  captions: {len(captions)}개")
        print(f"  current_time: {current_time}초")
        print(f"  context_source: {context['suggested_context_source']}")
        print(f"  selected_context: {context['selected_context_text']}")
        print()


if __name__ == "__main__":
    main()