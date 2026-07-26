from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
from pathlib import Path

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

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/subtitles/{video_name}")
def get_subtitles(video_name: str):
    file_path = MOCK_DATA_DIR / f"subtitle_{video_name}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="자막 파일을 찾을 수 없습니다")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)