from typing import Any, Dict

from ai.attention.schemas import ClsPayload
from ai.nudge.nudge_trigger import build_nudge_event
from ai.nudge.prefetch_queue import MissionQueue


def build_nudge_from_attention(
    payload: ClsPayload,
    mission_queue: MissionQueue,
    child_tier: str,
) -> Dict[str, Any]:
    event = build_nudge_event(
        cls_score=payload.cls_score,
        current_time=payload.timestamp,
        mission_queue=mission_queue,
        child_tier=child_tier,
    )

    # AI1과 AI2가 판단한 강도가 같은지 확인
    if event["trigger_strength"] != payload.intensity:
        raise ValueError(
            "CLS intensity mismatch: "
            f"AI1={payload.intensity}, "
            f"AI2={event['trigger_strength']}"
        )

    # 분석 근거도 결과에 포함
    event["attention_metrics"] = {
        "gv": payload.gv,
        "fd": payload.fd,
        "br": payload.br,
    }

    return event