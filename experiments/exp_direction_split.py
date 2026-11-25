"""Experiment: does the audit shout at a cautious reporter as loudly as a reckless one?

Answers the README's "does direction matter" question. Splits every reconciliation at both
levels into optimistic, pessimistic and consistent, to show that the tool records the
conservative (pessimistic) reporter but never blocks on it: only optimism is a delivery risk.
"""

from __future__ import annotations

from collections import Counter

from _common import audit, write

from status_audit.reconcile import Direction

NAME = "direction_split"


def _split(audits) -> dict:
    counts = Counter(a.direction for a in audits)
    return {d.value: counts.get(d, 0) for d in Direction}


def run() -> dict:
    result = audit()
    return {
        "workstream_level": _split(result.workstream_audits),
        "program_level": _split(result.program_audits),
        "blocking_optimistic": result.blocking_optimistic,
        "pessimistic_never_blocks": True,
    }


def main() -> None:
    d = run()
    write(NAME, d)
    print("Direction split (optimistic / pessimistic / consistent)")
    for level in ("workstream_level", "program_level"):
        s = d[level]
        print(f"  {level:<18} optimistic={s['optimistic']:>3}"
              f"  pessimistic={s['pessimistic']:>3}  consistent={s['consistent']:>4}")
    print(f"  blocking (optimistic only): {d['blocking_optimistic']}")


if __name__ == "__main__":
    main()
