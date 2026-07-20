import time
from typing import Any, Callable, Dict, List, Optional

from ai.attention.schemas import ClsPayload
from ai.nudge.caption_slicer import build_caption_context
from ai.nudge.mission_generator import generate_mission
from ai.nudge.nudge_trigger import build_nudge_event
from ai.nudge.prefetch_queue import MissionQueue, QueuedMission
from ai.nudge.schemas import NudgeResponse


MissionGenerator = Callable[[Dict[str, Any], str], Dict[str, Any]]


class NudgeService:
    """Connect attention results to caption-aware nudge events."""

    def __init__(
        self,
        cooldown_seconds: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._last_nudge_at: Optional[float] = None

    def _cooldown_remaining(self) -> float:
        if self._last_nudge_at is None:
            return 0.0

        elapsed = self._clock() - self._last_nudge_at
        return max(0.0, self.cooldown_seconds - elapsed)

    @staticmethod
    def _frontend_response(event: Dict[str, Any]) -> Dict[str, Any]:
        return NudgeResponse.model_validate(event).to_frontend()

    @staticmethod
    def _generate_mission(context: Dict[str, Any], child_tier: str) -> Dict[str, Any]:
        return generate_mission(
            current_captions=context["current_captions"],
            previous_captions=context["previous_captions"],
            current_text=context["current_text"],
            previous_text=context["previous_text"],
            selected_context_text=context["selected_context_text"],
            suggested_context_source=context["suggested_context_source"],
            child_tier=child_tier,
        )

    def process(
        self,
        payload: ClsPayload,
        captions: List[Dict[str, Any]],
        child_tier: str,
        generator: Optional[MissionGenerator] = None,
    ) -> Dict[str, Any]:
        metrics = {"gv": payload.gv, "fd": payload.fd, "br": payload.br}

        if payload.intensity == "none":
            event = build_nudge_event(
                cls_score=payload.cls_score,
                intensity=payload.intensity,
                timestamp=payload.timestamp,
                mission_queue=MissionQueue(),
                child_tier=child_tier,
            )
            event["attention"] = metrics
            return self._frontend_response(event)

        cooldown_remaining = self._cooldown_remaining()
        if cooldown_remaining > 0:
            return self._frontend_response({
                "should_nudge": False,
                "intensity": payload.intensity,
                "cls_score": payload.cls_score,
                "child_tier": child_tier,
                "timestamp": payload.timestamp,
                "pause_video": False,
                "source": "cooldown",
                "cooldown_remaining": cooldown_remaining,
                "question": None,
                "attention": metrics,
            })

        mission_queue = MissionQueue()

        if payload.intensity == "strong":
            context = build_caption_context(captions, payload.timestamp)
            mission_generator = generator or self._generate_mission
            mission = mission_generator(context, child_tier)
            mission_queue.add(
                QueuedMission(
                    trigger_time=payload.timestamp,
                    prefetch_time=payload.timestamp,
                    mission=mission,
                    context=context,
                )
            )

        event = build_nudge_event(
            cls_score=payload.cls_score,
            intensity=payload.intensity,
            timestamp=payload.timestamp,
            mission_queue=mission_queue,
            child_tier=child_tier,
        )
        event["attention"] = metrics
        self._last_nudge_at = self._clock()
        return self._frontend_response(event)
