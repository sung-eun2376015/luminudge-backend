import json
from pathlib import Path

from ai.attention.schemas import ClsPayload
from ai.nudge.nudge_service import NudgeService
from ai.nudge.schemas import NudgeResponse


BASE_DIR = Path(__file__).resolve().parents[3]
SUBTITLE_PATH = BASE_DIR / "mock_data" / "subtitle_pinkfong.json"


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def load_subtitles() -> list[dict]:
    with SUBTITLE_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def fake_gemini(context: dict, child_tier: str) -> dict:
    assert context["selected_context_text"]
    assert child_tier == "tier2"
    return {
        "context_source": context["suggested_context_source"],
        "scene_summary": context["selected_context_text"],
        "missions": {
            "tier2": {
                "type": "choice",
                "prompt": "방금 방의 온도를 바꾼 것은 무엇일까요?",
                "choices": ["노란색 버튼", "파란색 공"],
                "answer": "노란색 버튼",
            }
        },
    }


def make_payload(timestamp: int, cls_score: float, intensity: str) -> ClsPayload:
    return ClsPayload(
        cls_score=cls_score,
        intensity=intensity,
        gv=0.1,
        fd=4.5,
        br=3,
        timestamp=timestamp,
    )


def test_pinkfong_attention_flow() -> None:
    captions = load_subtitles()
    clock = FakeClock()
    service = NudgeService(cooldown_seconds=10, clock=clock)

    none_event = service.process(
        make_payload(5, 0.3, "none"), captions, child_tier="tier2"
    )
    assert none_event["should_nudge"] is False
    assert none_event["source"] == "no_trigger"

    clock.advance(1)
    soft_event = service.process(
        make_payload(22, 0.6, "soft"), captions, child_tier="tier2"
    )
    assert soft_event["should_nudge"] is True
    assert soft_event["pause_video"] is False
    assert "question" not in soft_event

    clock.advance(5)
    cooldown_event = service.process(
        make_payload(35, 0.8, "strong"),
        captions,
        child_tier="tier2",
        generator=fake_gemini,
    )
    assert cooldown_event["should_nudge"] is False
    assert cooldown_event["source"] == "cooldown"
    assert cooldown_event["cooldown_remaining"] == 5

    clock.advance(5)
    strong_event = service.process(
        make_payload(35, 0.8, "strong"),
        captions,
        child_tier="tier2",
        generator=fake_gemini,
    )
    response = NudgeResponse.model_validate(strong_event)
    assert response.should_nudge is True
    assert response.pause_video is True
    assert response.timestamp == 35
    assert response.question is not None
    assert response.question.type == "choice"
    assert response.question.choices == ["노란색 버튼", "파란색 공"]

    print("=== FRONTEND NUDGE RESPONSE ===")
    print(json.dumps(strong_event, ensure_ascii=False, indent=2))
    print("PASS: pinkfong subtitles + continuous CLS + cooldown + question output")


if __name__ == "__main__":
    test_pinkfong_attention_flow()
