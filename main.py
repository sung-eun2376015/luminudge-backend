from dotenv import load_dotenv
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from ai.nudge.router import router as nudge_router
from ai.nudge.nudge_trigger import classify_child_tier
from storage.onboarding import (
    OnboardingCreateResponse,
    OnboardingRecord,
    initialize_database,
    save_onboarding_record,
)

load_dotenv()

tags_metadata = [
    {"name": "System", "description": "서버 상태 확인"},
    {"name": "Onboarding", "description": "아동 초기 정보와 발달 tier 생성"},
    {"name": "Sessions", "description": "영상 시청 세션 생성"},
    {"name": "Subtitles", "description": "개발용 mock 자막 확인"},
    {"name": "Attention / Nudge", "description": "프론트 AI-1 결과를 Nudge로 변환"},
    {"name": "Mission Responses", "description": "질문 응답 평가와 음성 fallback"},
]

app = FastAPI(
    title="LumiNudge Backend API",
    version="1.0.0",
    description=(
        "프론트 AI-1의 Attention 분석 결과를 받아 아동 맞춤형 Nudge를 생성합니다. "
        "프론트는 온보딩 → 세션 → Nudge → 미션 응답 순서로 호출합니다."
    ),
    openapi_tags=tags_metadata,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://luminudge.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nudge_router)

@app.on_event("startup")
def on_startup():
    initialize_database()


@app.get("/health", tags=["System"], summary="서버 상태 확인")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/onboarding",
    response_model=OnboardingCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Onboarding"],
    summary="온보딩 생성",
    description=(
        "아동 정보를 저장하고 tier를 계산합니다. 반환된 onboarding_id는 프론트에서 "
        "보관한 뒤 세션 생성 요청에 사용합니다."
    ),
    responses={422: {"description": "온보딩 데이터 검증 실패"}},
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
