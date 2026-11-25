"""Loading and the strict validation that refuses a partial or malformed dataset."""

from __future__ import annotations

import pandas as pd
import pytest

from status_audit.loader import DataError, load_status_data
from status_audit.rag import Rag


def _write_min(data_dir, ws_rows, pg_rows, names_rows=None):
    pd.DataFrame(ws_rows).to_csv(data_dir / "workstream_status.csv", index=False)
    pd.DataFrame(pg_rows).to_csv(data_dir / "program_status.csv", index=False)
    if names_rows is not None:
        pd.DataFrame(names_rows).to_csv(data_dir / "programs.csv", index=False)


def _ws(program, ws, week, rag="G"):
    return {
        "program_id": program, "workstream_id": ws, "week": week, "reported_rag": rag,
        "spi": 1.0, "cpi": 1.0, "open_criticals": 0, "overdue_milestones": 0,
        "open_high_risks": 0,
    }


def test_the_committed_data_loads(repo_root):
    data = load_status_data(repo_root / "data")
    assert len(data.program_ids) == 6
    assert data.weeks == list(range(1, 27))


def test_the_reported_rag_column_is_parsed_into_rag_values(repo_root):
    data = load_status_data(repo_root / "data")
    assert set(data.programs["reported_rag"]) <= {Rag.GREEN, Rag.AMBER, Rag.RED}


def test_program_names_are_loaded_when_present(repo_root):
    data = load_status_data(repo_root / "data")
    assert data.names["PRG-ATLAS"] == "Atlas Core Banking"


def test_a_missing_workstream_file_raises(tmp_path):
    pd.DataFrame([{"program_id": "P", "week": 1, "reported_rag": "G"}]).to_csv(
        tmp_path / "program_status.csv", index=False
    )
    with pytest.raises(DataError, match="not found"):
        load_status_data(tmp_path)


def test_a_missing_column_is_named(tmp_path):
    pd.DataFrame([{"program_id": "P", "week": 1}]).to_csv(
        tmp_path / "workstream_status.csv", index=False
    )
    pd.DataFrame([{"program_id": "P", "week": 1, "reported_rag": "G"}]).to_csv(
        tmp_path / "program_status.csv", index=False
    )
    with pytest.raises(DataError, match="missing columns"):
        load_status_data(tmp_path)


def test_an_unparseable_rag_cell_is_rejected_with_its_value(tmp_path):
    _write_min(
        tmp_path,
        [_ws("P", "w", 1, rag="purple")],
        [{"program_id": "P", "week": 1, "reported_rag": "G"}],
    )
    with pytest.raises(DataError, match="unparseable"):
        load_status_data(tmp_path)


def test_a_workstream_week_with_no_program_row_is_rejected(tmp_path):
    _write_min(
        tmp_path,
        [_ws("P", "w", 1), _ws("P", "w", 2)],
        [{"program_id": "P", "week": 1, "reported_rag": "G"}],
    )
    with pytest.raises(DataError, match="no matching program week"):
        load_status_data(tmp_path)


def test_a_program_week_with_no_workstream_rows_is_rejected(tmp_path):
    _write_min(
        tmp_path,
        [_ws("P", "w", 1)],
        [
            {"program_id": "P", "week": 1, "reported_rag": "G"},
            {"program_id": "P", "week": 2, "reported_rag": "G"},
        ],
    )
    with pytest.raises(DataError, match="no matching workstream"):
        load_status_data(tmp_path)


def test_missing_programs_csv_is_tolerated(tmp_path):
    _write_min(
        tmp_path,
        [_ws("P", "w", 1)],
        [{"program_id": "P", "week": 1, "reported_rag": "G"}],
    )
    data = load_status_data(tmp_path)
    assert data.names == {}


def test_a_programs_csv_without_name_columns_is_ignored(tmp_path):
    _write_min(
        tmp_path,
        [_ws("P", "w", 1)],
        [{"program_id": "P", "week": 1, "reported_rag": "G"}],
        names_rows=[{"program_id": "P", "label": "wrong column"}],
    )
    data = load_status_data(tmp_path)
    assert data.names == {}


def test_an_empty_input_file_is_reported(tmp_path):
    (tmp_path / "workstream_status.csv").write_text("")
    (tmp_path / "program_status.csv").write_text("")
    with pytest.raises(DataError, match="empty"):
        load_status_data(tmp_path)
