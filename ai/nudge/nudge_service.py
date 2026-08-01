from typing import Any, Callable, Dict, List, Optional

from ai.attention.schemas import ClsPayload
from ai.nudge.caption_slicer import build_caption_context
from ai.nudge.mission_generator import generate_mission
from ai.nudge.nudge_trigger import build_nudge_event
from ai.nudge.nudge_trigger import select_tier_mission
from ai.nudge.prefetch_queue import MissionQueue, QueuedMission
from ai.nudge.schemas import NudgeResponse


MissionGenerator = Callable[[Dict[str, Any], str], Dict[str, Any]]


class NudgeService:
    """Connect attention results to caption-aware nudge events."""

    def __init__(self) -> None:
        self._created_mission: Optional[Dict[str, Any]] = None

    def take_created_mission(self) -> Optional[Dict[str, Any]]:
        """Return and clear the mission created by the latest process call."""
        mission = self._created_mission
        self._created_mission = None
        return mission

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
        mission_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._created_mission = None
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

        mission_queue = MissionQueue()

        if payload.intensity == "strong":
            context = build_caption_context(captions, payload.timestamp)
            mission_generator = generator or self._generate_mission
            mission = mission_generator(context, child_tier)
            selected_mission = select_tier_mission(mission, child_tier)
            if mission_id is not None:
                self._created_mission = {
                    "mission_id": mission_id,
                    "type": selected_mission.get("type", "fallback"),
                    "prompt": selected_mission.get(
                        "prompt", "루미랑 같이 화면을 한 번 볼까요?"
                    ),
                    "choices": selected_mission.get("choices"),
                    "answer": selected_mission.get("answer"),
                    "expected_keywords": selected_mission.get("expected_keywords"),
                    "context_source": mission.get("context_source"),
                    "scene_summary": mission.get("scene_summary"),
                    "video_timestamp": payload.timestamp,
                    "answered": False,
                    "responses": [],
                }
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
            mission_id=mission_id,
        )
        event["attention"] = metrics
        return self._frontend_response(event)
