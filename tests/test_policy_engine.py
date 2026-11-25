"""The engine: the pure function that recomputes a RAG and names why it fired."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from status_audit.policy_engine import Verdict, compute_rag
from status_audit.rag import Rag
from status_audit.signals import Signals


def green():
    return Signals(spi=1.0, cpi=1.0, open_criticals=0, overdue_milestones=0, open_high_risks=0)


def test_all_signals_within_thresholds_computes_green(policy):
    v = compute_rag(green(), policy)
    assert v.rag == Rag.GREEN
    assert v.reasons == ()


def test_a_green_verdict_has_no_padding_reasons(policy):
    assert compute_rag(green(), policy).worst_reason == "all signals within green thresholds"


def test_spi_below_the_amber_line_computes_amber(policy):
    s = Signals(spi=0.90, cpi=1.0, open_criticals=0, overdue_milestones=0, open_high_risks=0)
    assert compute_rag(s, policy).rag == Rag.AMBER


def test_spi_below_the_red_line_computes_red(policy):
    s = Signals(spi=0.80, cpi=1.0, open_criticals=0, overdue_milestones=0, open_high_risks=0)
    assert compute_rag(s, policy).rag == Rag.RED


def test_spi_exactly_on_the_amber_line_is_still_green(policy):
    # The band is strict-below, so 0.95 is not yet amber.
    s = Signals(spi=0.95, cpi=1.0, open_criticals=0, overdue_milestones=0, open_high_risks=0)
    assert compute_rag(s, policy).rag == Rag.GREEN


def test_three_open_criticals_computes_red(policy):
    s = Signals(spi=1.0, cpi=1.0, open_criticals=3, overdue_milestones=0, open_high_risks=0)
    assert compute_rag(s, policy).rag == Rag.RED


def test_one_open_critical_computes_amber(policy):
    s = Signals(spi=1.0, cpi=1.0, open_criticals=1, overdue_milestones=0, open_high_risks=0)
    assert compute_rag(s, policy).rag == Rag.AMBER


def test_two_overdue_milestones_computes_red(policy):
    s = Signals(spi=1.0, cpi=1.0, open_criticals=0, overdue_milestones=2, open_high_risks=0)
    assert compute_rag(s, policy).rag == Rag.RED


def test_cost_alone_never_forces_red(policy):
    # CPI far below the line, everything else clean: cost tops out at amber by design.
    s = Signals(spi=1.0, cpi=0.50, open_criticals=0, overdue_milestones=0, open_high_risks=0)
    assert compute_rag(s, policy).rag == Rag.AMBER


def test_risks_alone_never_force_red(policy):
    s = Signals(spi=1.0, cpi=1.0, open_criticals=0, overdue_milestones=0, open_high_risks=5)
    assert compute_rag(s, policy).rag == Rag.AMBER


def test_the_verdict_is_the_worst_band_not_the_average(policy):
    # One red dimension (SPI) and four green: the verdict is red, never diluted to amber.
    s = Signals(spi=0.80, cpi=1.0, open_criticals=0, overdue_milestones=0, open_high_risks=0)
    assert compute_rag(s, policy).rag == Rag.RED


def test_the_worst_reason_belongs_to_the_worst_band(policy):
    # Red SPI and amber cost together: the first reason must be the red one.
    s = Signals(spi=0.80, cpi=0.80, open_criticals=0, overdue_milestones=0, open_high_risks=0)
    v = compute_rag(s, policy)
    assert v.rag == Rag.RED
    assert "SPI" in v.worst_reason and "red" in v.worst_reason


def test_reasons_include_lesser_bands_after_the_worst(policy):
    s = Signals(spi=0.80, cpi=0.80, open_criticals=0, overdue_milestones=0, open_high_risks=0)
    v = compute_rag(s, policy)
    joined = " ".join(v.reasons)
    assert "CPI" in joined  # the amber cost reason is retained, after the red one


def test_the_engine_is_a_pure_function_of_its_inputs(policy):
    s = Signals(spi=0.9, cpi=0.9, open_criticals=2, overdue_milestones=1, open_high_risks=1)
    assert compute_rag(s, policy) == compute_rag(s, policy)


def test_verdict_is_frozen(policy):
    v = compute_rag(green(), policy)
    assert isinstance(v, Verdict)
    with pytest.raises(FrozenInstanceError):
        v.rag = Rag.RED  # type: ignore[misc]
