import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from ai.attention.schemas import ClsPayload
from ai.nudge.nudge_service import NudgeService
from ai.nudge.response_service import evaluate_mission_response
from ai.nudge.schemas import (
    MissionResponseRequest,
    MissionResponseResult,
    NudgeResponse,
    SessionCreateRequest,
    SessionCreateResponse,
)
from ai.nudge.audio_transcription_service import (
    AudioTranscriptionError,
    transcribe_audio,
)
from storage.memory import (
    get_mission,
    get_session,
    save_attention_event,
    save_mission,
    save_session,
    update_attention_event,
)
from storage.onboarding import get_onboarding_record


router = APIRouter()

COMMON_ERROR_RESPONSES = {
    404: {"description": "요청한 온보딩, 세션 또는 미션을 찾을 수 없음"},
    422: {"description": "요청 데이터 검증 실패"},
}

MOCK_DATA_DIR = Path(__file__).resolve().parents[2] / "mock_data"
MOCK_SUBTITLE_FILES = {
    "pinkfong": MOCK_DATA_DIR / "subtitle_pinkfong.json",
    "pororo": MOCK_DATA_DIR / "subtitle_pororo.json",
}


def load_captions(file_path: Path) -> list[dict[str, Any]]:
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="자막 파일을 찾을 수 없습니다")

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_mock_subtitle_path(subtitle_name: str) -> Path:
    file_path = MOCK_SUBTITLE_FILES.get(subtitle_name)
    if file_path is None:
        raise HTTPException(status_code=404, detail="지원하지 않는 mock 자막입니다")
    return file_path


def store_response_result(
    session_id: str,
    mission: dict[str, Any],
    request: MissionResponseRequest,
    result: MissionResponseResult,
) -> None:
    mission["responses"].append(
        {
            "request": request.model_dump(),
            "result": result.model_dump(),
        }
    )
    mission["result"] = result.model_dump()
    mission["answered"] = result.reaction == "praise"
    mission["status"] = "completed" if mission["answered"] else "awaiting_retry"
    save_mission(session_id, mission["mission_id"], mission)


@router.get(
    "/subtitles/{video_name}",
    tags=["Subtitles"],
    summary="개발용 mock 자막 조회",
    description="pinkfong 또는 pororo mock 자막을 반환합니다. 운영용 자막 API가 아닙니다.",
    responses={404: {"description": "지원하지 않는 mock 자막"}},
)
def get_subtitles(video_name: str) -> list[dict[str, Any]]:
    file_path = get_mock_subtitle_path(video_name)
    return load_captions(file_path)


@router.post(
    "/sessions",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Sessions"],
    summary="영상 시청 세션 생성",
    description=(
        "온보딩 ID와 YouTube URL로 시청 세션을 생성합니다. captions가 있으면 실제 입력 "
        "자막을 우선 사용하고, 없으면 subtitle_name의 개발용 mock 자막을 사용합니다. "
        "반환된 session_id는 해당 영상 시청이 끝날 때까지 프론트에서 보관해야 합니다."
    ),
    responses=COMMON_ERROR_RESPONSES,
)
def create_session(request: SessionCreateRequest) -> SessionCreateResponse:
    subtitle_path: Path | None = None
    if request.captions:
        captions = [
            {"start": caption.start, "end": caption.end, "text": caption.text}
            for caption in request.captions
        ]
        subtitle_source = "provided_captions"
    else:
        subtitle_path = get_mock_subtitle_path(request.subtitle_name or "")
        captions = load_captions(subtitle_path)
        subtitle_source = f"mock_data/{subtitle_path.name}"
    onboarding = get_onboarding_record(request.onboarding_id)
    if onboarding is None:
        raise HTTPException(status_code=404, detail="온보딩 정보를 찾을 수 없습니다")

    session_id = uuid4().hex
    child_tier = onboarding.childTier

    save_session(
        session_id,
        {
            "onboarding_id": request.onboarding_id,
            "youtube_url": request.youtube_url,
            "subtitle_name": request.subtitle_name,
            "subtitle_source": subtitle_source,
            "child_tier": child_tier,
            "baseline": {
                "gv": onboarding.baselineGV,
                "fd": onboarding.baselineFD,
                "br": onboarding.baselineBR,
                "plr_seconds": onboarding.plr,
            },
            "captions": captions,
            "attention_events": [],
            "missions": {},
        },
    )

    return SessionCreateResponse(
        session_id=session_id,
        onboarding_id=request.onboarding_id,
        youtube_url=request.youtube_url,
        subtitle_name=request.subtitle_name,
        child_tier=child_tier,
        caption_count=len(captions),
        subtitle_source=subtitle_source,
    )


@router.post(
    "/sessions/{session_id}/nudge",
    response_model=NudgeResponse,
    tags=["Attention / Nudge"],
    summary="AI-1 Attention 결과 처리",
    description=(
        "프론트 AI-1이 계산한 ClsPayload를 세션 문맥과 함께 처리합니다. "
        "pause_video가 true이면 프론트는 영상을 정지하고 question을 표시해야 합니다. "
        "timestamp와 video_duration_sec는 초, cooldown_ms는 밀리초 단위입니다."
    ),
    responses={
        **COMMON_ERROR_RESPONSES,
        502: {"description": "Gemini 미션 생성 실패"},
    },
)
def create_nudge(session_id: str, payload: ClsPayload) -> dict[str, Any]:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    event_id = uuid4().hex
    mission_id = uuid4().hex if payload.intensity == "strong" else None
    save_attention_event(
        session_id,
        {
            "event_id": event_id,
            "session_id": session_id,
            "cls_score": payload.cls_score,
            "intensity": payload.intensity,
            "gv": payload.gv,
            "fd": payload.fd,
            "br": payload.br,
            "video_timestamp": payload.timestamp,
            "video_duration_sec": payload.video_duration_sec,
            "cooldown_ms": payload.cooldown_ms,
            "mission_id": mission_id,
            "processing_status": "received",
            "received_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    try:
        nudge_service = NudgeService()
        response = nudge_service.process(
            payload=payload,
            captions=session["captions"],
            child_tier=session["child_tier"],
            mission_id=mission_id,
        )
        created_mission = nudge_service.take_created_mission()
        if created_mission is not None:
            save_mission(
                session_id,
                created_mission["mission_id"],
                created_mission,
            )
        update_attention_event(
            session_id,
            event_id,
            {
                "should_nudge": response["should_nudge"],
                "pause_video": response["pause_video"],
                "response_source": response["source"],
                "processing_status": "completed",
            },
        )
        return response
    except ValueError as error:
        update_attention_event(
            session_id,
            event_id,
            {
                "processing_status": "failed",
                "error": str(error),
            },
        )
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post(
    "/sessions/{session_id}/missions/{mission_id}/responses",
    response_model=MissionResponseResult,
    tags=["Mission Responses"],
    summary="미션 응답 제출",
    description=(
        "choice, voice(Web Speech transcript), gesture 응답을 평가합니다. "
        "response_time_ms는 질문 표시부터 응답 완료까지의 밀리초입니다. "
        "Tier별 권장 매핑은 tier1=gesture, tier2=choice, tier3=voice입니다. "
        "praise는 미션 완료와 영상 재생, hint/retry는 같은 mission_id 재시도를 뜻합니다. "
        "resume_video가 true일 때만 프론트가 영상을 재생합니다. "
        "voice에서 needs_stt_fallback이 true이면 /responses/audio를 호출합니다."
    ),
    responses={
        **COMMON_ERROR_RESPONSES,
        409: {"description": "이미 완료된 미션에 대한 중복 응답"},
    },
)
def submit_mission_response(
    session_id: str,
    mission_id: str,
    request: MissionResponseRequest,
) -> MissionResponseResult:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    mission = get_mission(session_id, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="미션을 찾을 수 없습니다")
    if mission["answered"]:
        raise HTTPException(status_code=409, detail="이미 답변한 미션입니다")

    result = evaluate_mission_response(mission=mission, request=request)
    store_response_result(session_id, mission, request, result)
    return result


@router.post(
    "/sessions/{session_id}/missions/{mission_id}/responses/audio",
    response_model=MissionResponseResult,
    tags=["Mission Responses"],
    summary="Gemini 음성 전사 fallback",
    description=(
        "Web Speech가 transcript를 만들지 못했거나 신뢰도가 낮을 때 녹음 파일을 전송합니다. "
        "audio, response_time_ms, language를 multipart/form-data로 전달합니다."
    ),
    responses={
        400: {"description": "빈 파일, 미지원 확장자 또는 10MB 초과"},
        **COMMON_ERROR_RESPONSES,
        409: {"description": "이미 완료된 미션에 대한 중복 응답"},
        502: {"description": "Gemini 음성 전사 실패"},
    },
)
async def submit_audio_mission_response(
    session_id: str,
    mission_id: str,
    audio: UploadFile = File(...),
    response_time_ms: int = Form(..., ge=0),
    language: str = Form("ko"),
) -> MissionResponseResult:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    mission = get_mission(session_id, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="미션을 찾을 수 없습니다")
    if mission["answered"]:
        raise HTTPException(status_code=409, detail="이미 답변한 미션입니다")

    audio_bytes = await audio.read()
    try:
        transcript = transcribe_audio(
            filename=audio.filename or "response.webm",
            content_type=audio.content_type or "application/octet-stream",
            audio_bytes=audio_bytes,
            language=language,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except AudioTranscriptionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    finally:
        await audio.close()

    request = MissionResponseRequest(
        response_type="voice",
        transcript=transcript,
        stt_source="gemini_audio",
        language=language,
        response_time_ms=response_time_ms,
    )
    result = evaluate_mission_response(mission=mission, request=request)
    store_response_result(session_id, mission, request, result)
    return result
