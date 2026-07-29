# stt_csr.py

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class STTResult:
    transcript: str
    source: str = "web_speech"
    confidence: float | None = None
    language: str = "ko-KR"


@dataclass
class CSRResult:
    csr_score: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    is_contextual: bool
    transcript: str
    expected_keywords: list[str]
    source: str


def normalize_text(text: str) -> str:
    """
    한국어 답변 비교를 위한 최소 정규화 함수.
    4주차에서는 가볍게 공백 제거 + 소문자 처리만 수행한다.
    """
    if not text:
        return ""

    return text.strip().lower().replace(" ", "")


def extract_expected_keywords(mission: dict[str, Any]) -> list[str]:
    """
    tier3 미션에서 expected_keywords를 꺼낸다.
    없으면 answer 또는 keywords를 fallback으로 사용한다.
    """
    if not mission:
        return []

    expected_keywords = mission.get("expected_keywords")
    if isinstance(expected_keywords, list):
        return [str(keyword) for keyword in expected_keywords if str(keyword).strip()]

    answer = mission.get("answer")
    if answer:
        return [str(answer)]

    keywords = mission.get("keywords")
    if isinstance(keywords, list):
        return [str(keyword) for keyword in keywords if str(keyword).strip()]

    return []


def calculate_keyword_overlap_csr(
    transcript: str,
    expected_keywords: list[str],
) -> tuple[float, list[str], list[str]]:
    """
    임시 CSR 계산 방식.
    아이 답변 안에 expected_keywords가 얼마나 포함되어 있는지 비율로 계산한다.

    예:
    transcript = "토끼가 깡충 뛰었어"
    expected_keywords = ["토끼", "깡충"]
    csr_score = 1.0
    """
    if not transcript or not expected_keywords:
        return 0.0, [], expected_keywords

    normalized_transcript = normalize_text(transcript)

    matched_keywords: list[str] = []
    missing_keywords: list[str] = []

    for keyword in expected_keywords:
        normalized_keyword = normalize_text(keyword)

        if normalized_keyword and normalized_keyword in normalized_transcript:
            matched_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)

    csr_score = len(matched_keywords) / len(expected_keywords)

    return round(csr_score, 3), matched_keywords, missing_keywords


def evaluate_stt_response(
    stt_result: STTResult,
    mission: dict[str, Any],
    threshold: float = 0.5,
) -> CSRResult:
    """
    STT 텍스트와 미션의 expected_keywords를 비교해 CSR 결과를 반환한다.
    """
    expected_keywords = extract_expected_keywords(mission)

    csr_score, matched_keywords, missing_keywords = calculate_keyword_overlap_csr(
        transcript=stt_result.transcript,
        expected_keywords=expected_keywords,
    )

    return CSRResult(
        csr_score=csr_score,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        is_contextual=csr_score >= threshold,
        transcript=stt_result.transcript,
        expected_keywords=expected_keywords,
        source=stt_result.source,
    )


def build_csr_event(
    stt_result: STTResult,
    mission: dict[str, Any],
    threshold: float = 0.5,
) -> dict[str, Any]:
    """
    Dev 또는 리포트 로깅 파트에서 사용할 수 있는 CSR event JSON을 생성한다.
    """
    result = evaluate_stt_response(
        stt_result=stt_result,
        mission=mission,
        threshold=threshold,
    )

    return {
        "event_type": "csr_evaluation",
        **asdict(result),
    }