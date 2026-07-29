# stt_adapter.py

from __future__ import annotations

from typing import Any

from ai.nudge.stt_csr import STTResult


SUPPORTED_STT_SOURCES = {"web_speech", "gemini_audio", "whisper", "mock"}


def build_stt_result_from_payload(payload: dict[str, Any]) -> STTResult:
    """
    프론트엔드 Web Speech API 또는 백엔드 Gemini 오디오 전사 결과를
    AI-2 내부 표준 STTResult 구조로 변환한다.
    """
    transcript = str(payload.get("transcript", "")).strip()
    source = str(payload.get("source", "web_speech")).strip()
    language = str(payload.get("language", "ko-KR")).strip()
    confidence = payload.get("confidence")

    if source not in SUPPORTED_STT_SOURCES:
        source = "mock"

    if confidence is not None:
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = None

    return STTResult(
        transcript=transcript,
        source=source,
        confidence=confidence,
        language=language,
    )


def build_mock_stt_payload(
    transcript: str,
    source: str = "mock",
    confidence: float | None = 1.0,
    language: str = "ko-KR",
) -> dict[str, Any]:
    """
    실제 마이크 입력 없이 STT 결과를 흉내 내는 테스트용 payload를 만든다.
    """
    return {
        "transcript": transcript,
        "source": source,
        "confidence": confidence,
        "language": language,
    }


def should_use_stt_fallback(stt_result: STTResult, min_confidence: float = 0.6) -> bool:
    """
    Web Speech API 결과가 비어 있거나 confidence가 낮으면
    서버 오디오 전사 fallback을 사용할지 판단한다.

    실제 Gemini 오디오 전사는 백엔드에서 붙이고,
    여기서는 fallback 필요 여부만 판단한다.
    """
    if not stt_result.transcript:
        return True

    if stt_result.confidence is not None and stt_result.confidence < min_confidence:
        return True

    return False


def should_use_whisper_fallback(
    stt_result: STTResult,
    min_confidence: float = 0.6,
) -> bool:
    """Backward-compatible alias for the provider-neutral fallback check."""
    return should_use_stt_fallback(stt_result, min_confidence)
