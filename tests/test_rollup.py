"""Rollup integrity: the program colour implied by its workstreams, and violations."""

from __future__ import annotations

import pytest

from status_audit.config import Policy
from status_audit.rag import Rag
from status_audit.reconcile import Direction
from status_audit.rollup import audit_rollup, expected_program_rag


def test_worst_of_returns_the_reddest_workstream():
    assert expected_program_rag([Rag.GREEN, Rag.AMBER, Rag.RED], "worst_of") == Rag.RED


def test_worst_of_of_all_green_is_green():
    assert expected_program_rag([Rag.GREEN, Rag.GREEN], "worst_of") == Rag.GREEN


def test_majority_returns_the_most_common_colour():
    assert expected_program_rag([Rag.GREEN, Rag.GREEN, Rag.RED], "majority") == Rag.GREEN


def test_majority_breaks_a_tie_toward_the_redder_colour():
    assert expected_program_rag([Rag.GREEN, Rag.RED], "majority") == Rag.RED


def test_majority_is_never_redder_than_worst_of():
    rags = [Rag.GREEN, Rag.GREEN, Rag.AMBER, Rag.RED]
    assert expected_program_rag(rags, "majority") <= expected_program_rag(rags, "worst_of")


def test_an_empty_workstream_list_raises():
    with pytest.raises(ValueError, match="no workstream rows"):
        expected_program_rag([], "worst_of")


def test_an_unknown_rule_raises():
    with pytest.raises(ValueError, match="unknown rollup rule"):
        expected_program_rag([Rag.GREEN], "average")


def test_a_program_greener_than_its_worst_workstream_is_a_violation(policy: Policy):
    audit = audit_rollup("PRG-X", 7, Rag.GREEN, [Rag.GREEN, Rag.RED, Rag.AMBER], policy)
    assert audit.expected == Rag.RED
    assert audit.direction == Direction.OPTIMISTIC
    assert audit.is_violation is True


def test_a_program_matching_its_worst_workstream_is_not_a_violation(policy: Policy):
    audit = audit_rollup("PRG-X", 7, Rag.RED, [Rag.GREEN, Rag.RED], policy)
    assert audit.is_violation is False


def test_a_program_redder_than_its_workstreams_is_not_a_violation(policy: Policy):
    audit = audit_rollup("PRG-X", 7, Rag.RED, [Rag.GREEN, Rag.GREEN], policy)
    assert audit.direction == Direction.PESSIMISTIC
    assert audit.is_violation is False
