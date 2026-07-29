from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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
    should_nudge: bool
    intensity: Literal["none", "soft", "strong"]
    cls_score: float = Field(ge=0.0, le=1.0)
    child_tier: str
    timestamp: float
    pause_video: bool
    source: Literal["no_trigger", "cooldown", "soft_lumi", "mission_queue", "fallback"]
    question: NudgeQuestion | None = None
    context_source: str | None = None
    scene_summary: str | None = None
    cooldown_remaining: float | None = None
    attention: AttentionMetrics

    def to_frontend(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class SessionCreateRequest(BaseModel):
    youtube_url: str = Field(min_length=1)
    subtitle_name: Literal["pinkfong", "pororo"]
    child_tier: Literal["tier1", "tier2", "tier3"]


class SessionCreateResponse(BaseModel):
    session_id: str
    youtube_url: str
    subtitle_name: Literal["pinkfong", "pororo"]
    child_tier: Literal["tier1", "tier2", "tier3"]
    caption_count: int
    subtitle_source: str


class MissionResponseRequest(BaseModel):
    response_type: Literal["choice", "voice", "gesture"]
    answer: str | None = None
    transcript: str | None = None
    stt_source: Literal["web_speech", "whisper", "mock"] = "web_speech"
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
    needs_whisper_fallback: bool = False
