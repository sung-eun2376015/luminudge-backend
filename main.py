from dotenv import load_dotenv
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from ai.attention.router import router as attention_router
from ai.nudge.router import router as nudge_router
from ai.nudge.nudge_trigger import classify_child_tier
from storage.onboarding import (
    OnboardingCreateResponse,
    OnboardingRecord,
    initialize_database,
    save_onboarding_record,
)

load_dotenv()

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

@app.on_event("startup")
def on_startup():
    initialize_database()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/onboarding",
    response_model=OnboardingCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_onboarding(record: OnboardingRecord) -> OnboardingCreateResponse:
    child_tier = classify_child_tier(
        child_age=record.ageYears,
        can_follow_simple_instruction=record.canFollowSimpleInstruction,
        can_speak=record.canSpeak,
    )
    stored_record = save_onboarding_record(record, child_tier)
    return OnboardingCreateResponse(
        onboarding_id=stored_record.id,
        child_tier=child_tier,
    )
