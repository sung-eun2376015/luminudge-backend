from typing import Any, Dict, Optional

from ai.nudge.prefetch_queue import MissionQueue, QueuedMission


SOFT_THRESHOLD = 0.5
STRONG_THRESHOLD = 0.7


def get_trigger_strength(cls_score: float) -> str:
    if cls_score >= STRONG_THRESHOLD:
        return "strong"

    if cls_score >= SOFT_THRESHOLD:
        return "soft"

    return "none"


def should_nudge(cls_score: float) -> bool:
    return get_trigger_strength(cls_score) != "none"


def classify_child_tier(
    child_age: int,
    can_follow_simple_instruction: bool = True,
    can_speak: bool = False,
) -> str:
    if child_age <= 2:
        return "tier1"

    if child_age <= 4:
        if can_follow_simple_instruction:
            return "tier2"
        return "tier1"

    if can_speak:
        return "tier3"

    return "tier2"


def select_tier_mission(mission: Dict[str, Any], child_tier: str) -> Dict[str, Any]:
    missions = mission.get("missions")

    if isinstance(missions, dict):
        tier_mission = missions.get(child_tier)

        if tier_mission:
            return tier_mission

        fallback_order = ["tier2", "tier1", "tier3"]

        for tier in fallback_order:
            if tier in missions:
                return missions[tier]

    return {
        "type": mission.get("mission_type", "fallback"),
        "prompt": mission.get("mission_text", "루미랑 같이 화면을 한 번 볼까요?"),
    }


def build_fallback_nudge_event(
    cls_score: float,
    child_tier: str,
    current_time: float,
) -> Dict[str, Any]:
    trigger_strength = get_trigger_strength(cls_score)

    return {
        "should_nudge": should_nudge(cls_score),
        "trigger_strength": trigger_strength,
        "cls_score": cls_score,
        "child_tier": child_tier,
        "current_time": current_time,
        "mission_type": "fallback",
        "nudge_text": "루미랑 같이 화면을 한 번 볼까요?",
        "pause_video": trigger_strength == "strong",
        "source": "fallback",
    }


def build_nudge_event(
    cls_score: float,
    current_time: float,
    mission_queue: MissionQueue,
    child_tier: str,
) -> Dict[str, Any]:
    trigger_strength = get_trigger_strength(cls_score)

    if trigger_strength == "none":
        return {
            "should_nudge": False,
            "trigger_strength": "none",
            "cls_score": cls_score,
            "child_tier": child_tier,
            "current_time": current_time,
            "mission_type": None,
            "nudge_text": None,
            "pause_video": False,
            "source": "no_trigger",
        }

    queued_mission: Optional[QueuedMission] = mission_queue.get_ready(current_time)

    if queued_mission is None:
        return build_fallback_nudge_event(
            cls_score=cls_score,
            child_tier=child_tier,
            current_time=current_time,
        )

    selected_mission = select_tier_mission(
        mission=queued_mission.mission,
        child_tier=child_tier,
    )

    return {
        "should_nudge": True,
        "trigger_strength": trigger_strength,
        "cls_score": cls_score,
        "child_tier": child_tier,
        "current_time": current_time,
        "mission_type": selected_mission.get("type"),
        "nudge_text": selected_mission.get("prompt"),
        "pause_video": trigger_strength == "strong",
        "source": "mission_queue",
        "context_source": queued_mission.mission.get("context_source"),
        "scene_summary": queued_mission.mission.get("scene_summary"),
    }