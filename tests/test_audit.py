"""The orchestrated audit over the committed data, including the pinned headline numbers.

These assertions double as a lock on the fixture: if the generator or the engine changes the
headline, this file fails before the README can go stale.
"""

from __future__ import annotations

from status_audit.audit import run_audit
from status_audit.rag import Rag
from status_audit.reconcile import Direction


def test_every_reported_cell_is_reconciled(audit_result):
    assert len(audit_result.workstream_audits) == 468
    assert len(audit_result.program_audits) == 156
    assert audit_result.total_reports == 624


def test_the_headline_count_of_green_over_trouble_program_weeks(audit_result):
    assert audit_result.green_over_trouble_program_weeks == 26


def test_all_optimistic_program_weeks_are_green_over_trouble(audit_result):
    # On this portfolio every optimistic program-week is a green report over amber/red signals.
    assert audit_result.optimistic_program_weeks == 26


def test_no_workstream_week_is_optimistic(audit_result):
    # The distortion lives at the program rollup, not in the workstream leads' own reports.
    assert audit_result.optimistic_workstream_weeks == 0


def test_the_rollup_integrity_violation_count(audit_result):
    assert audit_result.rollup_violations == 48


def test_exactly_one_program_never_confessed(audit_result):
    assert audit_result.programs_never_confessed == 1
    never = [c.program_id for c in audit_result.confessions if c.never_confessed]
    assert never == ["PRG-CEDAR"]


def test_the_confession_lags_present_in_the_portfolio(audit_result):
    assert audit_result.confession_lags == [2, 4]
    assert audit_result.max_confession_lag == 4


def test_the_gate_fails_on_the_committed_data(audit_result):
    assert audit_result.blocking_optimistic == 26
    assert audit_result.gate_passed() is False


def test_the_sandbagger_is_recorded_as_pessimistic_not_optimistic(audit_result):
    delta = [a for a in audit_result.program_audits if a.program_id == "PRG-DELTA"]
    assert any(a.direction == Direction.PESSIMISTIC for a in delta)
    assert all(a.direction != Direction.OPTIMISTIC for a in delta)


def test_the_rollup_liar_is_caught_by_rollup_without_a_signal_violation(audit_result):
    # FORGE's signals stay green (no program-signal violation) yet it contradicts a workstream
    # that reported red: the rollup check is the only one that can see it.
    forge_signal = [a for a in audit_result.program_audits if a.program_id == "PRG-FORGE"]
    assert all(a.direction != Direction.OPTIMISTIC for a in forge_signal)
    forge_rollup = [r for r in audit_result.rollup_audits
                    if r.program_id == "PRG-FORGE" and r.is_violation]
    assert len(forge_rollup) > 0


def test_the_objective_program_rag_is_as_red_as_its_reddest_workstream(status_data, policy):
    # Rebuild one program-week by hand and confirm the orchestrator used worst_of.
    result = run_audit(status_data, policy)
    cedar = [a for a in result.program_audits if a.program_id == "PRG-CEDAR" and a.week == 20]
    assert cedar and cedar[0].computed == Rag.RED
