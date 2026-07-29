import os
from unittest.mock import patch

import httpx

from ai.nudge.whisper_service import transcribe_audio, validate_audio


def test_transcribe_audio_sends_multipart_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/audio/transcriptions"
        assert request.headers["authorization"] == "Bearer test-key"
        assert "multipart/form-data" in request.headers["content-type"]
        return httpx.Response(200, json={"text": "파란색이에요"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        transcript = transcribe_audio(
            filename="answer.webm",
            content_type="audio/webm",
            audio_bytes=b"fake audio bytes",
            language="ko-KR",
            client=client,
            api_key="test-key",
        )
    finally:
        client.close()

    assert transcript == "파란색이에요"


def test_audio_validation_rejects_invalid_input() -> None:
    for filename, content, expected_message in (
        ("answer.txt", b"not audio", "지원하지 않는 오디오 파일 형식입니다"),
        ("answer.webm", b"", "오디오 파일이 비어 있습니다"),
    ):
        try:
            validate_audio(filename, content)
        except ValueError as error:
            assert str(error) == expected_message
        else:
            raise AssertionError("invalid audio must be rejected")


def test_missing_api_key_is_reported_without_exposing_a_key() -> None:
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        try:
            transcribe_audio(
                filename="answer.webm",
                content_type="audio/webm",
                audio_bytes=b"fake audio",
            )
        except RuntimeError as error:
            assert "OPENAI_API_KEY" in str(error)
        else:
            raise AssertionError("missing key must fail")


if __name__ == "__main__":
    test_transcribe_audio_sends_multipart_request()
    test_audio_validation_rejects_invalid_input()
    test_missing_api_key_is_reported_without_exposing_a_key()
    print("PASS: Whisper multipart transcription service")
