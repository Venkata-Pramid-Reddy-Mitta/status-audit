"""The objective signals for one reporting unit in one week, and how they are validated.

A "signal" here is a number that is produced by the delivery system rather than typed as a
judgement: SPI and CPI come out of earned-value tracking, the counts come out of the issue
and milestone trackers. The reported RAG is the judgement. Keeping the signals in their own
small, validated object is what lets the engine stay a pure function of them, which in turn
is what makes every recomputed colour reproducible from the committed CSV.
"""

from __future__ import annotations

from dataclasses import dataclass


class SignalError(ValueError):
    """Raised when a signal value is outside the range the engine can reason about."""


@dataclass(frozen=True)
class Signals:
    """Objective signals for a single workstream-week.

    Frozen and validated at construction. The validation is not decoration: an SPI of -1 or
    a negative issue count is almost always a data-entry or join error upstream, and letting
    it through would produce a confident, wrong recomputed RAG, which is the one failure this
    repository must never commit.
    """

    spi: float
    cpi: float
    open_criticals: int
    overdue_milestones: int
    open_high_risks: int

    def __post_init__(self) -> None:
        if self.spi < 0:
            raise SignalError(f"spi must be non-negative, got {self.spi}")
        if self.cpi < 0:
            raise SignalError(f"cpi must be non-negative, got {self.cpi}")
        for name in ("open_criticals", "overdue_milestones", "open_high_risks"):
            value = getattr(self, name)
            if value < 0:
                raise SignalError(f"{name} must be non-negative, got {value}")


SIGNAL_COLUMNS = ("spi", "cpi", "open_criticals", "overdue_milestones", "open_high_risks")


def signals_from_row(row: dict) -> Signals:
    """Build Signals from a CSV-derived mapping, coercing the numeric types explicitly.

    pandas hands back numpy scalar types; coercing to plain float/int here keeps the rest of
    the code (and the JSON report) free of numpy types, which otherwise leak out and break
    json.dumps in a way that only shows up at report time.
    """
    try:
        return Signals(
            spi=float(row["spi"]),
            cpi=float(row["cpi"]),
            open_criticals=int(row["open_criticals"]),
            overdue_milestones=int(row["overdue_milestones"]),
            open_high_risks=int(row["open_high_risks"]),
        )
    except KeyError as exc:
        raise SignalError(f"row is missing a signal column: {exc}") from exc
