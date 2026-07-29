from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai.attention.router import router as attention_router
from ai.nudge.router import router as nudge_router


app = FastAPI(title="LumiNudge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://luminudge.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(attention_router)
app.include_router(nudge_router)

DATA_DIR = Path(__file__).parent / "data"
ONBOARDING_FILE = DATA_DIR / "onboarding_records.jsonl"

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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


@app.post("/onboarding", status_code=201)
def create_onboarding(record: OnboardingRecord):
    DATA_DIR.mkdir(exist_ok=True)
    with open(ONBOARDING_FILE, "a", encoding="utf-8") as f:
        f.write(record.model_dump_json() + "\n")
    return {"status": "ok"}
