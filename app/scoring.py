"""Pure scoring logic. No I/O, no DB, no framework imports — keep it that way so it stays
trivially unit-testable.
"""

POINTS_EXACT = 3
POINTS_CORRECT_DIFF = 2
POINTS_CORRECT_RESULT = 1
POINTS_WRONG = 0


def _result(home: int, away: int) -> str:
    if home > away:
        return "home"
    if home < away:
        return "away"
    return "draw"


def score(pred_home: int, pred_away: int, actual_home: int, actual_away: int) -> int:
    if pred_home == actual_home and pred_away == actual_away:
        return POINTS_EXACT

    pred_result = _result(pred_home, pred_away)
    actual_result = _result(actual_home, actual_away)
    if pred_result != actual_result:
        return POINTS_WRONG

    # Decision: a correct-but-inexact draw (e.g. predicted 1-1, actual 2-2) has the same
    # goal difference (0) as the actual result, so it currently scores in the
    # POINTS_CORRECT_DIFF tier like any other correct-diff prediction. If that should
    # instead be worth only POINTS_CORRECT_RESULT, gate on `pred_result != "draw"` below —
    # see test_correct_but_inexact_draw for the case this affects.
    pred_diff = pred_home - pred_away
    actual_diff = actual_home - actual_away
    if pred_diff == actual_diff:
        return POINTS_CORRECT_DIFF

    return POINTS_CORRECT_RESULT
