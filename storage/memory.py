from typing import Any


# MVP용 메모리 저장소입니다. 서버를 재시작하면 모든 데이터가 사라집니다.
sessions: dict[str, dict[str, Any]] = {}


def save_session(session_id: str, session: dict[str, Any]) -> None:
    sessions[session_id] = session


def get_session(session_id: str) -> dict[str, Any] | None:
    return sessions.get(session_id)


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
