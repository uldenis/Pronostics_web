from app.scoring import (
    POINTS_CORRECT_DIFF,
    POINTS_CORRECT_RESULT,
    POINTS_EXACT,
    POINTS_WRONG,
    score,
)


def test_exact_score():
    assert score(3, 1, 3, 1) == POINTS_EXACT


def test_correct_result_and_diff_not_exact():
    assert score(2, 1, 3, 2) == POINTS_CORRECT_DIFF


def test_correct_result_only():
    assert score(1, 0, 3, 1) == POINTS_CORRECT_RESULT


def test_wrong_result():
    assert score(2, 0, 1, 2) == POINTS_WRONG


def test_correct_but_inexact_draw():
    # Open design decision (see scoring.py): predicted 1-1, actual 2-2 share goal
    # difference 0, so under the current rules this lands in POINTS_CORRECT_DIFF.
    # If draws should be gated to POINTS_CORRECT_RESULT instead, update this assertion
    # and the gate in `score()` together.
    assert score(1, 1, 2, 2) == POINTS_CORRECT_DIFF


def test_away_win_correct_diff():
    assert score(0, 2, 1, 3) == POINTS_CORRECT_DIFF
