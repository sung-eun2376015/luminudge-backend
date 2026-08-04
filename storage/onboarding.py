import os
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel
from sqlmodel import Field, SQLModel, Session, create_engine


load_dotenv()


class OnboardingRecord(BaseModel):
    ageYears: int
    gender: Literal["male", "female"]
    canFollowSimpleInstruction: bool
    canSpeak: bool
    baselineGV: float
    baselineFD: float
    baselineBR: float
    plr: float | None = None
    completedAt: str


class OnboardingRecordDB(SQLModel, table=True):
    __tablename__ = "onboarding_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    ageYears: int
    gender: str
    canFollowSimpleInstruction: bool
    canSpeak: bool
    baselineGV: float
    baselineFD: float
    baselineBR: float
    plr: Optional[float] = None
    completedAt: str
    childTier: str


class OnboardingCreateResponse(BaseModel):
    onboarding_id: int
    child_tier: Literal["tier1", "tier2", "tier3"]


DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)


def initialize_database() -> None:
    # Importing registers session, attention, and mission tables in metadata.
    import storage.memory  # noqa: F401

    SQLModel.metadata.create_all(engine)


def save_onboarding_record(
    record: OnboardingRecord,
    child_tier: str,
) -> OnboardingRecordDB:
    stored_record = OnboardingRecordDB(
        **record.model_dump(),
        childTier=child_tier,
    )
    with Session(engine) as session:
        session.add(stored_record)
        session.commit()
        session.refresh(stored_record)
    return stored_record


def get_onboarding_record(onboarding_id: int) -> OnboardingRecordDB | None:
    with Session(engine) as session:
        return session.get(OnboardingRecordDB, onboarding_id)
