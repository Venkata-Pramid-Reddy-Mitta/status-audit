"""Signals: construction, the validation that rejects impossible inputs, and row coercion."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from status_audit.signals import SignalError, Signals, signals_from_row


def test_a_healthy_signal_record_constructs():
    s = Signals(spi=1.0, cpi=1.0, open_criticals=0, overdue_milestones=0, open_high_risks=0)
    assert s.spi == 1.0


def test_a_negative_spi_is_refused_at_the_boundary():
    with pytest.raises(SignalError, match="spi"):
        Signals(spi=-0.1, cpi=1.0, open_criticals=0, overdue_milestones=0, open_high_risks=0)


def test_a_negative_cpi_is_refused():
    with pytest.raises(SignalError, match="cpi"):
        Signals(spi=1.0, cpi=-1.0, open_criticals=0, overdue_milestones=0, open_high_risks=0)


@pytest.mark.parametrize("field", ["open_criticals", "overdue_milestones", "open_high_risks"])
def test_a_negative_count_is_refused(field):
    kwargs = {"spi": 1.0, "cpi": 1.0, "open_criticals": 0, "overdue_milestones": 0,
              "open_high_risks": 0}
    kwargs[field] = -1
    with pytest.raises(SignalError, match=field):
        Signals(**kwargs)


def test_signals_from_row_coerces_numpy_scalars_to_plain_python():
    row = {
        "spi": np.float64(0.9), "cpi": np.float64(0.95),
        "open_criticals": np.int64(2), "overdue_milestones": np.int64(1),
        "open_high_risks": np.int64(0),
    }
    s = signals_from_row(row)
    assert type(s.spi) is float
    assert type(s.open_criticals) is int


def test_signals_from_row_names_the_missing_column():
    with pytest.raises(SignalError, match="missing a signal column"):
        signals_from_row({"spi": 1.0})


def test_signals_is_frozen():
    s = Signals(spi=1.0, cpi=1.0, open_criticals=0, overdue_milestones=0, open_high_risks=0)
    with pytest.raises(FrozenInstanceError):
        s.spi = 0.5  # type: ignore[misc]
