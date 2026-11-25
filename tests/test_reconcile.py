"""Reconciliation: the signed classification of reported against computed."""

from __future__ import annotations

from status_audit.config import Policy
from status_audit.rag import Rag
from status_audit.reconcile import Direction, classify, reconcile_unit
from status_audit.signals import Signals


def test_a_report_greener_than_computed_is_optimistic():
    assert classify(Rag.GREEN, Rag.RED) == Direction.OPTIMISTIC


def test_a_report_redder_than_computed_is_pessimistic():
    assert classify(Rag.RED, Rag.GREEN) == Direction.PESSIMISTIC


def test_a_matching_report_is_consistent():
    assert classify(Rag.AMBER, Rag.AMBER) == Direction.CONSISTENT


def test_reconcile_unit_recomputes_the_colour_and_classifies_it(policy: Policy):
    # Signals that compute Red, reported Green: optimistic with severity 2.
    signals = Signals(spi=0.80, cpi=1.0, open_criticals=0, overdue_milestones=0, open_high_risks=0)
    audit = reconcile_unit("PRG-X", "ws-1", 5, Rag.GREEN, signals, policy)
    assert audit.computed == Rag.RED
    assert audit.reported == Rag.GREEN
    assert audit.direction == Direction.OPTIMISTIC
    assert audit.severity == 2
    assert audit.is_blocking is True


def test_a_consistent_unit_is_not_blocking(policy: Policy):
    signals = Signals(spi=1.0, cpi=1.0, open_criticals=0, overdue_milestones=0, open_high_risks=0)
    audit = reconcile_unit("PRG-X", "ws-1", 5, Rag.GREEN, signals, policy)
    assert audit.direction == Direction.CONSISTENT
    assert audit.is_blocking is False


def test_a_pessimistic_unit_is_not_blocking(policy: Policy):
    # Signals compute Green, reported Red: conservative, recorded, never blocks.
    signals = Signals(spi=1.0, cpi=1.0, open_criticals=0, overdue_milestones=0, open_high_risks=0)
    audit = reconcile_unit("PRG-X", "ws-1", 5, Rag.RED, signals, policy)
    assert audit.direction == Direction.PESSIMISTIC
    assert audit.is_blocking is False


def test_the_reasons_travel_from_the_verdict_onto_the_unit_audit(policy: Policy):
    signals = Signals(spi=0.80, cpi=1.0, open_criticals=0, overdue_milestones=0, open_high_risks=0)
    audit = reconcile_unit("PRG-X", "ws-1", 5, Rag.GREEN, signals, policy)
    assert any("SPI" in r for r in audit.reasons)
