from typing import Any, Dict, Optional

from ai.nudge.prefetch_queue import MissionQueue, QueuedMission


def classify_child_tier(
    child_age: int,
    can_follow_simple_instruction: bool = True,
    can_speak: bool = False,
) -> str:
    if child_age <= 2:
        return "tier1"

    if child_age <= 4:
        return "tier2" if can_follow_simple_instruction else "tier1"

    return "tier3" if can_speak else "tier2"


def select_tier_mission(mission: Dict[str, Any], child_tier: str) -> Dict[str, Any]:
    missions = mission.get("missions")

    if isinstance(missions, dict):
        tier_mission = missions.get(child_tier)
        if tier_mission:
            return tier_mission

        for tier in ("tier2", "tier1", "tier3"):
            if tier in missions:
                return missions[tier]

    return {
        "type": mission.get("mission_type", "fallback"),
        "prompt": mission.get("mission_text", "루미랑 같이 화면을 한 번 볼까요?"),
    }


def _question_from_mission(mission: Dict[str, Any]) -> Dict[str, Any]:
    question = {
        "type": mission.get("type", "fallback"),
        "text": mission.get("prompt", "루미랑 같이 화면을 한 번 볼까요?"),
    }
    choices = mission.get("choices")
    if isinstance(choices, list):
        question["choices"] = choices
    return question


def build_nudge_event(
    cls_score: float,
    intensity: str,
    timestamp: float,
    mission_queue: MissionQueue,
    child_tier: str,
    mission_id: str | None = None,
) -> Dict[str, Any]:
    base = {
        "intensity": intensity,
        "cls_score": cls_score,
        "child_tier": child_tier,
        "timestamp": timestamp,
    }

    if intensity == "none":
        return {
            **base,
            "should_nudge": False,
            "pause_video": False,
            "source": "no_trigger",
            "question": None,
        }

    if intensity == "soft":
        return {
            **base,
            "should_nudge": True,
            "pause_video": False,
            "source": "soft_lumi",
            "question": None,
        }

    queued_mission: Optional[QueuedMission] = mission_queue.get_ready(timestamp)
    if queued_mission is None:
        return {
            **base,
            "should_nudge": True,
            "pause_video": True,
            "source": "fallback",
            "question": {
                "type": "fallback",
                "text": "루미랑 같이 화면을 한 번 볼까요?",
            },
        }

    selected_mission = select_tier_mission(queued_mission.mission, child_tier)
    question = _question_from_mission(selected_mission)
    if mission_id is not None:
        question["mission_id"] = mission_id
    return {
        **base,
        "should_nudge": True,
        "pause_video": True,
        "source": "mission_queue",
        "question": question,
        "context_source": queued_mission.mission.get("context_source"),
        "scene_summary": queued_mission.mission.get("scene_summary"),
    }
