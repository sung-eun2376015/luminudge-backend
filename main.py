import os
from typing import Literal, Optional

import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Field, SQLModel, Session, create_engine

load_dotenv()

app = FastAPI(title="LumiNudge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://luminudge.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_DATA_DIR = Path(__file__).parent / "mock_data"

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)


@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)


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


# 프론트(src/types/onboarding.ts)의 OnboardingRecord와 필드 맞춤.
# 프론트는 이 요청을 best-effort로 보내고, 실패해도 localStorage 저장을 1차 소스로 쓰므로
# 여기서는 검증 후 그대로 적재만 하면 된다 (실시간 처리/응답값 필요 없음).
class OnboardingRecord(BaseModel):
    ageYears: int
    gender: Literal["male", "female"]
    baselineGV: float
    baselineFD: float
    baselineBR: float
    plr: float
    completedAt: str


class OnboardingRecordDB(SQLModel, table=True):
    __tablename__ = "onboarding_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    ageYears: int
    gender: str
    baselineGV: float
    baselineFD: float
    baselineBR: float
    plr: float
    completedAt: str


@app.post("/onboarding", status_code=201)
def create_onboarding(record: OnboardingRecord):
    with Session(engine) as session:
        session.add(OnboardingRecordDB(**record.model_dump()))
        session.commit()
    return {"status": "ok"}