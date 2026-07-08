from datetime import datetime, timezone

from sqlmodel import Field, SQLModel, UniqueConstraint


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class Match(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    external_id: int = Field(unique=True, index=True)
    competition: str
    season: int
    # For knockout rounds (WC Last 32, Quarter-finals, ...) football-data.org sends
    # matchday=null and a `stage` code instead - see app/stages.py for how those get a
    # synthetic matchday so ordering/tabs still work, plus a human-readable label.
    matchday: int
    stage: str | None = None
    home_team: str
    away_team: str
    kickoff_at: datetime
    status: str
    home_score: int | None = None
    away_score: int | None = None
    scored_at: datetime | None = None


class Prediction(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "match_id"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    match_id: int = Field(foreign_key="match.id")
    pred_home: int
    pred_away: int
    points: int | None = None
    created_at: datetime = Field(default_factory=utc_now)
