"""Experiment: do the rollup contradictions survive the lenient rule a reporter would prefer?

Answers the README's "is this just a strict rollup rule" question. Counts rollup integrity
violations under worst_of (the strict rule the policy ships with) and under majority (the
weaker rule a reporter might lean on), to show how many contradictions are robust to the
choice of rule rather than artefacts of it.
"""

from __future__ import annotations

from dataclasses import replace

from _common import load, write

from status_audit.audit import run_audit

NAME = "rollup_rule"


def run() -> dict:
    data, policy = load()
    worst = run_audit(data, replace(policy, rollup_rule="worst_of"))
    majority = run_audit(data, replace(policy, rollup_rule="majority"))
    return {
        "violations_worst_of": worst.rollup_violations,
        "violations_majority": majority.rollup_violations,
        "survive_majority_fraction": round(
            majority.rollup_violations / worst.rollup_violations, 3
        )
        if worst.rollup_violations
        else 0.0,
    }


def main() -> None:
    d = run()
    write(NAME, d)
    print("Rollup integrity violations by rule")
    print(f"  worst_of (strict):  {d['violations_worst_of']}")
    print(f"  majority (lenient): {d['violations_majority']}")
    print(f"  fraction surviving the lenient rule: {d['survive_majority_fraction']}")


if __name__ == "__main__":
    main()
