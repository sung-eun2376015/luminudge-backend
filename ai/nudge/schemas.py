from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AttentionMetrics(BaseModel):
    gv: float
    fd: float
    br: int


class NudgeQuestion(BaseModel):
    mission_id: str | None = None
    type: str
    text: str
    choices: list[str] | None = None


class NudgeResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "should_nudge": True,
                "intensity": "strong",
                "cls_score": 0.8,
                "child_tier": "tier2",
                "timestamp": 35.2,
                "pause_video": True,
                "source": "mission_queue",
                "question": {
                    "mission_id": "mission-id",
                    "type": "choice",
                    "text": "방의 온도를 바꾼 것은 무엇일까요?",
                    "choices": ["노란색 버튼", "파란색 공"],
                },
                "context_source": "current",
                "scene_summary": "방의 온도가 바뀌는 장면",
                "attention": {"gv": 0.1, "fd": 5.0, "br": 2},
            }
        }
    )
    should_nudge: bool
    intensity: Literal["none", "soft", "strong"]
    cls_score: float = Field(ge=0.0, le=1.0)
    child_tier: str
    timestamp: float
    pause_video: bool
    source: Literal["no_trigger", "soft_lumi", "mission_queue", "fallback"]
    question: NudgeQuestion | None = None
    context_source: str | None = None
    scene_summary: str | None = None
    attention: AttentionMetrics

    def to_frontend(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class CaptionInput(BaseModel):
    start: float = Field(ge=0, description="자막 시작 시점(초)")
    duration: float | None = Field(default=None, gt=0, description="자막 재생 길이(초)")
    end: float | None = Field(
        default=None,
        gt=0,
        description="자막 종료 시점(초). duration 대신 사용할 수 있습니다.",
    )
    text: str = Field(min_length=1, description="자막 내용")

    @model_validator(mode="after")
    def validate_time_range(self) -> "CaptionInput":
        if self.duration is None and self.end is None:
            raise ValueError("duration 또는 end 중 하나가 필요합니다")
        if self.end is None and self.duration is not None:
            self.end = self.start + self.duration
        if self.end is not None and self.end <= self.start:
            raise ValueError("end는 start보다 커야 합니다")
        return self


class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "youtube_url": "https://www.youtube.com/watch?v=example",
                    "onboarding_id": 17,
                    "captions": [
                        {"start": 28, "duration": 15, "text": "방의 온도가 바뀌어요."}
                    ],
                },
                {
                    "youtube_url": "https://www.youtube.com/watch?v=example",
                    "onboarding_id": 17,
                    "subtitle_name": "pinkfong",
                },
            ]
        }
    )

    youtube_url: str = Field(min_length=1, description="시청할 YouTube URL")
    subtitle_name: Literal["pinkfong", "pororo"] | None = Field(
        default=None, description="개발용 mock 자막 이름"
    )
    captions: list[CaptionInput] | None = Field(
        default=None, description="프론트 또는 자막 모듈이 제공한 실제 자막"
    )
    onboarding_id: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_subtitle_source(self) -> "SessionCreateRequest":
        if not self.captions and self.subtitle_name is None:
            raise ValueError("captions 또는 subtitle_name 중 하나가 필요합니다")
        return self


class SessionCreateResponse(BaseModel):
    session_id: str
    onboarding_id: int
    youtube_url: str
    subtitle_name: Literal["pinkfong", "pororo"] | None = None
    child_tier: Literal["tier1", "tier2", "tier3"]
    caption_count: int
    subtitle_source: str


class MissionResponseRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "response_type": "choice",
                    "answer": "노란색 버튼",
                    "response_time_ms": 2800,
                },
                {
                    "response_type": "voice",
                    "transcript": "방이 파란색으로 변했어요",
                    "stt_source": "web_speech",
                    "confidence": 0.91,
                    "response_time_ms": 3400,
                },
            ]
        }
    )
    response_type: Literal["choice", "voice", "gesture"]
    answer: str | None = None
    transcript: str | None = None
    stt_source: Literal["web_speech", "gemini_audio", "whisper", "mock"] = "web_speech"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    language: str = "ko-KR"
    completed: bool | None = None
    response_time_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_response_value(self) -> "MissionResponseRequest":
        if self.response_type == "choice" and not (self.answer or "").strip():
            raise ValueError("선택형 답변에는 answer가 필요합니다")
        if self.response_type == "voice" and self.transcript is None:
            raise ValueError("음성 답변에는 transcript 필드가 필요합니다")
        if self.response_type == "gesture" and self.completed is None:
            raise ValueError("제스처 답변에는 completed가 필요합니다")
        return self


class MissionResponseResult(BaseModel):
    mission_id: str
    response_type: Literal["choice", "voice", "gesture"]
    is_correct: bool
    csr_score: float | None = Field(default=None, ge=0.0, le=1.0)
    csr_method: Literal["semantic_embedding", "keyword_fallback"] | None = None
    plr_seconds: float = Field(ge=0.0)
    reaction: Literal["praise", "hint", "retry"]
    feedback_text: str
    resume_video: bool
    needs_retry: bool
    needs_stt_fallback: bool = False
    transcript: str | None = None
    stt_source: Literal["web_speech", "gemini_audio", "whisper", "mock"] | None = None
