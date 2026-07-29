from unittest.mock import patch

from fastapi.testclient import TestClient

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


def create_session() -> str:
    response = client.post(
        "/sessions",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=example",
            "subtitle_name": "pinkfong",
            "child_tier": "tier2",
        },
    )
    assert response.status_code == 201
    return response.json()["session_id"]


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
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["question"]["mission_id"]
    assert "answer" not in body["question"]
    assert "expected_keywords" not in body["question"]
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


def test_voice_response_uses_csr_and_requests_whisper_fallback() -> None:
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
    assert body["needs_whisper_fallback"] is True
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
    assert audio_body["stt_source"] == "whisper"
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
    test_choice_response_returns_praise_and_is_stored()
    test_voice_response_uses_csr_and_requests_whisper_fallback()
    test_wrong_choice_returns_hint()
    test_voice_response_uses_semantic_csr()
    print("PASS: mission storage + choice/voice evaluation + reactions")
