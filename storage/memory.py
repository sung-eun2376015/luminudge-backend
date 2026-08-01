from typing import Any


# MVP용 메모리 저장소입니다. 서버를 재시작하면 모든 데이터가 사라집니다.
sessions: dict[str, dict[str, Any]] = {}


def save_session(session_id: str, session: dict[str, Any]) -> None:
    sessions[session_id] = session


def get_session(session_id: str) -> dict[str, Any] | None:
    return sessions.get(session_id)


def save_attention_event(
    session_id: str,
    event: dict[str, Any],
) -> None:
    session = get_session(session_id)
    if session is None:
        raise KeyError(session_id)
    session.setdefault("attention_events", []).append(event)


def get_attention_events(session_id: str) -> list[dict[str, Any]]:
    session = get_session(session_id)
    if session is None:
        return []
    return session.get("attention_events", [])


def update_attention_event(
    session_id: str,
    event_id: str,
    updates: dict[str, Any],
) -> None:
    for event in get_attention_events(session_id):
        if event.get("event_id") == event_id:
            event.update(updates)
            return
    raise KeyError(event_id)


def save_mission(
    session_id: str,
    mission_id: str,
    mission: dict[str, Any],
) -> None:
    session = get_session(session_id)
    if session is None:
        raise KeyError(session_id)
    session["missions"][mission_id] = mission


def get_mission(session_id: str, mission_id: str) -> dict[str, Any] | None:
    session = get_session(session_id)
    if session is None:
        return None
    return session["missions"].get(mission_id)
