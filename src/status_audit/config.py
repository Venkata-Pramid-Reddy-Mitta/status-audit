"""The policy, loaded from TOML into a frozen object the engine can trust.

The thresholds live in policy.toml, not in the code, for one concrete reason: the audit's
whole output is "the report disagrees with this policy", so a reviewer has to be able to
read, challenge and change the policy without reading Python. Keeping the numbers in a
commented TOML file is what lets the sensitivity experiment perturb one threshold and
re-run, and what lets an interviewer argue with a line of config instead of a function.

This module only loads and validates. It holds no thresholds of its own: a default buried
here would silently override the file, which is the bug this separation prevents.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

ROLLUP_RULES = ("worst_of", "majority")


class PolicyError(ValueError):
    """Raised when a policy file is missing a field or carries an impossible value.

    This is a distinct type so the CLI can map a bad policy to its own exit code and a
    reviewer can tell "your config is wrong" apart from "your data is wrong".
    """


@dataclass(frozen=True)
class Policy:
    """Every threshold the engine needs, validated once at load time.

    Frozen so that no part of the pipeline can nudge a threshold mid-run: a moving policy
    would make the recomputed RAG depend on evaluation order, which would quietly destroy
    the determinism the receipts depend on.
    """

    amber_below_spi: float
    red_below_spi: float
    amber_below_cpi: float
    amber_at_or_above_criticals: int
    red_at_or_above_criticals: int
    amber_at_or_above_overdue: int
    red_at_or_above_overdue: int
    amber_at_or_above_high_risks: int
    rollup_rule: str
    min_severity: int
    max_optimistic_allowed: int

    def __post_init__(self) -> None:
        # The ordering checks below are not defensive padding: an amber line set below the
        # red line would make RED unreachable by SPI and the engine would silently never
        # fire it, which is the single most expensive way to get a wrong answer here.
        if not (self.red_below_spi <= self.amber_below_spi):
            raise PolicyError(
                "red_below_spi must be <= amber_below_spi, else Red by SPI is unreachable"
            )
        if not (self.amber_at_or_above_criticals <= self.red_at_or_above_criticals):
            raise PolicyError(
                "amber_at_or_above_criticals must be <= red_at_or_above_criticals"
            )
        if not (self.amber_at_or_above_overdue <= self.red_at_or_above_overdue):
            raise PolicyError(
                "amber_at_or_above_overdue must be <= red_at_or_above_overdue"
            )
        if self.rollup_rule not in ROLLUP_RULES:
            raise PolicyError(
                f"rollup.rule must be one of {ROLLUP_RULES}, got {self.rollup_rule!r}"
            )
        if self.min_severity < 1:
            raise PolicyError("gate.min_severity must be at least 1")
        if self.max_optimistic_allowed < 0:
            raise PolicyError("gate.max_optimistic_allowed must be non-negative")


def _require(table: dict, section: str, key: str) -> object:
    """Fetch policy[section][key] or raise a PolicyError naming exactly what is missing."""
    if section not in table:
        raise PolicyError(f"policy is missing the [{section}] section")
    if key not in table[section]:
        raise PolicyError(f"policy is missing {section}.{key}")
    return table[section][key]


def load_policy(path: str | Path) -> Policy:
    """Read a policy TOML file into a validated Policy, or raise PolicyError.

    A missing file raises PolicyError rather than FileNotFoundError so the CLI has a single
    policy-shaped failure to catch, and so the message points at the policy rather than at
    a stack trace.
    """
    path = Path(path)
    if not path.exists():
        raise PolicyError(f"policy file not found: {path}")
    with path.open("rb") as handle:
        table = tomllib.load(handle)
    try:
        return Policy(
            amber_below_spi=float(_require(table, "schedule", "amber_below_spi")),
            red_below_spi=float(_require(table, "schedule", "red_below_spi")),
            amber_below_cpi=float(_require(table, "cost", "amber_below_cpi")),
            amber_at_or_above_criticals=int(
                _require(table, "issues", "amber_at_or_above_criticals")
            ),
            red_at_or_above_criticals=int(
                _require(table, "issues", "red_at_or_above_criticals")
            ),
            amber_at_or_above_overdue=int(
                _require(table, "milestones", "amber_at_or_above_overdue")
            ),
            red_at_or_above_overdue=int(
                _require(table, "milestones", "red_at_or_above_overdue")
            ),
            amber_at_or_above_high_risks=int(
                _require(table, "risks", "amber_at_or_above_high_risks")
            ),
            rollup_rule=str(_require(table, "rollup", "rule")),
            min_severity=int(_require(table, "gate", "min_severity")),
            max_optimistic_allowed=int(_require(table, "gate", "max_optimistic_allowed")),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, PolicyError):
            raise
        raise PolicyError(f"policy value has the wrong type: {exc}") from exc
