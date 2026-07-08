from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, func, select

from app.auth import get_current_user, require_user
from app.config import settings
from app.db import get_session
from app.models import Match, Prediction, User
from app.stages import matchday_label
from app.templating import templates

router = APIRouter()


def _resolve_competition(code: str | None) -> str:
    codes = [c.code for c in settings.competitions]
    if code in codes:
        return code
    return codes[0]


def _resolve_matchday(matchday: int | None, available: list[int]) -> int | None:
    if not available:
        return None
    if matchday in available:
        return matchday
    return available[0]  # available is sorted latest-first


@router.get("/predictions")
def list_matches(
    request: Request,
    competition: str | None = None,
    matchday: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_user),
):
    selected_code = _resolve_competition(competition)

    # Latest matchday first, per the user's request - lets you land on the most recent
    # results by default and browse back through earlier rounds. Knockout rounds carry a
    # `stage` (e.g. "QUARTER_FINALS") instead of a real matchday number - see app/stages.py.
    matchday_stage_rows = session.exec(
        select(Match.matchday, Match.stage)
        .where(Match.competition == selected_code)
        .distinct()
        .order_by(Match.matchday.desc())
    ).all()
    available_matchdays = [md for md, _ in matchday_stage_rows]
    matchday_tabs = [
        {"matchday": md, "label": matchday_label(md, stage)} for md, stage in matchday_stage_rows
    ]

    selected_matchday = _resolve_matchday(matchday, available_matchdays)
    selected_stage = next(
        (stage for md, stage in matchday_stage_rows if md == selected_matchday), None
    )

    matches = []
    if selected_matchday is not None:
        matches = session.exec(
            select(Match)
            .where(Match.competition == selected_code, Match.matchday == selected_matchday)
            .order_by(Match.kickoff_at)
        ).all()

    existing_predictions = {
        p.match_id: p
        for p in session.exec(
            select(Prediction).where(Prediction.user_id == current_user.id)
        ).all()
    }

    return templates.TemplateResponse(
        request,
        "matches.html",
        {
            "user": current_user,
            "competitions": settings.competitions,
            "selected_code": selected_code,
            "matchday_tabs": matchday_tabs,
            "selected_matchday": selected_matchday,
            "selected_matchday_label": matchday_label(selected_matchday, selected_stage)
            if selected_matchday is not None
            else None,
            "matches": matches,
            "predictions": existing_predictions,
            # kickoff_at comes back tz-naive from SQLite (stored as UTC), so compare naive-to-naive.
            "now": datetime.now(timezone.utc).replace(tzinfo=None),
        },
    )


@router.get("/leaderboard")
def leaderboard(
    request: Request,
    competition: str | None = None,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    selected_code = _resolve_competition(competition)

    rows = session.exec(
        select(User.id, User.name, func.sum(Prediction.points))
        .join(Prediction, Prediction.user_id == User.id)
        .join(Match, Match.id == Prediction.match_id)
        .where(Prediction.points.is_not(None), Match.competition == selected_code)
        .group_by(User.id)
        .order_by(func.sum(Prediction.points).desc())
    ).all()

    return templates.TemplateResponse(
        request,
        "leaderboard.html",
        {
            "user": current_user,
            "competitions": settings.competitions,
            "selected_code": selected_code,
            "rows": rows,
        },
    )
