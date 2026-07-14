# response_evaluator.py

from __future__ import annotations

from typing import Any

from ai.nudge.stt_adapter import (
    build_stt_result_from_payload,
    should_use_whisper_fallback,
)
from ai.nudge.stt_csr import build_csr_event

def evaluate_response_from_stt_payload(
    stt_payload: dict[str, Any],
    mission: dict[str, Any],
    threshold: float = 0.5,
) -> dict[str, Any]:
    """
    프론트엔드 또는 백엔드에서 전달된 STT payload를 받아
    CSR event까지 생성한다.

    흐름:
    STT payload
    → STTResult 변환
    → Whisper fallback 필요 여부 판단
    → CSR 계산
    → response_evaluation event 반환
    """
    stt_result = build_stt_result_from_payload(stt_payload)
    needs_whisper_fallback = should_use_whisper_fallback(stt_result)

    csr_event = build_csr_event(
        stt_result=stt_result,
        mission=mission,
        threshold=threshold,
    )

    return {
        "event_type": "response_evaluation",
        "needs_whisper_fallback": needs_whisper_fallback,
        "stt": {
            "transcript": stt_result.transcript,
            "source": stt_result.source,
            "confidence": stt_result.confidence,
            "language": stt_result.language,
        },
        "csr": {
            "csr_score": csr_event["csr_score"],
            "matched_keywords": csr_event["matched_keywords"],
            "missing_keywords": csr_event["missing_keywords"],
            "is_contextual": csr_event["is_contextual"],
            "expected_keywords": csr_event["expected_keywords"],
        },
        "mission": {
            "type": mission.get("type"),
            "prompt": mission.get("prompt"),
        },
    }