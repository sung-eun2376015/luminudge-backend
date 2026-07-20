import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from ai.attention.schemas import ClsPayload
from ai.nudge.nudge_service import NudgeService
from ai.nudge.schemas import NudgeResponse, SessionCreateRequest, SessionCreateResponse

app = FastAPI(title="LumiNudge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://luminudge.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        return session["nudge_service"].process(
            payload=payload,
            captions=session["captions"],
            child_tier=session["child_tier"],
        )
    except ValueError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
