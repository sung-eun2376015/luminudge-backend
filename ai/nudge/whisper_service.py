import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


TRANSCRIPTION_URL = "https://api.openai.com/v1/audio/transcriptions"
TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
MAX_AUDIO_BYTES = 10 * 1024 * 1024
SUPPORTED_AUDIO_EXTENSIONS = {
    ".flac", ".m4a", ".mp3", ".mp4", ".mpeg",
    ".mpga", ".ogg", ".wav", ".webm",
}


class WhisperServiceError(RuntimeError):
    pass


def validate_audio(filename: str, audio_bytes: bytes) -> None:
    if Path(filename).suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        raise ValueError("지원하지 않는 오디오 파일 형식입니다")
    if not audio_bytes:
        raise ValueError("오디오 파일이 비어 있습니다")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ValueError("오디오 파일은 10MB 이하여야 합니다")


def transcribe_audio(
    *,
    filename: str,
    content_type: str,
    audio_bytes: bytes,
    language: str = "ko",
    client: httpx.Client | None = None,
    api_key: str | None = None,
) -> str:
    """Transcribe one uploaded audio file with OpenAI's transcription API."""
    validate_audio(filename, audio_bytes)
    load_dotenv()
    resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not resolved_api_key:
        raise WhisperServiceError(".env 파일에 OPENAI_API_KEY가 없습니다")

    owns_client = client is None
    http_client = client or httpx.Client(timeout=60.0)
    try:
        response = http_client.post(
            TRANSCRIPTION_URL,
            headers={"Authorization": f"Bearer {resolved_api_key}"},
            files={
                "file": (
                    filename,
                    audio_bytes,
                    content_type or "application/octet-stream",
                )
            },
            data={
                "model": TRANSCRIPTION_MODEL,
                "language": language.split("-")[0].lower(),
                "response_format": "json",
            },
        )
        response.raise_for_status()
        transcript = str(response.json().get("text", "")).strip()
        if not transcript:
            raise WhisperServiceError("Whisper가 빈 transcript를 반환했습니다")
        return transcript
    except httpx.HTTPStatusError as error:
        raise WhisperServiceError(
            f"Whisper API 요청에 실패했습니다 (HTTP {error.response.status_code})"
        ) from error
    except httpx.HTTPError as error:
        raise WhisperServiceError("Whisper API에 연결할 수 없습니다") from error
    finally:
        if owns_client:
            http_client.close()
