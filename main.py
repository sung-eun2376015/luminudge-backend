import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

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

from ai.attention.router import router as attention_router  # 추가

app = FastAPI(title="LumiNudge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://luminudge.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(attention_router)  # 추가

MOCK_DATA_DIR = Path(__file__).parent / "mock_data"
MOCK_SUBTITLE_FILES = {
    "pinkfong": MOCK_DATA_DIR / "subtitle_pinkfong.json",
    "pororo": MOCK_DATA_DIR / "subtitle_pororo.json",
}

# MVP용 메모리 저장소입니다. 서버를 재시작하면 세션이 사라집니다.
sessions: dict[str, dict[str, Any]] = {}


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

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/subtitles/{video_name}")
def get_subtitles(video_name: str):
    file_path = get_mock_subtitle_path(video_name)
    return load_captions(file_path)


@app.post(
    "/sessions",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(request: SessionCreateRequest) -> SessionCreateResponse:
    subtitle_path = get_mock_subtitle_path(request.subtitle_name)
    captions = load_captions(subtitle_path)
    session_id = uuid4().hex

    sessions[session_id] = {
        "youtube_url": request.youtube_url,
        "subtitle_name": request.subtitle_name,
        "child_tier": request.child_tier,
        "captions": captions,
        "nudge_service": NudgeService(cooldown_seconds=10),
        "missions": {},
    }

    return SessionCreateResponse(
        session_id=session_id,
        youtube_url=request.youtube_url,
        subtitle_name=request.subtitle_name,
        child_tier=request.child_tier,
        caption_count=len(captions),
        subtitle_source=f"mock_data/{subtitle_path.name}",
    )


@app.post("/sessions/{session_id}/nudge", response_model=NudgeResponse)
def create_nudge(session_id: str, payload: ClsPayload) -> dict[str, Any]:
    session = sessions.get(session_id)
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
            session["missions"][created_mission["mission_id"]] = created_mission
        return response
    except ValueError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post(
    "/sessions/{session_id}/missions/{mission_id}/responses",
    response_model=MissionResponseResult,
)
def submit_mission_response(
    session_id: str,
    mission_id: str,
    request: MissionResponseRequest,
) -> MissionResponseResult:
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    mission = session["missions"].get(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="미션을 찾을 수 없습니다")
    if mission["answered"]:
        raise HTTPException(status_code=409, detail="이미 답변한 미션입니다")

    result = evaluate_mission_response(mission=mission, request=request)
    mission["responses"].append(request.model_dump())
    mission["result"] = result.model_dump()
    mission["answered"] = True
    return result
