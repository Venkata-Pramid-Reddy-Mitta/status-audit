"""Threshold sensitivity: the headline's dependence on the amber SPI line."""

from __future__ import annotations

from status_audit.sensitivity import sweep_amber_spi


def test_the_sweep_returns_one_point_per_valid_threshold(status_data, policy):
    points = sweep_amber_spi(status_data, policy, [0.90, 0.925, 0.95, 0.975, 1.0])
    assert [p.amber_below_spi for p in points] == [0.90, 0.925, 0.95, 0.975, 1.0]


def test_a_threshold_below_the_red_line_is_skipped_not_raised(status_data, policy):
    # 0.80 is below the red line (0.85) and is incoherent as an amber line, so it is dropped.
    points = sweep_amber_spi(status_data, policy, [0.80, 0.95])
    assert [p.amber_below_spi for p in points] == [0.95]


def test_tightening_the_amber_line_never_reduces_the_optimistic_count(status_data, policy):
    points = sweep_amber_spi(status_data, policy, [0.90, 0.95, 0.975, 1.0])
    counts = [p.optimistic_program_weeks for p in points]
    assert counts == sorted(counts)  # monotonic non-decreasing in the threshold


def test_the_headline_at_the_default_threshold_matches_the_full_audit(status_data, policy, audit_result):
    points = sweep_amber_spi(status_data, policy, [policy.amber_below_spi])
    assert points[0].green_over_trouble_program_weeks == audit_result.green_over_trouble_program_weeks
