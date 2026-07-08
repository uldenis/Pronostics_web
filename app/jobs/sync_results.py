"""Fetch finished results from football-data.org, update matches, and score every
finished-but-unscored match's predictions. Safe to re-run: the `scored_at` guard means
already-scored matches are never rescored (see app/models.py::Match.scored_at).

Run every 15-30 min during match windows, e.g.:
    python -m app.jobs.sync_results                  # all configured competitions
    python -m app.jobs.sync_results --competition WC
"""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.football_data import FootballDataClient
from app.models import Match, Prediction, utc_now
from app.scoring import score


def _default_window() -> tuple[str, str]:
    today = datetime.now(timezone.utc).date()
    return (today - timedelta(days=7)).isoformat(), today.isoformat()


def _update_result(session: Session, raw: dict) -> None:
    match = session.exec(select(Match).where(Match.external_id == raw["id"])).first()
    if match is None:
        # Fixture was never synced (e.g. sync_fixtures hasn't run for this matchday yet).
        return

    match.status = raw["status"]
    full_time = raw.get("score", {}).get("fullTime", {})
    match.home_score = full_time.get("home")
    match.away_score = full_time.get("away")
    session.add(match)


def _score_finished_matches(session: Session) -> int:
    # Competition-agnostic on purpose: scores whatever is FINISHED and unscored,
    # regardless of which competition it came from.
    unscored = session.exec(
        select(Match).where(Match.status == "FINISHED", Match.scored_at.is_(None))
    ).all()

    scored_count = 0
    for match in unscored:
        if match.home_score is None or match.away_score is None:
            continue  # marked FINISHED but no score yet; try again next run

        predictions = session.exec(
            select(Prediction).where(Prediction.match_id == match.id)
        ).all()
        for prediction in predictions:
            prediction.points = score(
                prediction.pred_home, prediction.pred_away, match.home_score, match.away_score
            )
            session.add(prediction)

        match.scored_at = utc_now()
        session.add(match)
        scored_count += 1

    return scored_count


async def sync_results(
    competition_codes: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> int:
    if date_from is None or date_to is None:
        date_from, date_to = _default_window()
    if competition_codes is None:
        competition_codes = [c.code for c in settings.competitions]

    client = FootballDataClient()
    try:
        with Session(engine) as session:
            for code in competition_codes:
                matches = await client.get_matches(
                    code, status="FINISHED", date_from=date_from, date_to=date_to
                )
                for raw in matches:
                    _update_result(session, raw)
            session.commit()

            scored_count = _score_finished_matches(session)
            session.commit()
    finally:
        await client.aclose()

    return scored_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--competition",
        default=None,
        help="Competition code (e.g. PL, WC). Omit to sync every competition in settings.competitions.",
    )
    args = parser.parse_args()

    codes = [args.competition] if args.competition else None
    count = asyncio.run(sync_results(codes))
    print(f"Scored {count} newly finished matches.")
