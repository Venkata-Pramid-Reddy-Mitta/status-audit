"""The generator: determinism, schema, and that it reproduces the committed fixtures."""

from __future__ import annotations

import pandas as pd
import pytest

from status_audit.generate import (
    SEED,
    ProgramPlan,
    _reported_program_rag,
    generate_frames,
    write_fixtures,
)
from status_audit.loader import WORKSTREAM_COLUMNS
from status_audit.rag import Rag


def test_the_generator_is_deterministic_for_a_seed():
    a_ws, a_pg, a_names = generate_frames(SEED)
    b_ws, b_pg, b_names = generate_frames(SEED)
    pd.testing.assert_frame_equal(a_ws, b_ws)
    pd.testing.assert_frame_equal(a_pg, b_pg)
    pd.testing.assert_frame_equal(a_names, b_names)


def test_a_different_seed_changes_the_signals():
    a_ws, _, _ = generate_frames(SEED)
    b_ws, _, _ = generate_frames(SEED + 1)
    assert not a_ws.equals(b_ws)


def test_the_workstream_frame_has_every_required_column():
    ws, _, _ = generate_frames(SEED)
    assert set(ws.columns) >= WORKSTREAM_COLUMNS


def test_the_generated_frames_have_the_expected_shape():
    ws, pg, names = generate_frames(SEED)
    assert len(ws) == 6 * 3 * 26  # programs x workstreams x weeks
    assert len(pg) == 6 * 26
    assert len(names) == 6


def test_write_fixtures_writes_three_csvs(tmp_path):
    write_fixtures(tmp_path)
    for name in ("workstream_status.csv", "program_status.csv", "programs.csv"):
        assert (tmp_path / name).exists()


def test_regenerating_reproduces_the_committed_workstream_file(repo_root, tmp_path):
    # The committed CSV must be exactly what `make generate` would write, so a reviewer can
    # trust that the fixture was not hand-edited after generation.
    write_fixtures(tmp_path)
    fresh = pd.read_csv(tmp_path / "workstream_status.csv")
    committed = pd.read_csv(repo_root / "data" / "workstream_status.csv")
    pd.testing.assert_frame_equal(fresh, committed)


def test_regenerating_reproduces_the_committed_program_file(repo_root, tmp_path):
    write_fixtures(tmp_path)
    fresh = pd.read_csv(tmp_path / "program_status.csv")
    committed = pd.read_csv(repo_root / "data" / "program_status.csv")
    pd.testing.assert_frame_equal(fresh, committed)


def _plan(profile: str) -> ProgramPlan:
    return ProgramPlan("PRG-T", "Test", profile, 3, ())


def test_a_watermelon_with_no_objective_onset_reports_the_objective_colour():
    # Defensive branch: a watermelon program whose signals never turned reports honestly.
    result = _reported_program_rag(_plan("watermelon"), Rag.GREEN, None, 5)
    assert result == Rag.GREEN


def test_an_unknown_profile_raises():
    with pytest.raises(ValueError, match="unknown profile"):
        _reported_program_rag(_plan("mystery"), Rag.GREEN, 3, 5)
