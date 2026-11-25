"""Confession lag: how long a program stayed green on paper after its signals turned.

The single reconciliation of one week answers "is this week's colour honest". It cannot
answer the question a sponsor actually cares about, which is temporal: once the signals
started saying Amber, how many weeks passed before the report finally admitted it. That lag
is where the money is lost, because every week of optimistic reporting is a week nobody
escalated. Computing it needs the whole time series for a program, not a single week, which
is why it lives apart from reconcile.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from .rag import Rag


@dataclass(frozen=True)
class ConfessionResult:
    """The confession lag for one program's first deterioration episode."""

    program_id: str
    objective_onset_week: int | None
    reported_onset_week: int | None
    lag_weeks: int
    never_confessed: bool

    @property
    def is_optimistic_episode(self) -> bool:
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
    """Compute the first-episode confession lag for one program."""
    if not (len(weeks) == len(objective) == len(reported)):
        raise ValueError("weeks, objective and reported must be the same length")
    if weeks != sorted(weeks):
        raise ValueError("weeks must be sorted ascending")

    objective_onset = _first_non_green(weeks, objective)
    reported_onset = _first_non_green(weeks, reported)

    if objective_onset is None:
        return ConfessionResult(program_id, None, reported_onset, 0, False)

    if reported_onset is None:
        return ConfessionResult(program_id, objective_onset, None, 0, True)

    # The gap between when the signals turned and when the report turned.
    lag = abs(reported_onset - objective_onset)
    return ConfessionResult(
        program_id=program_id,
        objective_onset_week=objective_onset,
        reported_onset_week=reported_onset,
        lag_weeks=lag,
        never_confessed=False,
    )
