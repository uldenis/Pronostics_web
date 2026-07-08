"""Fetch fixtures from football-data.org and upsert them into the DB.

With no --matchday, fetches every matchday for the competition (past results and
upcoming fixtures alike) in a single request. Pass --matchday to refresh just one round.

Run on demand or weekly, e.g.:
    python -m app.jobs.sync_fixtures                       # entire schedule, all configured competitions
    python -m app.jobs.sync_fixtures --competition PL --matchday 5
"""

import argparse
import asyncio
from datetime import datetime

from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.football_data import FootballDataClient
from app.models import Match
from app.stages import resolve_matchday_and_stage


def _parse_kickoff(utc_date: str) -> datetime:
    # football-data returns e.g. "2026-08-15T14:00:00Z"; fromisoformat wants "+00:00".
    return datetime.fromisoformat(utc_date.replace("Z", "+00:00"))


def _upsert_match(session: Session, competition_code: str, raw: dict) -> Match:
    # NOTE: verify these nested field names against a real API response before relying on
    # them long-term (see app/football_data.py docstring / project spec) - they can drift.
    external_id = raw["id"]
    existing = session.exec(select(Match).where(Match.external_id == external_id)).first()

    season_year = int(raw.get("season", {}).get("startDate", "0000")[:4])
    matchday, stage = resolve_matchday_and_stage(raw.get("matchday"), raw.get("stage"))
    # Future knockout fixtures whose matchup isn't decided yet (e.g. "Winner QF1 vs Winner
    # QF2") come back with homeTeam/awayTeam name=null - re-synced later once it's known.
    home_team = raw["homeTeam"].get("name") or "TBD"
    away_team = raw["awayTeam"].get("name") or "TBD"

    if existing is None:
        match = Match(
            external_id=external_id,
            competition=competition_code,
            season=season_year,
            matchday=matchday,
            stage=stage,
            home_team=home_team,
            away_team=away_team,
            kickoff_at=_parse_kickoff(raw["utcDate"]),
            status=raw["status"],
        )
        session.add(match)
        return match

    existing.kickoff_at = _parse_kickoff(raw["utcDate"])
    existing.status = raw["status"]
    existing.matchday = matchday
    existing.stage = stage
    existing.home_team = home_team
    existing.away_team = away_team
    session.add(existing)
    return existing


async def sync_fixtures(competition_code: str, matchday: int | None = None) -> int:
    # matchday=None fetches every matchday for the competition in one request - this is
    # the default, so a plain sync backfills past results and future fixtures alike
    # instead of only ever seeing whatever the API currently considers "current".
    client = FootballDataClient()
    try:
        matches = await client.get_matches(competition_code, matchday=matchday)
    finally:
        await client.aclose()

    with Session(engine) as session:
        for raw in matches:
            _upsert_match(session, competition_code, raw)
        session.commit()

    return len(matches)


async def sync_all_configured_fixtures() -> dict[str, int]:
    results = {}
    for competition in settings.competitions:
        results[competition.code] = await sync_fixtures(competition.code)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--competition",
        default=None,
        help="Competition code (e.g. PL, WC). Omit to sync every competition in settings.competitions.",
    )
    parser.add_argument(
        "--matchday",
        type=int,
        default=None,
        help="Requires --competition. Omit to sync every matchday for the competition.",
    )
    args = parser.parse_args()

    if args.matchday is not None and args.competition is None:
        parser.error("--matchday requires --competition")

    if args.competition:
        count = asyncio.run(sync_fixtures(args.competition, args.matchday))
        print(f"[{args.competition}] synced {count} fixtures.")
    else:
        results = asyncio.run(sync_all_configured_fixtures())
        for code, count in results.items():
            print(f"[{code}] synced {count} fixtures.")
