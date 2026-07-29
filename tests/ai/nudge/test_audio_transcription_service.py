import os
from unittest.mock import patch

from ai.nudge.audio_transcription_service import (
    AudioTranscriptionError,
    transcribe_audio,
    validate_audio,
)


def test_transcribe_audio_uses_injected_gemini_generator() -> None:
    def fake_generator(audio: bytes, content_type: str, language: str) -> str:
        assert audio == b"fake audio bytes"
        assert content_type == "audio/webm"
        assert language == "ko"
        return "파란색이에요"

    transcript = transcribe_audio(
        filename="answer.webm",
        content_type="audio/webm",
        audio_bytes=b"fake audio bytes",
        language="ko",
        generator=fake_generator,
    )
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


def test_empty_gemini_transcript_is_rejected() -> None:
    try:
        transcribe_audio(
            filename="answer.webm",
            content_type="audio/webm",
            audio_bytes=b"fake audio",
            generator=lambda *_: "",
        )
    except AudioTranscriptionError as error:
        assert str(error) == "Gemini가 빈 transcript를 반환했습니다"
    else:
        raise AssertionError("empty transcript must fail")


if __name__ == "__main__":
    test_transcribe_audio_uses_injected_gemini_generator()
    test_audio_validation_rejects_invalid_input()
    test_empty_gemini_transcript_is_rejected()
    print("PASS: Gemini audio transcription service")
