"""The seeded generator behind the committed fixtures: realistic reporting behaviour.

A reconciliation tool cannot be demonstrated on honest data, because honest data has nothing
to reconcile. So the generator models reporting *behaviour*, not just numbers: each program
has a profile that distorts the gap between what its signals say and what it reports. The
audit never sees these profiles; it only ever recomputes the colour from the signals. That
separation is the whole demonstration, and it is why the generator is allowed to know the
truth while the engine is not.

Every value is produced by a seeded numpy generator, so the committed CSVs are reproducible
to the row with `python -m status_audit.generate`. The profiles are:

  honest          report equals the objective colour, every week.
  watermelon      workstream leads report honestly; the program rolls up Green for a fixed
                  number of weeks after the signals turn, then confesses. (confession lag)
  watermelon_never same, but the program never confesses within the horizon.
  sandbagger      the program reports one notch redder than the signals (pessimistic).
  rollup_liar     one workstream reports redder than its green signals, yet the program
                  still reports Green: a contradiction visible without any signal at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import load_policy
from .policy_engine import compute_rag
from .rag import Rag
from .rollup import expected_program_rag
from .signals import Signals

WEEKS = 26
SEED = 20260224


@dataclass(frozen=True)
class WorkstreamPlan:
    """How one workstream's signals evolve: when trouble starts and how fast it deepens."""

    workstream_id: str
    onset_week: int | None  # None means the workstream stays healthy all horizon
    spi_decline: float  # SPI lost per week after onset
    crit_rate: float  # criticals accrued per week after onset
    overdue_rate: float  # overdue milestones accrued per week after onset


@dataclass(frozen=True)
class ProgramPlan:
    """A program, its human-readable name, its reporting profile, and its workstreams."""

    program_id: str
    program_name: str
    profile: str
    confession_lag: int
    workstreams: tuple[WorkstreamPlan, ...]


def _plans() -> list[ProgramPlan]:
    """The fixed cast of programs. Hand-authored so each audit path has a worked example."""
    return [
        ProgramPlan(
            "PRG-ATLAS", "Atlas Core Banking", "honest", 0,
            (
                WorkstreamPlan("cloud-migration", None, 0.0, 0.0, 0.0),
                WorkstreamPlan("app-modernization", 14, 0.012, 0.15, 0.0),
                WorkstreamPlan("testing", None, 0.0, 0.0, 0.0),
            ),
        ),
        ProgramPlan(
            "PRG-BEACON", "Beacon Payments Platform", "watermelon", 4,
            (
                WorkstreamPlan("data-migration", 8, 0.03, 0.5, 0.18),
                WorkstreamPlan("integration", 11, 0.02, 0.3, 0.1),
                WorkstreamPlan("testing", None, 0.0, 0.0, 0.0),
            ),
        ),
        ProgramPlan(
            "PRG-CEDAR", "Cedar Lending Modernization", "watermelon_never", 0,
            (
                WorkstreamPlan("cloud-migration", 6, 0.035, 0.6, 0.2),
                WorkstreamPlan("app-modernization", 9, 0.025, 0.4, 0.15),
                WorkstreamPlan("deployment", 13, 0.02, 0.25, 0.1),
            ),
        ),
        ProgramPlan(
            "PRG-DELTA", "Delta Fraud Analytics", "sandbagger", 0,
            (
                WorkstreamPlan("data-migration", 16, 0.015, 0.2, 0.0),
                WorkstreamPlan("integration", None, 0.0, 0.0, 0.0),
                WorkstreamPlan("testing", None, 0.0, 0.0, 0.0),
            ),
        ),
        ProgramPlan(
            "PRG-ECHO", "Echo Mobile Banking", "watermelon", 2,
            (
                WorkstreamPlan("app-modernization", 10, 0.03, 0.45, 0.16),
                WorkstreamPlan("cloud-migration", 12, 0.02, 0.3, 0.12),
                WorkstreamPlan("deployment", None, 0.0, 0.0, 0.0),
            ),
        ),
        ProgramPlan(
            "PRG-FORGE", "Forge Regulatory Reporting", "rollup_liar", 0,
            (
                WorkstreamPlan("integration", None, 0.0, 0.0, 0.0),
                WorkstreamPlan("testing", None, 0.0, 0.0, 0.0),
                WorkstreamPlan("deployment", None, 0.0, 0.0, 0.0),
            ),
        ),
    ]


def _signals_for(plan: WorkstreamPlan, week: int, rng: np.random.Generator) -> Signals:
    """Build one workstream-week's signals from its plan plus small seeded noise."""
    noise = rng.normal(0.0, 0.01)
    if plan.onset_week is None or week < plan.onset_week:
        spi = float(np.clip(1.01 + noise, 0.9, 1.08))
        cpi = float(np.clip(1.0 + rng.normal(0.0, 0.015), 0.9, 1.08))
        return Signals(spi=spi, cpi=cpi, open_criticals=0, overdue_milestones=0,
                       open_high_risks=int(rng.integers(0, 2)))
    elapsed = week - plan.onset_week
    spi = float(np.clip(1.0 - plan.spi_decline * elapsed + noise, 0.55, 1.05))
    cpi = float(np.clip(1.0 - 0.012 * elapsed + rng.normal(0.0, 0.015), 0.7, 1.05))
    criticals = int(min(round(plan.crit_rate * elapsed), 6))
    overdue = int(min(round(plan.overdue_rate * elapsed), 4))
    risks = int(min(rng.integers(0, 3) + (elapsed // 4), 5))
    return Signals(spi=spi, cpi=cpi, open_criticals=criticals,
                   overdue_milestones=overdue, open_high_risks=risks)


def _reported_workstream_rag(
    profile: str, workstream_id: str, objective: Rag, week: int, rng: np.random.Generator
) -> Rag:
    """What a workstream lead reports, given the program's profile and the objective colour."""
    if profile == "rollup_liar" and workstream_id == "integration":
        # One workstream reports one notch redder than its (healthy) signals, out of caution.
        bumped = Rag(min(int(objective) + 1, int(Rag.RED)))
        return bumped if week >= 5 else objective
    # In every modelled profile the workstream leads themselves report honestly; the
    # distortion that the watermelon profiles introduce happens at the program rollup.
    return objective


def _reported_program_rag(
    plan: ProgramPlan, objective: Rag, objective_onset: int | None, week: int
) -> Rag:
    """What the program reports to the steering committee, applying the profile's distortion."""
    if plan.profile == "honest":
        return objective
    if plan.profile == "sandbagger":
        return Rag(min(int(objective) + 1, int(Rag.RED)))
    if plan.profile == "rollup_liar":
        return Rag.GREEN
    if plan.profile == "watermelon_never":
        return Rag.GREEN
    if plan.profile == "watermelon":
        if objective_onset is None:
            return objective
        if week < objective_onset + plan.confession_lag:
            return Rag.GREEN
        return objective
    raise ValueError(f"unknown profile: {plan.profile}")


def generate_frames(seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Produce the (workstreams, programs, names) frames deterministically for a seed."""
    rng = np.random.default_rng(seed)
    policy = load_policy(Path(__file__).resolve().parents[2] / "policy.toml")
    plans = _plans()

    ws_rows: list[dict] = []
    pg_rows: list[dict] = []
    name_rows: list[dict] = []

    for plan in plans:
        name_rows.append({"program_id": plan.program_id, "program_name": plan.program_name})

        # First pass: objective colours per week, needed to find the objective onset.
        objective_by_week: dict[int, Rag] = {}
        signals_by_week: dict[int, list[tuple[WorkstreamPlan, Signals, Rag]]] = {}
        for week in range(1, WEEKS + 1):
            per_ws = []
            for wplan in plan.workstreams:
                sig = _signals_for(wplan, week, rng)
                obj = compute_rag(sig, policy).rag
                per_ws.append((wplan, sig, obj))
            signals_by_week[week] = per_ws
            objective_by_week[week] = expected_program_rag([o for _, _, o in per_ws], "worst_of")

        objective_onset = next(
            (w for w in range(1, WEEKS + 1) if objective_by_week[w] != Rag.GREEN), None
        )

        for week in range(1, WEEKS + 1):
            for wplan, sig, obj in signals_by_week[week]:
                rep_ws = _reported_workstream_rag(plan.profile, wplan.workstream_id, obj, week, rng)
                ws_rows.append({
                    "program_id": plan.program_id,
                    "workstream_id": wplan.workstream_id,
                    "week": week,
                    "reported_rag": rep_ws.letter,
                    "spi": round(sig.spi, 3),
                    "cpi": round(sig.cpi, 3),
                    "open_criticals": sig.open_criticals,
                    "overdue_milestones": sig.overdue_milestones,
                    "open_high_risks": sig.open_high_risks,
                })
            rep_pg = _reported_program_rag(plan, objective_by_week[week], objective_onset, week)
            pg_rows.append({
                "program_id": plan.program_id,
                "week": week,
                "reported_rag": rep_pg.letter,
            })

    return (
        pd.DataFrame(ws_rows),
        pd.DataFrame(pg_rows),
        pd.DataFrame(name_rows),
    )


def write_fixtures(data_dir: str | Path, seed: int = SEED) -> None:
    """Write the three CSV fixtures into data_dir, creating it if needed."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    workstreams, programs, names = generate_frames(seed)
    workstreams.to_csv(data_dir / "workstream_status.csv", index=False)
    programs.to_csv(data_dir / "program_status.csv", index=False)
    names.to_csv(data_dir / "programs.csv", index=False)


def main() -> None:  # pragma: no cover
    """Regenerate the committed fixtures under the repository's data/ directory."""
    data_dir = Path(__file__).resolve().parents[2] / "data"
    write_fixtures(data_dir)
    print(f"wrote fixtures to {data_dir}")


if __name__ == "__main__":  # pragma: no cover
    main()
