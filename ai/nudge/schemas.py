from typing import Any, Literal

from pydantic import BaseModel, Field


class AttentionMetrics(BaseModel):
    gv: float
    fd: float
    br: int


class NudgeQuestion(BaseModel):
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
