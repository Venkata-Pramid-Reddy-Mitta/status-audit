"""Load the three status CSVs into validated frames, failing loudly on a bad shape.

The tool's credibility rests on the recomputed RAG, and a recomputed RAG is only as good as
the join behind it. So loading is strict: required columns must be present, weeks must be
integers, every workstream-week must have a matching program-week and vice versa, and RAG
cells must parse. A silent row drop or an unmatched join here would change the headline
count without any error, which is the failure mode this module is written to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .rag import parse_rag

WORKSTREAM_COLUMNS = {
    "program_id",
    "workstream_id",
    "week",
    "reported_rag",
    "spi",
    "cpi",
    "open_criticals",
    "overdue_milestones",
    "open_high_risks",
}
PROGRAM_COLUMNS = {"program_id", "week", "reported_rag"}


class DataError(ValueError):
    """Raised when the input CSVs are missing, malformed, or fail to reconcile their keys."""


@dataclass(frozen=True)
class StatusData:
    """The loaded, validated status data: workstream rows, program rows, program names."""

    workstreams: pd.DataFrame
    programs: pd.DataFrame
    names: dict[str, str]

    @property
    def program_ids(self) -> list[str]:
        return sorted(self.programs["program_id"].unique())

    @property
    def weeks(self) -> list[int]:
        return sorted(int(w) for w in self.programs["week"].unique())


def _read_csv(path: Path, required: set[str]) -> pd.DataFrame:
    if not path.exists():
        raise DataError(f"input file not found: {path}")
    try:
        frame = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise DataError(f"input file is empty: {path}") from exc
    missing = required - set(frame.columns)
    if missing:
        raise DataError(f"{path.name} is missing columns: {sorted(missing)}")
    return frame


def load_status_data(data_dir: str | Path) -> StatusData:
    """Read workstream_status.csv, program_status.csv and programs.csv from a directory.

    Validates that the reported_rag cells parse and that the program/workstream key sets
    agree, so that the audit never silently scores a partial dataset.
    """
    data_dir = Path(data_dir)
    workstreams = _read_csv(data_dir / "workstream_status.csv", WORKSTREAM_COLUMNS)
    programs = _read_csv(data_dir / "program_status.csv", PROGRAM_COLUMNS)

    names_path = data_dir / "programs.csv"
    names: dict[str, str] = {}
    if names_path.exists():
        names_frame = pd.read_csv(names_path)
        if {"program_id", "program_name"} <= set(names_frame.columns):
            names = dict(zip(names_frame["program_id"], names_frame["program_name"], strict=True))

    # Parse (and therefore validate) every RAG cell up front; a bad cell raises here with the
    # offending value rather than deep inside the engine.
    for frame, label in ((workstreams, "workstream_status"), (programs, "program_status")):
        try:
            frame["reported_rag"] = frame["reported_rag"].map(parse_rag)
        except ValueError as exc:
            raise DataError(f"{label}.csv has an unparseable reported_rag: {exc}") from exc
        frame["week"] = frame["week"].astype(int)

    ws_keys = set(zip(workstreams["program_id"], workstreams["week"], strict=True))
    pg_keys = set(zip(programs["program_id"], programs["week"], strict=True))
    only_ws = ws_keys - pg_keys
    only_pg = pg_keys - ws_keys
    if only_ws:
        raise DataError(f"workstream weeks with no matching program week: {sorted(only_ws)[:5]}")
    if only_pg:
        raise DataError(f"program weeks with no matching workstream rows: {sorted(only_pg)[:5]}")

    return StatusData(workstreams=workstreams, programs=programs, names=names)
