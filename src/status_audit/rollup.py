"""Rollup integrity: does a program's reported colour follow from its own workstreams?

This check needs no objective signals at all. It asks a narrower question: given the RAG a
program *reported* for itself, and the RAGs its workstreams *reported* for themselves, is
the program colour even internally consistent under a stated rollup rule? A program that
calls itself Green while one of its own workstreams reported Red is contradicting itself on
the same page, before anyone argues about thresholds. Catching that is cheap and damning,
so it is kept separate from the signal reconciliation.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .config import Policy
from .rag import Rag
from .reconcile import Direction, classify


def expected_program_rag(workstream_rags: list[Rag], rule: str) -> Rag:
    """The program RAG implied by its workstreams' reported RAGs under the given rule.

    "worst_of" returns the reddest workstream: a program is no greener than its worst part.
    "majority" returns the most common colour, breaking ties toward the redder one, which is
    the weaker rule a reporter might lean on to keep a single red workstream from colouring
    the whole program. The audit supports both so it can quantify how many contradictions
    survive even the lenient rule.
    """
    if not workstream_rags:
        raise ValueError("a program week has no workstream rows to roll up")
    if rule == "worst_of":
        return max(workstream_rags)
    if rule == "majority":
        counts = Counter(workstream_rags)
        top = max(counts.values())
        tied = [rag for rag, n in counts.items() if n == top]
        return max(tied)  # tie breaks toward the redder colour
    raise ValueError(f"unknown rollup rule: {rule!r}")


@dataclass(frozen=True)
class RollupAudit:
    """One program-week's reported colour against the colour its workstreams imply."""

    program_id: str
    week: int
    reported: Rag
    expected: Rag
    direction: Direction
    rule: str
    workstream_rags: tuple[Rag, ...]

    @property
    def is_violation(self) -> bool:
        """Optimistic rollup: the program called itself greener than its own parts."""
        return self.direction == Direction.OPTIMISTIC


def audit_rollup(
    program_id: str,
    week: int,
    reported_program_rag: Rag,
    reported_workstream_rags: list[Rag],
    policy: Policy,
) -> RollupAudit:
    """Compare a reported program RAG with the rollup of its reported workstream RAGs."""
    expected = expected_program_rag(reported_workstream_rags, policy.rollup_rule)
    return RollupAudit(
        program_id=program_id,
        week=week,
        reported=reported_program_rag,
        expected=expected,
        direction=classify(reported_program_rag, expected),
        rule=policy.rollup_rule,
        workstream_rags=tuple(reported_workstream_rags),
    )
