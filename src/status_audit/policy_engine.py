"""The independent judge: signals plus policy produce a RAG and the reasons it fired.

This is the module the whole repository is built to earn trust for. It is a pure function:
the same Signals and the same Policy always give the same Rag, with no clock, no randomness
and no I/O. That purity is what makes the recomputed colour defensible, because an
interviewer can trace any Red back to the exact rule and threshold that produced it.

The engine returns the reasons alongside the colour. A verdict with no reasons is unusable
in a governance setting: the first question in any status meeting is "why", and a tool that
only emits a colour has just reinvented the thing it set out to audit.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import Policy
from .rag import Rag
from .signals import Signals


@dataclass(frozen=True)
class Verdict:
    """A computed RAG with the human-readable reasons each contributing rule fired."""

    rag: Rag
    reasons: tuple[str, ...]

    @property
    def worst_reason(self) -> str:
        """The first reason, which by construction belongs to the most severe band."""
        return self.reasons[0] if self.reasons else "all signals within green thresholds"


def _schedule_band(spi: float, policy: Policy) -> tuple[Rag, str | None]:
    if spi < policy.red_below_spi:
        return Rag.RED, f"SPI {spi:.2f} below red line {policy.red_below_spi:.2f}"
    if spi < policy.amber_below_spi:
        return Rag.AMBER, f"SPI {spi:.2f} below amber line {policy.amber_below_spi:.2f}"
    return Rag.GREEN, None


def _issues_band(open_criticals: int, policy: Policy) -> tuple[Rag, str | None]:
    if open_criticals >= policy.red_at_or_above_criticals:
        return Rag.RED, (
            f"{open_criticals} open criticals at/above red line "
            f"{policy.red_at_or_above_criticals}"
        )
    if open_criticals >= policy.amber_at_or_above_criticals:
        return Rag.AMBER, (
            f"{open_criticals} open criticals at/above amber line "
            f"{policy.amber_at_or_above_criticals}"
        )
    return Rag.GREEN, None


def _milestones_band(overdue: int, policy: Policy) -> tuple[Rag, str | None]:
    if overdue >= policy.red_at_or_above_overdue:
        return Rag.RED, (
            f"{overdue} overdue milestones at/above red line "
            f"{policy.red_at_or_above_overdue}"
        )
    if overdue >= policy.amber_at_or_above_overdue:
        return Rag.AMBER, (
            f"{overdue} overdue milestones at/above amber line "
            f"{policy.amber_at_or_above_overdue}"
        )
    return Rag.GREEN, None


def _cost_band(cpi: float, policy: Policy) -> tuple[Rag, str | None]:
    # Cost tops out at Amber on purpose (see policy.toml [cost]); it never returns Red.
    if cpi < policy.amber_below_cpi:
        return Rag.AMBER, f"CPI {cpi:.2f} below amber line {policy.amber_below_cpi:.2f}"
    return Rag.GREEN, None


def _risks_band(open_high_risks: int, policy: Policy) -> tuple[Rag, str | None]:
    # Risks top out at Amber on purpose: a risk has not happened yet.
    if open_high_risks >= policy.amber_at_or_above_high_risks:
        return Rag.AMBER, (
            f"{open_high_risks} open high risks at/above amber line "
            f"{policy.amber_at_or_above_high_risks}"
        )
    return Rag.GREEN, None


def compute_rag(signals: Signals, policy: Policy) -> Verdict:
    """Compute the objective RAG for one workstream-week as the worst band any rule reaches.

    The combination rule is "worst wins": the unit is as red as its reddest dimension. This
    is the honest rule for delivery risk, because a program that is on budget and on scope
    but badly behind schedule is not Amber on average, it is Red. Averaging the dimensions
    would let a single healthy number dilute a genuine emergency, which is precisely the
    optimism this tool exists to catch.

    Reasons are ordered most-severe first, and only bands that actually raised the colour
    above green are included, so the report never pads a Green verdict with empty rationale.
    """
    bands = [
        _schedule_band(signals.spi, policy),
        _issues_band(signals.open_criticals, policy),
        _milestones_band(signals.overdue_milestones, policy),
        _cost_band(signals.cpi, policy),
        _risks_band(signals.open_high_risks, policy),
    ]
    worst = max(rag for rag, _ in bands)
    if worst == Rag.GREEN:
        return Verdict(rag=Rag.GREEN, reasons=())
    reasons = tuple(
        reason for rag, reason in bands if reason is not None and rag == worst
    ) + tuple(
        reason for rag, reason in bands if reason is not None and rag != worst
    )
    return Verdict(rag=worst, reasons=reasons)
