"""Threshold sensitivity: price the audit's own biggest assumption.

The audit's output is "the report disagrees with this policy", so the honest question a
reviewer asks is "how much of your headline is the policy rather than the program". This
module answers it by re-running the whole audit across a grid of the single most load-bearing
threshold (the amber SPI line) and reporting how the headline count moves. A finding that
survives a wide sweep is robust; one that collapses when the line shifts by 0.05 is really a
statement about the threshold, and this module is what forces that admission into the open.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .audit import run_audit
from .config import Policy
from .loader import StatusData


@dataclass(frozen=True)
class SensitivityPoint:
    """The headline counts at one value of the amber SPI threshold."""

    amber_below_spi: float
    green_over_trouble_program_weeks: int
    optimistic_program_weeks: int


def sweep_amber_spi(
    data: StatusData, policy: Policy, thresholds: list[float]
) -> list[SensitivityPoint]:
    """Recompute the headline counts for each amber SPI threshold in the grid.

    Each threshold must stay at or above the policy's red line, since an amber line below the
    red line is incoherent (ADR validation forbids it); such values are skipped rather than
    raising, so a caller can hand in a symmetric grid without pre-filtering.
    """
    points: list[SensitivityPoint] = []
    for threshold in thresholds:
        if threshold < policy.red_below_spi:
            continue
        perturbed = replace(policy, amber_below_spi=threshold)
        result = run_audit(data, perturbed)
        points.append(
            SensitivityPoint(
                amber_below_spi=threshold,
                green_over_trouble_program_weeks=result.green_over_trouble_program_weeks,
                optimistic_program_weeks=result.optimistic_program_weeks,
            )
        )
    return points
