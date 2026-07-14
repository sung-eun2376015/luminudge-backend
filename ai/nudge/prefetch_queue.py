from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, List, Optional

from ai.nudge.caption_slicer import build_caption_context
from ai.nudge.mission_generator import generate_mission


PREFETCH_SECONDS = 5


@dataclass
class QueuedMission:
    trigger_time: float
    prefetch_time: float
    mission: Dict[str, Any]
    context: Dict[str, Any]
    status: str = "ready"


class MissionQueue:
    def __init__(self) -> None:
        self._queue: List[QueuedMission] = []

    def add(self, item: QueuedMission) -> None:
        self._queue.append(item)
        self._queue.sort(key=lambda mission: mission.trigger_time)

    def get_ready(self, current_time: float) -> Optional[QueuedMission]:
        for index, item in enumerate(self._queue):
            if item.trigger_time <= current_time:
                return self._queue.pop(index)
        return None

    def peek_all(self) -> List[Dict[str, Any]]:
        return [asdict(item) for item in self._queue]

    def clear(self) -> None:
        self._queue.clear()


def mock_generate_mission(context: Dict[str, Any], child_tier: str = "all") -> Dict[str, Any]:
    return {
        "should_generate": context.get("suggested_should_generate", True),
        "context_source": context.get("suggested_context_source", "generic"),
        "mission_type": "mock",
        "mission_text": "루미랑 함께 화면 속 장면을 따라 해볼까?",
        "target_response": "gesture_or_voice",
        "difficulty": child_tier,
        "source": "mock",
    }


def prefetch_mission(
    timeline: List[Dict[str, Any]],
    current_time: float,
    mission_queue: MissionQueue,
    child_tier: str = "all",
    dry_run: bool = True,
    generator: Optional[Callable[..., Dict[str, Any]]] = None,
) -> QueuedMission:
    prefetch_time = current_time + PREFETCH_SECONDS

    context = build_caption_context(
        captions=timeline,
        current_time=prefetch_time,
    )
    
    if generator is not None:
        mission = generator(
            context,
            child_tier=child_tier,
        )
    elif dry_run:
        mission = mock_generate_mission(
            context,
            child_tier=child_tier,
        )
    else:
        mission = generate_mission(
            current_captions=context["current_captions"],
            previous_captions=context["previous_captions"],
            current_text=context["current_text"],
            previous_text=context["previous_text"],
            selected_context_text=context["selected_context_text"],
            suggested_context_source=context["suggested_context_source"],
            child_tier=child_tier,
        )

    queued = QueuedMission(
        trigger_time=prefetch_time,
        prefetch_time=prefetch_time,
        mission=mission,
        context=context,
    )

    mission_queue.add(queued)
    return queued