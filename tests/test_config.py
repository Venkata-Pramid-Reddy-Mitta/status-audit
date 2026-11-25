"""Policy loading and the validation that refuses an incoherent policy at load time."""

from __future__ import annotations

import textwrap
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from status_audit.config import Policy, PolicyError, load_policy

FULL = """
[schedule]
amber_below_spi = 0.95
red_below_spi = 0.85
[cost]
amber_below_cpi = 0.90
[issues]
amber_at_or_above_criticals = 1
red_at_or_above_criticals = 3
[milestones]
amber_at_or_above_overdue = 1
red_at_or_above_overdue = 2
[risks]
amber_at_or_above_high_risks = 3
[rollup]
rule = "worst_of"
[gate]
min_severity = 1
max_optimistic_allowed = 0
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "policy.toml"
    path.write_text(textwrap.dedent(text))
    return path


def test_the_committed_policy_file_loads(repo_root):
    policy = load_policy(repo_root / "policy.toml")
    assert isinstance(policy, Policy)
    assert policy.rollup_rule == "worst_of"


def test_a_missing_policy_file_raises_policy_error_not_file_not_found(tmp_path):
    with pytest.raises(PolicyError, match="not found"):
        load_policy(tmp_path / "nope.toml")


def test_a_policy_missing_a_section_names_the_section(tmp_path):
    path = _write(tmp_path, FULL.replace("[cost]\namber_below_cpi = 0.90\n", ""))
    with pytest.raises(PolicyError, match=r"\[cost\]"):
        load_policy(path)


def test_a_policy_missing_a_key_names_the_key(tmp_path):
    path = _write(tmp_path, FULL.replace("red_below_spi = 0.85", "# removed"))
    with pytest.raises(PolicyError, match="schedule.red_below_spi"):
        load_policy(path)


def test_an_amber_spi_below_the_red_spi_is_rejected_as_unreachable_red(tmp_path):
    path = _write(tmp_path, FULL.replace("amber_below_spi = 0.95", "amber_below_spi = 0.80"))
    with pytest.raises(PolicyError, match="Red by SPI is unreachable"):
        load_policy(path)


def test_amber_criticals_above_red_criticals_is_rejected(tmp_path):
    path = _write(tmp_path, FULL.replace("amber_at_or_above_criticals = 1",
                                         "amber_at_or_above_criticals = 5"))
    with pytest.raises(PolicyError, match="criticals"):
        load_policy(path)


def test_amber_overdue_above_red_overdue_is_rejected(tmp_path):
    path = _write(tmp_path, FULL.replace("amber_at_or_above_overdue = 1",
                                         "amber_at_or_above_overdue = 9"))
    with pytest.raises(PolicyError, match="overdue"):
        load_policy(path)


def test_an_unknown_rollup_rule_is_rejected(tmp_path):
    path = _write(tmp_path, FULL.replace('rule = "worst_of"', 'rule = "average"'))
    with pytest.raises(PolicyError, match="rollup.rule"):
        load_policy(path)


def test_a_min_severity_below_one_is_rejected(tmp_path):
    path = _write(tmp_path, FULL.replace("min_severity = 1", "min_severity = 0"))
    with pytest.raises(PolicyError, match="min_severity"):
        load_policy(path)


def test_a_negative_optimism_budget_is_rejected(tmp_path):
    path = _write(tmp_path, FULL.replace("max_optimistic_allowed = 0",
                                         "max_optimistic_allowed = -1"))
    with pytest.raises(PolicyError, match="non-negative"):
        load_policy(path)


def test_a_non_numeric_threshold_is_reported_as_a_type_error(tmp_path):
    path = _write(tmp_path, FULL.replace("amber_below_spi = 0.95",
                                         'amber_below_spi = "low"'))
    with pytest.raises(PolicyError):
        load_policy(path)


def test_the_policy_is_frozen_so_a_threshold_cannot_be_mutated(repo_root):
    policy = load_policy(repo_root / "policy.toml")
    with pytest.raises(FrozenInstanceError):
        policy.amber_below_spi = 0.5  # type: ignore[misc]
