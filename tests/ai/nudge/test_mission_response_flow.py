import os
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ["SESSION_STORAGE"] = "memory"

from ai.nudge.semantic_csr import SemanticCSRResult
from main import app
from storage.memory import sessions


client = TestClient(app)


def fake_mission(context: dict, child_tier: str) -> dict:
    return {
        "context_source": context["suggested_context_source"],
        "scene_summary": context["selected_context_text"],
        "missions": {
            child_tier: {
                "type": "choice",
                "prompt": "방이 무슨 색으로 변했을까요?",
                "choices": ["파란색", "노란색"],
                "answer": "파란색",
                "expected_keywords": ["파란색"],
            }
        },
    }


def test_onboarding_returns_id_and_computed_tier() -> None:
    with patch(
        "main.save_onboarding_record",
        return_value=SimpleNamespace(id=17),
    ):
        response = client.post(
            "/onboarding",
            json={
                "ageYears": 4,
                "gender": "female",
                "canFollowSimpleInstruction": True,
                "canSpeak": True,
                "baselineGV": 0.25,
                "baselineFD": 1.2,
                "baselineBR": 15,
                "plr": 2.8,
                "completedAt": "2026-08-01T12:00:00+09:00",
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "onboarding_id": 17,
        "child_tier": "tier2",
    }


def test_session_rejects_unknown_onboarding_id() -> None:
    with patch("ai.nudge.router.get_onboarding_record", return_value=None):
        response = client.post(
            "/sessions",
            json={
                "youtube_url": "https://www.youtube.com/watch?v=example",
                "subtitle_name": "pinkfong",
                "onboarding_id": 999,
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "온보딩 정보를 찾을 수 없습니다"


def create_session() -> str:
    onboarding = SimpleNamespace(
        childTier="tier2",
        baselineGV=0.25,
        baselineFD=1.2,
        baselineBR=15.0,
        plr=2.8,
    )
    with patch(
        "ai.nudge.router.get_onboarding_record",
        return_value=onboarding,
    ):
        response = client.post(
            "/sessions",
            json={
                "youtube_url": "https://www.youtube.com/watch?v=example",
                "subtitle_name": "pinkfong",
                "onboarding_id": 17,
            },
        )
    assert response.status_code == 201
    assert response.json()["onboarding_id"] == 17
    assert response.json()["child_tier"] == "tier2"
    session_id = response.json()["session_id"]
    assert sessions[session_id]["baseline"] == {
        "gv": 0.25,
        "fd": 1.2,
        "br": 15.0,
        "plr_seconds": 2.8,
    }
    return session_id


def test_session_accepts_provided_captions() -> None:
    sessions.clear()
    onboarding = SimpleNamespace(
        childTier="tier2",
        baselineGV=0.25,
        baselineFD=1.2,
        baselineBR=15.0,
        plr=2.8,
    )
    with patch("ai.nudge.router.get_onboarding_record", return_value=onboarding):
        response = client.post(
            "/sessions",
            json={
                "youtube_url": "https://www.youtube.com/watch?v=example",
                "onboarding_id": 17,
                "captions": [
                    {"start": 28, "end": 43, "text": "방의 온도가 바뀌어요."}
                ],
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["subtitle_name"] is None
    assert body["subtitle_source"] == "provided_captions"
    assert body["caption_count"] == 1
    assert sessions[body["session_id"]]["captions"][0]["start"] == 28


def test_session_requires_a_subtitle_source() -> None:
    response = client.post(
        "/sessions",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=example",
            "onboarding_id": 17,
        },
    )
    assert response.status_code == 422


def create_strong_mission(session_id: str) -> str:
    with patch(
        "ai.nudge.nudge_service.NudgeService._generate_mission",
        side_effect=fake_mission,
    ):
        response = client.post(
            f"/sessions/{session_id}/nudge",
            json={
                "cls_score": 0.8,
                "intensity": "strong",
                "gv": 0.1,
                "fd": 5.0,
                "br": 2,
                "timestamp": 35,
                "video_duration_sec": 300,
                "cooldown_ms": 10000,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["question"]["mission_id"]
    assert "answer" not in body["question"]
    assert "expected_keywords" not in body["question"]
    attention_event = sessions[session_id]["attention_events"][0]
    assert attention_event["intensity"] == "strong"
    assert attention_event["cooldown_ms"] == 10000
    assert attention_event["processing_status"] == "completed"
    assert attention_event["mission_id"] == body["question"]["mission_id"]
    return body["question"]["mission_id"]


def test_choice_response_returns_praise_and_is_stored() -> None:
    sessions.clear()
    session_id = create_session()
    mission_id = create_strong_mission(session_id)

    response = client.post(
        f"/sessions/{session_id}/missions/{mission_id}/responses",
        json={
            "response_type": "choice",
            "answer": "파란색",
            "response_time_ms": 2800,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_correct"] is True
    assert body["reaction"] == "praise"
    assert body["plr_seconds"] == 2.8
    assert body["resume_video"] is True
    assert sessions[session_id]["missions"][mission_id]["answered"] is True

    duplicate = client.post(
        f"/sessions/{session_id}/missions/{mission_id}/responses",
        json={
            "response_type": "choice",
            "answer": "파란색",
            "response_time_ms": 3000,
        },
    )
    assert duplicate.status_code == 409


def test_voice_response_uses_csr_and_requests_stt_fallback() -> None:
    sessions.clear()
    session_id = create_session()
    mission_id = create_strong_mission(session_id)

    response = client.post(
        f"/sessions/{session_id}/missions/{mission_id}/responses",
        json={
            "response_type": "voice",
            "transcript": "",
            "stt_source": "web_speech",
            "confidence": 0.2,
            "response_time_ms": 1500,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reaction"] == "retry"
    assert body["needs_stt_fallback"] is True
    assert body["csr_score"] == 0.0
    assert body["resume_video"] is False
    assert sessions[session_id]["missions"][mission_id]["answered"] is False

    semantic_result = SemanticCSRResult(
        csr_score=0.88,
        method="semantic_embedding",
        expected_text="파란색",
    )
    with (
        patch(
            "ai.nudge.router.transcribe_audio",
            return_value="방이 파랗게 변했어요",
        ),
        patch(
            "ai.nudge.response_service.calculate_semantic_csr",
            return_value=semantic_result,
        ),
    ):
        audio_response = client.post(
            f"/sessions/{session_id}/missions/{mission_id}/responses/audio",
            files={"audio": ("answer.webm", b"fake audio", "audio/webm")},
            data={"response_time_ms": "2300", "language": "ko"},
        )

    assert audio_response.status_code == 200
    audio_body = audio_response.json()
    assert audio_body["transcript"] == "방이 파랗게 변했어요"
    assert audio_body["stt_source"] == "gemini_audio"
    assert audio_body["csr_score"] == 0.88
    assert audio_body["reaction"] == "praise"
    assert sessions[session_id]["missions"][mission_id]["answered"] is True
    assert len(sessions[session_id]["missions"][mission_id]["responses"]) == 2


def test_wrong_choice_returns_hint() -> None:
    sessions.clear()
    session_id = create_session()
    mission_id = create_strong_mission(session_id)

    response = client.post(
        f"/sessions/{session_id}/missions/{mission_id}/responses",
        json={
            "response_type": "choice",
            "answer": "노란색",
            "response_time_ms": 2100,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_correct"] is False
    assert body["reaction"] == "hint"
    assert body["needs_retry"] is True
    assert body["resume_video"] is False
    assert sessions[session_id]["missions"][mission_id]["answered"] is False


def test_voice_response_uses_semantic_csr() -> None:
    sessions.clear()
    session_id = create_session()
    mission_id = create_strong_mission(session_id)

    semantic_result = SemanticCSRResult(
        csr_score=0.82,
        method="semantic_embedding",
        expected_text="파란색",
    )
    with patch(
        "ai.nudge.response_service.calculate_semantic_csr",
        return_value=semantic_result,
    ):
        response = client.post(
            f"/sessions/{session_id}/missions/{mission_id}/responses",
            json={
                "response_type": "voice",
                "transcript": "방이 파랗게 변했어요",
                "stt_source": "web_speech",
                "confidence": 0.9,
                "response_time_ms": 3200,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["csr_score"] == 0.82
    assert body["csr_method"] == "semantic_embedding"
    assert body["reaction"] == "praise"
    assert body["resume_video"] is True


if __name__ == "__main__":
    test_onboarding_returns_id_and_computed_tier()
    test_session_rejects_unknown_onboarding_id()
    test_session_accepts_provided_captions()
    test_session_requires_a_subtitle_source()
    test_choice_response_returns_praise_and_is_stored()
    test_voice_response_uses_csr_and_requests_stt_fallback()
    test_wrong_choice_returns_hint()
    test_voice_response_uses_semantic_csr()
    print("PASS: mission storage + choice/voice evaluation + reactions")
