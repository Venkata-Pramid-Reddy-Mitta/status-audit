"""Reconciliation: hold a reported RAG next to a computed RAG and name the gap.

This is the comparison the tool is named for. A reconciliation is not "are these equal". It
is a signed judgement: a report greener than the signals (optimistic) is the finding that
matters, a report redder than the signals (pessimistic) is recorded but harmless, and a
match is the common case. Separating these three is the difference between a tool that
flags noise and one that flags risk.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .config import Policy
from .policy_engine import Verdict, compute_rag
from .rag import Rag, severity_gap
from .signals import Signals


class Direction(StrEnum):
    """Which way a report disagrees with the signals, or that it agrees."""

    OPTIMISTIC = "optimistic"  # reported greener than computed: the dangerous direction
    PESSIMISTIC = "pessimistic"  # reported redder than computed: conservative, not a risk
    CONSISTENT = "consistent"  # reported equals computed


def classify(reported: Rag, computed: Rag) -> Direction:
    """Classify the signed relation between a reported and a computed RAG."""
    if reported < computed:
        return Direction.OPTIMISTIC
    if reported > computed:
        return Direction.PESSIMISTIC
    return Direction.CONSISTENT


@dataclass(frozen=True)
class UnitAudit:
    """The reconciliation of one reporting unit in one week.

    `key` is a tuple that identifies the unit (program and, for a workstream, its id) and
    the week, so the report can point a reader at the exact cell to open.
    """

    program_id: str
    workstream_id: str | None
    week: int
    reported: Rag
    computed: Rag
    direction: Direction
    severity: int
    reasons: tuple[str, ...]

    @property
    def is_blocking(self) -> bool:
        """Optimistic and at least one band severe: the kind the gate counts."""
        return self.direction == Direction.OPTIMISTIC and self.severity >= 1


def reconcile_unit(
    program_id: str,
    workstream_id: str | None,
    week: int,
    reported: Rag,
    signals: Signals,
    policy: Policy,
) -> UnitAudit:
    """Recompute a unit's RAG from its signals and reconcile it with what was reported."""
    verdict: Verdict = compute_rag(signals, policy)
    return UnitAudit(
        program_id=program_id,
        workstream_id=workstream_id,
        week=week,
        reported=reported,
        computed=verdict.rag,
        direction=classify(reported, verdict.rag),
        severity=severity_gap(reported, verdict.rag),
        reasons=verdict.reasons,
    )
