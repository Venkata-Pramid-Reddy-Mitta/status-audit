"""The RAG scale as an ordered thing, which is the only reason reconciliation is possible.

Green, Amber and Red are usually treated as labels. The entire tool depends on treating
them as an *ordered* scale instead (Green < Amber < Red), because the question that
matters is not "do the two colours differ" but "is the reported colour greener than the
computed one". A plain equality check would flag a report that is too pessimistic exactly
as loudly as one that is dangerously optimistic, and those are not the same finding. So
RAG carries an integer severity and all comparisons go through it.
"""

from __future__ import annotations

from enum import IntEnum


class Rag(IntEnum):
    """Red/Amber/Green as an ordinal scale. The integer value is the severity.

    Ordering is deliberate: GREEN is the least severe (0) and RED the most (2). Because
    this is an IntEnum, `reported < computed` reads as "the report was greener than the
    signals justify", which is the central relation of the audit.
    """

    GREEN = 0
    AMBER = 1
    RED = 2

    @property
    def letter(self) -> str:
        """Single-letter form (G/A/R) used in compact tables and CSV fixtures."""
        return self.name[0]

    def __str__(self) -> str:
        return self.name.capitalize()


_BY_TEXT = {
    "g": Rag.GREEN,
    "green": Rag.GREEN,
    "a": Rag.AMBER,
    "amber": Rag.AMBER,
    "y": Rag.AMBER,
    "yellow": Rag.AMBER,
    "r": Rag.RED,
    "red": Rag.RED,
}


def parse_rag(value: object) -> Rag:
    """Parse a RAG from a report cell, tolerating the forms a real export contains.

    Status exports are typed by humans into spreadsheets, so the same colour arrives as
    "Green", "G", "green ", or "YELLOW". A reconciliation tool that rejects "G" is useless
    on real data, so parsing is lenient on spelling and case but strict on meaning: an
    unrecognised token raises rather than being silently bucketed, because a quietly
    mis-parsed status is exactly the kind of error this repository is supposed to catch.
    """
    if isinstance(value, Rag):
        return value
    text = str(value).strip().lower()
    if text not in _BY_TEXT:
        raise ValueError(f"not a recognisable RAG status: {value!r}")
    return _BY_TEXT[text]


def is_optimistic(reported: Rag, computed: Rag) -> bool:
    """True when the report is greener than the signals justify (the dangerous direction)."""
    return reported < computed


def severity_gap(reported: Rag, computed: Rag) -> int:
    """Size of the disagreement as a non-negative integer (0 when they agree)."""
    return abs(int(reported) - int(computed))
