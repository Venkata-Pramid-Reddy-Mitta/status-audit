"""Confession lag: the temporal gap between the signals turning and the report admitting it.

The bug-pinning test lives here. See test_confession_lag_is_zero_when_the_report_leads_the
_signals and its docstring: an early version measured abs(reported - objective), which
reported a 6-week "lag" for a program that was being conservative, exactly inverting the
finding.
"""

from __future__ import annotations

import pytest

from status_audit.confession import confession_lag
from status_audit.rag import Rag

G, A, R = Rag.GREEN, Rag.AMBER, Rag.RED


def test_a_program_that_reports_green_while_signals_are_red_has_lag():
    weeks = [1, 2, 3, 4, 5]
    objective = [G, A, A, R, R]
    reported = [G, G, G, A, A]
    result = confession_lag("PRG-X", weeks, objective, reported)
    assert result.objective_onset_week == 2
    assert result.reported_onset_week == 4
    assert result.lag_weeks == 2
    assert result.never_confessed is False
    assert result.is_optimistic_episode is True


def test_a_program_whose_signals_never_leave_green_has_nothing_to_confess():
    result = confession_lag("PRG-X", [1, 2, 3], [G, G, G], [G, G, G])
    assert result.objective_onset_week is None
    assert result.lag_weeks == 0
    assert result.is_optimistic_episode is False


def test_a_program_that_never_confesses_is_flagged_as_such():
    result = confession_lag("PRG-X", [1, 2, 3], [G, R, R], [G, G, G])
    assert result.never_confessed is True
    assert result.reported_onset_week is None
    assert result.is_optimistic_episode is True


def test_confession_lag_is_zero_when_the_report_leads_the_signals():
    """Pins the inverted-sign bug.

    A sandbagging program reports Amber from week 1 while its signals stay green until week
    6. An early version computed abs(reported_onset - objective_onset) and reported a 5-week
    lag, flagging a conservative reporter as the worst offender. Lag must be zero (or the
    episode non-optimistic) when the report turns at or before the signals.
    """
    weeks = [1, 2, 3, 4, 5, 6, 7]
    objective = [G, G, G, G, G, A, A]
    reported = [A, A, A, A, A, A, A]
    result = confession_lag("PRG-X", weeks, objective, reported)
    assert result.lag_weeks == 0
    assert result.is_optimistic_episode is False


def test_a_report_that_turns_the_same_week_as_the_signals_has_zero_lag():
    result = confession_lag("PRG-X", [1, 2, 3], [G, A, R], [G, A, R])
    assert result.lag_weeks == 0
    assert result.never_confessed is False


def test_mismatched_series_lengths_raise():
    with pytest.raises(ValueError, match="same length"):
        confession_lag("PRG-X", [1, 2], [G], [G, A])


def test_unsorted_weeks_raise():
    with pytest.raises(ValueError, match="sorted"):
        confession_lag("PRG-X", [2, 1], [G, A], [G, A])
