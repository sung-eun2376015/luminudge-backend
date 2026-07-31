from pydantic import BaseModel, Field
from typing import Literal

class ClsPayload(BaseModel):
    cls_score: float = Field(ge=0.0, le=1.0)
    intensity: Literal["none", "soft", "strong"]
    gv: float
    fd: float
    br: int
    timestamp: int