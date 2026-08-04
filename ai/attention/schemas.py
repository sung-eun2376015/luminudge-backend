from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class ClsPayload(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cls_score": 0.8,
                "intensity": "strong",
                "gv": 0.1,
                "fd": 5.0,
                "br": 2,
                "timestamp": 35.2,
                "video_duration_sec": 300,
                "cooldown_ms": 10000,
            }
        }
    )

    cls_score: float = Field(ge=0.0, le=1.0, description="AI-1이 계산한 CLS 점수")
    intensity: Literal["none", "soft", "strong"] = Field(
        description="AI-1이 결정한 최종 개입 강도"
    )
    gv: float = Field(ge=0, description="Gaze Variance")
    fd: float = Field(ge=0, description="Fixation Duration")
    br: int = Field(ge=0, description="Blink Rate")
    timestamp: float = Field(ge=0, description="영상 시작점 기준 현재 재생 위치(초)")
    video_duration_sec: float = Field(gt=0, description="영상 전체 길이(초)")
    cooldown_ms: int = Field(
        ge=0,
        description="프론트에서 적용한 Nudge 쿨다운(밀리초). 백엔드는 기록만 합니다.",
    )
