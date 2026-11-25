"""Confession lag: how long a program stayed green on paper after its signals turned.

The single reconciliation of one week answers "is this week's colour honest". It cannot
answer the question a sponsor actually cares about, which is temporal: once the signals
started saying Amber, how many weeks passed before the report finally admitted it. That lag
is where the money is lost, because every week of optimistic reporting is a week nobody
escalated. Computing it needs the whole time series for a program, not a single week, which
is why it lives apart from reconcile.py.

Boundary (see README "What this cannot measure"): this measures the *first* deterioration
episode per program, from the first objectively non-green week to the first reported
non-green week. A program that recovers and relapses has a second episode this function does
not score. Episode detection is the Pivot, with its trigger stated in the README.
"""

from __future__ import annotations

from dataclasses import dataclass

from .rag import Rag


@dataclass(frozen=True)
class ConfessionResult:
    """The confession lag for one program's first deterioration episode.

    `objective_onset_week` is the first week the signals said Amber or worse.
    `reported_onset_week` is the first week the report said Amber or worse.
    `lag_weeks` is their difference when the report lagged the signals, else 0.
    `never_confessed` is True when the signals deteriorated but the report stayed Green for
    the rest of the horizon, which is the strongest possible finding: no confession at all.
    """

    program_id: str
    objective_onset_week: int | None
    reported_onset_week: int | None
    lag_weeks: int
    never_confessed: bool

    @property
    def is_optimistic_episode(self) -> bool:
        """True when the signals turned before (or without) the report admitting it."""
        return self.lag_weeks > 0 or self.never_confessed


def _first_non_green(weeks: list[int], rags: list[Rag]) -> int | None:
    for week, rag in zip(weeks, rags, strict=True):
        if rag != Rag.GREEN:
            return week
    return None


def confession_lag(
    program_id: str,
    weeks: list[int],
    objective: list[Rag],
    reported: list[Rag],
) -> ConfessionResult:
    """Compute the first-episode confession lag for one program.

    The three lists are parallel and must be the same length and ordered by week; a mismatch
    raises, because a silently misaligned join here would invent a lag that never happened.
    """
    if not (len(weeks) == len(objective) == len(reported)):
        raise ValueError("weeks, objective and reported must be the same length")
    if weeks != sorted(weeks):
        raise ValueError("weeks must be sorted ascending")

    objective_onset = _first_non_green(weeks, objective)
    reported_onset = _first_non_green(weeks, reported)

    if objective_onset is None:
        # The signals never left green, so there is nothing to confess.
        return ConfessionResult(program_id, None, reported_onset, 0, False)

    if reported_onset is None:
        # The signals deteriorated but the report stayed green for the whole horizon.
        return ConfessionResult(program_id, objective_onset, None, 0, True)

    if reported_onset <= objective_onset:
        # The report turned at or before the signals: honest or pessimistic, lag is zero.
        return ConfessionResult(program_id, objective_onset, reported_onset, 0, False)

    return ConfessionResult(
        program_id=program_id,
        objective_onset_week=objective_onset,
        reported_onset_week=reported_onset,
        lag_weeks=reported_onset - objective_onset,
        never_confessed=False,
    )
