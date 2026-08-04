import os
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, Session, SQLModel, select

from storage.onboarding import engine


class ViewingSessionDB(SQLModel, table=True):
    __tablename__ = "viewing_sessions"

    id: str = Field(primary_key=True)
    onboarding_id: int = Field(index=True)
    youtube_url: str
    subtitle_name: Optional[str] = None
    subtitle_source: str
    child_tier: str
    baseline: dict[str, Any] = Field(sa_column=Column(JSON))
    captions: list[dict[str, Any]] = Field(sa_column=Column(JSON))
    status: str = "active"
    created_at: str


class AttentionEventDB(SQLModel, table=True):
    __tablename__ = "attention_events"

    event_id: str = Field(primary_key=True)
    session_id: str = Field(index=True)
    mission_id: Optional[str] = Field(default=None, index=True)
    payload: dict[str, Any] = Field(sa_column=Column(JSON))


class MissionDB(SQLModel, table=True):
    __tablename__ = "missions"

    mission_id: str = Field(primary_key=True)
    session_id: str = Field(index=True)
    data: dict[str, Any] = Field(sa_column=Column(JSON))


# 요청 중 반복 조회를 줄이는 캐시입니다. DB가 원본이며 캐시가 없으면 DB에서 복원합니다.
sessions: dict[str, dict[str, Any]] = {}


def _database_enabled() -> bool:
    return os.getenv("SESSION_STORAGE", "database").lower() == "database"


def _session_to_dict(record: ViewingSessionDB) -> dict[str, Any]:
    return {
        "onboarding_id": record.onboarding_id,
        "youtube_url": record.youtube_url,
        "subtitle_name": record.subtitle_name,
        "subtitle_source": record.subtitle_source,
        "child_tier": record.child_tier,
        "baseline": record.baseline,
        "captions": record.captions,
        "attention_events": [],
        "missions": {},
    }


def save_session(session_id: str, session: dict[str, Any]) -> None:
    session.setdefault("attention_events", [])
    session.setdefault("missions", {})
    sessions[session_id] = session
    if not _database_enabled():
        return
    record = ViewingSessionDB(
        id=session_id,
        onboarding_id=session["onboarding_id"],
        youtube_url=session["youtube_url"],
        subtitle_name=session.get("subtitle_name"),
        subtitle_source=session["subtitle_source"],
        child_tier=session["child_tier"],
        baseline=session["baseline"],
        captions=session["captions"],
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    with Session(engine) as db:
        db.add(record)
        db.commit()


def get_session(session_id: str) -> dict[str, Any] | None:
    cached = sessions.get(session_id)
    if cached is not None:
        return cached
    if not _database_enabled():
        return None
    with Session(engine) as db:
        record = db.get(ViewingSessionDB, session_id)
    if record is None:
        return None
    restored = _session_to_dict(record)
    restored["attention_events"] = get_attention_events(session_id)
    with Session(engine) as db:
        mission_records = db.exec(
            select(MissionDB).where(MissionDB.session_id == session_id)
        ).all()
    restored["missions"] = {item.mission_id: item.data for item in mission_records}
    sessions[session_id] = restored
    return restored


def save_attention_event(session_id: str, event: dict[str, Any]) -> None:
    session = get_session(session_id)
    if session is None:
        raise KeyError(session_id)
    session.setdefault("attention_events", []).append(event)
    if not _database_enabled():
        return
    with Session(engine) as db:
        db.add(
            AttentionEventDB(
                event_id=event["event_id"],
                session_id=session_id,
                mission_id=event.get("mission_id"),
                payload=event,
            )
        )
        db.commit()


def get_attention_events(session_id: str) -> list[dict[str, Any]]:
    cached = sessions.get(session_id)
    if cached is not None and cached.get("attention_events"):
        return cached["attention_events"]
    if not _database_enabled():
        return []
    with Session(engine) as db:
        records = db.exec(
            select(AttentionEventDB).where(AttentionEventDB.session_id == session_id)
        ).all()
    return [record.payload for record in records]


def update_attention_event(
    session_id: str,
    event_id: str,
    updates: dict[str, Any],
) -> None:
    session = get_session(session_id)
    if session is None:
        raise KeyError(session_id)
    for event in session.setdefault("attention_events", []):
        if event.get("event_id") == event_id:
            event.update(updates)
            break
    else:
        raise KeyError(event_id)
    if not _database_enabled():
        return
    with Session(engine) as db:
        record = db.get(AttentionEventDB, event_id)
        if record is None:
            raise KeyError(event_id)
        record.payload = dict(event)
        record.mission_id = event.get("mission_id")
        db.add(record)
        db.commit()


def save_mission(
    session_id: str,
    mission_id: str,
    mission: dict[str, Any],
) -> None:
    session = get_session(session_id)
    if session is None:
        raise KeyError(session_id)
    session.setdefault("missions", {})[mission_id] = mission
    if not _database_enabled():
        return
    with Session(engine) as db:
        record = db.get(MissionDB, mission_id)
        if record is None:
            record = MissionDB(
                mission_id=mission_id,
                session_id=session_id,
                data=mission,
            )
        else:
            record.data = dict(mission)
        db.add(record)
        db.commit()


def get_mission(session_id: str, mission_id: str) -> dict[str, Any] | None:
    session = get_session(session_id)
    if session is None:
        return None
    cached = session.setdefault("missions", {}).get(mission_id)
    if cached is not None:
        return cached
    if not _database_enabled():
        return None
    with Session(engine) as db:
        record = db.get(MissionDB, mission_id)
    if record is None or record.session_id != session_id:
        return None
    session["missions"][mission_id] = record.data
    return record.data
