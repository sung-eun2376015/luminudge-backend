from typing import Any

from ai.nudge.response_evaluator import evaluate_response_from_stt_payload
from ai.nudge.semantic_csr import calculate_semantic_csr
from ai.nudge.schemas import MissionResponseRequest, MissionResponseResult
from ai.nudge.stt_csr import normalize_text


def _base_result(
    *,
    mission_id: str,
    request: MissionResponseRequest,
    is_correct: bool,
    reaction: str,
    feedback_text: str,
    csr_score: float | None = None,
    csr_method: str | None = None,
    needs_whisper_fallback: bool = False,
) -> MissionResponseResult:
    needs_retry = reaction != "praise"
    return MissionResponseResult(
        mission_id=mission_id,
        response_type=request.response_type,
        is_correct=is_correct,
        csr_score=csr_score,
        csr_method=csr_method,
        plr_seconds=round(request.response_time_ms / 1000, 3),
        reaction=reaction,
        feedback_text=feedback_text,
        resume_video=not needs_retry,
        needs_retry=needs_retry,
        needs_whisper_fallback=needs_whisper_fallback,
    )


def evaluate_mission_response(
    mission: dict[str, Any],
    request: MissionResponseRequest,
) -> MissionResponseResult:
    mission_id = str(mission["mission_id"])

    if request.response_type == "choice":
        expected = normalize_text(str(mission.get("answer") or ""))
        submitted = normalize_text(request.answer or "")
        has_objective_answer = bool(expected and expected != normalize_text("없음"))
        is_correct = submitted == expected if has_objective_answer else bool(submitted)

        if is_correct:
            return _base_result(
                mission_id=mission_id,
                request=request,
                is_correct=True,
                reaction="praise",
                feedback_text="정말 잘했어!",
            )
        return _base_result(
            mission_id=mission_id,
            request=request,
            is_correct=False,
            reaction="hint",
            feedback_text="힌트를 보고 한 번 더 생각해볼까?",
        )

    if request.response_type == "gesture":
        if request.completed:
            return _base_result(
                mission_id=mission_id,
                request=request,
                is_correct=True,
                reaction="praise",
                feedback_text="멋지게 따라 했어!",
            )
        return _base_result(
            mission_id=mission_id,
            request=request,
            is_correct=False,
            reaction="retry",
            feedback_text="괜찮아, 루미와 한 번 더 해보자!",
        )

    evaluation = evaluate_response_from_stt_payload(
        stt_payload={
            "transcript": request.transcript or "",
            "source": request.stt_source,
            "confidence": request.confidence,
            "language": request.language,
        },
        mission=mission,
    )
    csr_score = float(evaluation["csr"]["csr_score"])
    needs_fallback = bool(evaluation["needs_whisper_fallback"])

    if needs_fallback:
        return _base_result(
            mission_id=mission_id,
            request=request,
            is_correct=False,
            csr_score=csr_score,
            csr_method="keyword_fallback",
            reaction="retry",
            feedback_text="목소리를 잘 듣지 못했어. 한 번 더 말해줄래?",
            needs_whisper_fallback=True,
        )

    semantic_result = calculate_semantic_csr(
        transcript=request.transcript or "",
        mission=mission,
    )
    csr_score = semantic_result.csr_score

    if csr_score >= 0.65:
        return _base_result(
            mission_id=mission_id,
            request=request,
            is_correct=True,
            csr_score=csr_score,
            csr_method=semantic_result.method,
            reaction="praise",
            feedback_text="영상 내용을 정말 잘 기억했어!",
        )

    return _base_result(
        mission_id=mission_id,
        request=request,
        is_correct=False,
        csr_score=csr_score,
        csr_method=semantic_result.method,
        reaction="hint",
        feedback_text="힌트를 듣고 한 번 더 말해볼까?",
    )
