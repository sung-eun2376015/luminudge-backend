import json
from pathlib import Path

from ai.nudge.prefetch_queue import MissionQueue, prefetch_mission


BACKEND_DIR = Path(__file__).resolve().parents[3]
SUBTITLE_PATH = BACKEND_DIR / "mock_data" / "subtitle_pinkfong.json"


def main() -> None:
    with SUBTITLE_PATH.open(encoding="utf-8") as file:
        captions = json.load(file)

    queue = MissionQueue()
    current_time = 55

    queued = prefetch_mission(
        timeline=captions,
        current_time=current_time,
        mission_queue=queue,
        child_tier="all",
        dry_run=False,
    )

    print("[사용한 자막 파일]")
    print(SUBTITLE_PATH.name)

    print("\n[선택된 맥락]")
    print(queued.context["selected_context_text"])

    print("\n[Gemini 미션]")
    print(json.dumps(queued.mission, ensure_ascii=False, indent=2))

    print("\n[Queue]")
    print(json.dumps(queue.peek_all(), ensure_ascii=False, indent=2))

    assert queued.mission.get("missions")
    assert queue.peek_all()

    print("\nPASS: mock_data → Gemini → MissionQueue 연결 성공")


if __name__ == "__main__":
    main()