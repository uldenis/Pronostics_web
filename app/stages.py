"""Maps football-data.org knockout `stage` codes to display labels and synthetic
matchday numbers. Knockout fixtures (Last 32, Quarter-finals, ...) come back with
matchday=null from the API - group/league rounds always have a real integer matchday.
"""

KNOCKOUT_STAGE_ORDER = [
    "LAST_64",
    "LAST_32",
    "LAST_16",
    "QUARTER_FINALS",
    "SEMI_FINALS",
    "THIRD_PLACE",
    "FINAL",
]

STAGE_LABELS = {
    "LAST_64": "Round of 64",
    "LAST_32": "Round of 32",
    "LAST_16": "Round of 16",
    "QUARTER_FINALS": "Quarter-finals",
    "SEMI_FINALS": "Semi-finals",
    "THIRD_PLACE": "Third-place playoff",
    "FINAL": "Final",
}

# Comfortably above any realistic league/group-stage matchday count, so knockout
# rounds always sort after them.
_SYNTHETIC_MATCHDAY_BASE = 100


def resolve_matchday_and_stage(raw_matchday: int | None, raw_stage: str | None) -> tuple[int, str | None]:
    if raw_matchday is not None:
        return raw_matchday, None

    if raw_stage in KNOCKOUT_STAGE_ORDER:
        return _SYNTHETIC_MATCHDAY_BASE + KNOCKOUT_STAGE_ORDER.index(raw_stage), raw_stage

    # Unexpected: no matchday and an unrecognized stage. Don't crash the sync over it -
    # bucket it under matchday 0 with the raw stage code as the label.
    return 0, raw_stage


def matchday_label(matchday: int, stage: str | None) -> str:
    if stage:
        return STAGE_LABELS.get(stage, stage)
    return f"MD {matchday}"
