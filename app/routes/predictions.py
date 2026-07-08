from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.auth import require_user
from app.db import get_session
from app.models import Match, Prediction, User

router = APIRouter()


@router.post("/predictions")
def save_prediction(
    match_id: int = Form(...),
    pred_home: int = Form(...),
    pred_away: int = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_user),
):
    match = session.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    # SQLite has no native tz-aware datetime type, so kickoff_at may come back naive
    # even though it was stored as UTC - treat naive as UTC rather than trusting the client.
    kickoff = match.kickoff_at
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) >= kickoff:
        raise HTTPException(status_code=400, detail="Predictions are locked for this match")

    existing = session.exec(
        select(Prediction).where(
            Prediction.user_id == current_user.id,
            Prediction.match_id == match_id,
        )
    ).first()

    if existing is None:
        existing = Prediction(
            user_id=current_user.id,
            match_id=match_id,
            pred_home=pred_home,
            pred_away=pred_away,
        )
    else:
        existing.pred_home = pred_home
        existing.pred_away = pred_away

    session.add(existing)
    session.commit()

    return RedirectResponse(
        url=f"/predictions?competition={match.competition}&matchday={match.matchday}", status_code=303
    )
