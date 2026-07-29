import json
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
from ai.nudge.whisper_service import WhisperServiceError, transcribe_audio
from storage.memory import get_mission, get_session, save_mission, save_session


router = APIRouter(tags=["Nudge"])

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


@router.get("/subtitles/{video_name}")
def get_subtitles(video_name: str) -> list[dict[str, Any]]:
    file_path = get_mock_subtitle_path(video_name)
    return load_captions(file_path)


@router.post(
    "/sessions",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(request: SessionCreateRequest) -> SessionCreateResponse:
    subtitle_path = get_mock_subtitle_path(request.subtitle_name)
    captions = load_captions(subtitle_path)
    session_id = uuid4().hex

    save_session(
        session_id,
        {
            "youtube_url": request.youtube_url,
            "subtitle_name": request.subtitle_name,
            "child_tier": request.child_tier,
            "captions": captions,
            "nudge_service": NudgeService(cooldown_seconds=10),
            "missions": {},
        },
    )

    return SessionCreateResponse(
        session_id=session_id,
        youtube_url=request.youtube_url,
        subtitle_name=request.subtitle_name,
        child_tier=request.child_tier,
        caption_count=len(captions),
        subtitle_source=f"mock_data/{subtitle_path.name}",
    )


@router.post("/sessions/{session_id}/nudge", response_model=NudgeResponse)
def create_nudge(session_id: str, payload: ClsPayload) -> dict[str, Any]:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    try:
        mission_id = uuid4().hex if payload.intensity == "strong" else None
        response = session["nudge_service"].process(
            payload=payload,
            captions=session["captions"],
            child_tier=session["child_tier"],
            mission_id=mission_id,
        )
        created_mission = session["nudge_service"].take_created_mission()
        if created_mission is not None:
            save_mission(
                session_id,
                created_mission["mission_id"],
                created_mission,
            )
        return response
    except ValueError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post(
    "/sessions/{session_id}/missions/{mission_id}/responses",
    response_model=MissionResponseResult,
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
    store_response_result(mission, request, result)
    return result


@router.post(
    "/sessions/{session_id}/missions/{mission_id}/responses/audio",
    response_model=MissionResponseResult,
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
    except WhisperServiceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    finally:
        await audio.close()

    request = MissionResponseRequest(
        response_type="voice",
        transcript=transcript,
        stt_source="whisper",
        language=language,
        response_time_ms=response_time_ms,
    )
    result = evaluate_mission_response(mission=mission, request=request)
    store_response_result(mission, request, result)
    return result
