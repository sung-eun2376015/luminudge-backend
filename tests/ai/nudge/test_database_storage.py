import os

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

import storage.memory as storage


def test_session_and_mission_are_restored_from_database() -> None:
    original_engine = storage.engine
    original_mode = os.environ.get("SESSION_STORAGE")
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        storage.engine = test_engine
        os.environ["SESSION_STORAGE"] = "database"
        SQLModel.metadata.create_all(test_engine)
        storage.sessions.clear()

        storage.save_session(
            "session-1",
            {
                "onboarding_id": 17,
                "youtube_url": "https://www.youtube.com/watch?v=example",
                "subtitle_name": None,
                "subtitle_source": "provided_captions",
                "child_tier": "tier2",
                "baseline": {"gv": 0.25, "fd": 1.2, "br": 15, "plr_seconds": 2.8},
                "captions": [{"start": 0, "end": 10, "text": "테스트 자막"}],
                "attention_events": [],
                "missions": {},
            },
        )
        storage.save_attention_event(
            "session-1",
            {
                "event_id": "event-1",
                "session_id": "session-1",
                "mission_id": "mission-1",
                "intensity": "strong",
            },
        )
        storage.save_mission(
            "session-1",
            "mission-1",
            {
                "mission_id": "mission-1",
                "type": "choice",
                "prompt": "무엇이 보이나요?",
                "answered": False,
                "responses": [],
            },
        )

        storage.sessions.clear()
        restored = storage.get_session("session-1")
        assert restored is not None
        assert restored["captions"][0]["text"] == "테스트 자막"
        assert restored["attention_events"][0]["event_id"] == "event-1"
        assert restored["missions"]["mission-1"]["answered"] is False
    finally:
        storage.sessions.clear()
        storage.engine = original_engine
        if original_mode is None:
            os.environ.pop("SESSION_STORAGE", None)
        else:
            os.environ["SESSION_STORAGE"] = original_mode


if __name__ == "__main__":
    test_session_and_mission_are_restored_from_database()
    print("PASS: database session + attention + mission persistence")
