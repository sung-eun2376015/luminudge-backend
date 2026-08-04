CREATE TABLE IF NOT EXISTS viewing_sessions (
    id VARCHAR PRIMARY KEY,
    onboarding_id INTEGER NOT NULL,
    youtube_url VARCHAR NOT NULL,
    subtitle_name VARCHAR,
    subtitle_source VARCHAR NOT NULL,
    child_tier VARCHAR NOT NULL,
    baseline JSON NOT NULL,
    captions JSON NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'active',
    created_at VARCHAR NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_viewing_sessions_onboarding_id
    ON viewing_sessions (onboarding_id);

CREATE TABLE IF NOT EXISTS attention_events (
    event_id VARCHAR PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    mission_id VARCHAR,
    payload JSON NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_attention_events_session_id
    ON attention_events (session_id);

CREATE TABLE IF NOT EXISTS missions (
    mission_id VARCHAR PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    data JSON NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_missions_session_id
    ON missions (session_id);
