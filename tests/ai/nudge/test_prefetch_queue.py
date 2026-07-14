import argparse
import json
from pathlib import Path

from ai.nudge.prefetch_queue import MissionQueue, prefetch_mission


def load_timeline(path: str = "tests/fixtures/nudge/timeline.json"):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--time", type=float, default=17)
    parser.add_argument("--child-tier", type=str, default="all")
    parser.add_argument("--real", action="store_true")
    parser.add_argument("--multi", action="store_true")
    args = parser.parse_args()

    timeline_path = Path("tests/fixtures/nudge/timeline.json")

    if not timeline_path.exists():
        raise FileNotFoundError("sample_data/timeline.json 파일이 없습니다.")

    timeline = load_timeline(str(timeline_path))
    mission_queue = MissionQueue()

    if args.multi:
        for time_point in [5, 17, 20, 65]:
            queued = prefetch_mission(
                timeline=timeline,
                current_time=time_point,
                mission_queue=mission_queue,
                child_tier=args.child_tier,
                dry_run=not args.real,
            )

            print(f"\n[PREFETCH] current_time={time_point}, prefetch_time={queued.prefetch_time}")
            print(f"context_source={queued.context.get('suggested_context_source')}")
            print(f"selected_context_text={queued.context.get('selected_context_text')}")
            print(f"mission_text={queued.mission.get('mission_text')}")

        print("\n=== FINAL QUEUE ===")
        print(json.dumps(mission_queue.peek_all(), ensure_ascii=False, indent=2))
        return

    queued = prefetch_mission(
        timeline=timeline,
        current_time=args.time,
        mission_queue=mission_queue,
        child_tier=args.child_tier,
        dry_run=not args.real,
    )

    print("=== PREFETCH RESULT ===")
    print(f"current_time: {args.time}")
    print(f"prefetch_time: {queued.prefetch_time}")
    print(f"trigger_time: {queued.trigger_time}")

    print("\n=== CONTEXT ===")
    print(f"suggested_context_source: {queued.context.get('suggested_context_source')}")
    print(f"selected_context_text: {queued.context.get('selected_context_text')}")

    print("\n=== MISSION ===")
    print(json.dumps(queued.mission, ensure_ascii=False, indent=2))

    print("\n=== QUEUE BEFORE TRIGGER ===")
    print(json.dumps(mission_queue.peek_all(), ensure_ascii=False, indent=2))

    ready_before = mission_queue.get_ready(args.time)
    print("\n=== GET READY AT CURRENT TIME ===")
    print(ready_before)

    ready_after = mission_queue.get_ready(queued.trigger_time)
    print("\n=== GET READY AT TRIGGER TIME ===")
    if ready_after is None:
        print("No mission ready")
    else:
        print(json.dumps(ready_after.mission, ensure_ascii=False, indent=2))

    print("\n=== QUEUE AFTER TRIGGER ===")
    print(json.dumps(mission_queue.peek_all(), ensure_ascii=False, indent=2))

    assert queued.prefetch_time == args.time + 5
    assert queued.trigger_time == queued.prefetch_time
    assert queued.context.get("suggested_context_source") in ["current", "previous", "generic", "skip"]
    assert ready_before is None
    assert ready_after is not None
    assert mission_queue.peek_all() == []

    print("\nPASS: prefetch mission was queued, held until trigger time, and popped successfully.")
    
if __name__ == "__main__":
    main()
