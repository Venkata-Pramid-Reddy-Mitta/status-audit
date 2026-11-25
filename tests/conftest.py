"""Shared fixtures: a repo-root path, the real policy, and the committed status data."""

from __future__ import annotations

from pathlib import Path

import pytest

from status_audit.audit import AuditResult, run_audit
from status_audit.config import Policy, load_policy
from status_audit.loader import StatusData, load_status_data

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def policy() -> Policy:
    return load_policy(REPO_ROOT / "policy.toml")


@pytest.fixture(scope="session")
def status_data() -> StatusData:
    return load_status_data(REPO_ROOT / "data")


@pytest.fixture(scope="session")
def audit_result(status_data: StatusData, policy: Policy) -> AuditResult:
    return run_audit(status_data, policy)
