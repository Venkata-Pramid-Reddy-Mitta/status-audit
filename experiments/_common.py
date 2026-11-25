"""Shared setup for the experiments: locate the repo, load the policy and the committed data.

Experiments are run both directly (for a human reading a table) and by the metrics collector
(for the machine-checked numbers), so the loading is centralised here and every experiment
reports against exactly the same data and policy the CLI uses.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from status_audit.audit import AuditResult, run_audit  # noqa: E402
from status_audit.config import Policy, load_policy  # noqa: E402
from status_audit.loader import StatusData, load_status_data  # noqa: E402

OUT_DIR = REPO_ROOT / "docs" / "experiments"


def load() -> tuple[StatusData, Policy]:
    return load_status_data(REPO_ROOT / "data"), load_policy(REPO_ROOT / "policy.toml")


def audit() -> AuditResult:
    data, policy = load()
    return run_audit(data, policy)


def write(name: str, payload: dict) -> Path:
    """Write an experiment's result to docs/experiments/<name>.json and return the path."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
