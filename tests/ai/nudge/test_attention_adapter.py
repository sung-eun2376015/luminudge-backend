from ai.attention.schemas import ClsPayload
from ai.nudge.attention_adapter import build_nudge_from_attention
from ai.nudge.prefetch_queue import MissionQueue


def test_strong_attention_to_nudge():
    payload = ClsPayload(
        cls_score=0.8,
        intensity="strong",
        gv=0.1,
        fd=4.5,
        br=3,
        timestamp=22,
    )

    event = build_nudge_from_attention(
        payload=payload,
        mission_queue=MissionQueue(),
        child_tier="tier2",
    )

    assert event["should_nudge"] is True
    assert event["trigger_strength"] == "strong"
    assert event["pause_video"] is True
    assert event["current_time"] == 22

    assert event["attention_metrics"] == {
        "gv": 0.1,
        "fd": 4.5,
        "br": 3,
    }

    print(event)


if __name__ == "__main__":
    test_strong_attention_to_nudge()
    print("PASS: attention connected to nudge")