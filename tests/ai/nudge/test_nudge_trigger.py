import json

from ai.nudge.nudge_trigger import (
    build_nudge_event,
    classify_child_tier,
    get_trigger_strength,
)
from ai.nudge.prefetch_queue import MissionQueue, QueuedMission


def make_mock_gemini_mission():
    return {
        "should_generate": True,
        "context_source": "previous",
        "scene_summary": "숲에서 토끼를 만나는 장면",
        "keywords": ["숲", "토끼"],
        "missions": {
            "tier1": {
                "type": "gesture",
                "prompt": "루미랑 토끼처럼 귀를 쫑긋 세워볼까요?",
            },
            "tier2": {
                "type": "choice",
                "prompt": "방금 나온 동물은 누구일까요?",
                "choices": ["토끼", "새"],
                "answer": "토끼",
            },
            "tier3": {
                "type": "open_question",
                "prompt": "토끼는 어떻게 움직였을까?",
                "expected_keywords": ["깡충", "뛰어"],
            },
        },
    }


def make_queue_with_ready_mission(trigger_time=22):
    mission_queue = MissionQueue()
    mission_queue.add(
        QueuedMission(
            trigger_time=trigger_time,
            prefetch_time=trigger_time,
            mission=make_mock_gemini_mission(),
            context={"selected_context_text": "토끼가 나왔어요."},
        )
    )
    return mission_queue


def test_trigger_strength():
    assert get_trigger_strength(0.3) == "none"
    assert get_trigger_strength(0.6) == "soft"
    assert get_trigger_strength(0.8) == "strong"


def test_child_tier():
    assert classify_child_tier(child_age=2) == "tier1"
    assert classify_child_tier(child_age=4) == "tier2"
    assert classify_child_tier(child_age=5, can_speak=True) == "tier3"
    assert classify_child_tier(child_age=5, can_speak=False) == "tier2"


def test_no_nudge_when_cls_low():
    mission_queue = make_queue_with_ready_mission()

    event = build_nudge_event(
        cls_score=0.3,
        current_time=22,
        mission_queue=mission_queue,
        child_tier="tier2",
    )

    assert event["should_nudge"] is False
    assert event["trigger_strength"] == "none"
    assert event["source"] == "no_trigger"


def test_soft_nudge_from_queue():
    mission_queue = make_queue_with_ready_mission()

    event = build_nudge_event(
        cls_score=0.6,
        current_time=22,
        mission_queue=mission_queue,
        child_tier="tier2",
    )

    assert event["should_nudge"] is True
    assert event["trigger_strength"] == "soft"
    assert event["pause_video"] is False
    assert event["source"] == "mission_queue"
    assert event["mission_type"] == "choice"
    assert event["nudge_text"] == "방금 나온 동물은 누구일까요?"


def test_strong_nudge_from_queue():
    mission_queue = make_queue_with_ready_mission()

    event = build_nudge_event(
        cls_score=0.8,
        current_time=22,
        mission_queue=mission_queue,
        child_tier="tier1",
    )

    assert event["should_nudge"] is True
    assert event["trigger_strength"] == "strong"
    assert event["pause_video"] is True
    assert event["source"] == "mission_queue"
    assert event["mission_type"] == "gesture"


def test_fallback_when_queue_empty():
    mission_queue = MissionQueue()

    event = build_nudge_event(
        cls_score=0.8,
        current_time=22,
        mission_queue=mission_queue,
        child_tier="tier2",
    )

    assert event["should_nudge"] is True
    assert event["trigger_strength"] == "strong"
    assert event["pause_video"] is True
    assert event["source"] == "fallback"
    assert event["mission_type"] == "fallback"


def main():
    test_trigger_strength()
    test_child_tier()
    test_no_nudge_when_cls_low()
    test_soft_nudge_from_queue()
    test_strong_nudge_from_queue()
    test_fallback_when_queue_empty()

    demo_queue = make_queue_with_ready_mission()
    demo_event = build_nudge_event(
        cls_score=0.6,
        current_time=22,
        mission_queue=demo_queue,
        child_tier="tier2",
    )

    print("=== DEMO NUDGE EVENT ===")
    print(json.dumps(demo_event, ensure_ascii=False, indent=2))
    print("\nPASS: nudge trigger logic works with mock CLS and mission_queue.")


if __name__ == "__main__":
    main()
