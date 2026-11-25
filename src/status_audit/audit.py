"""Orchestration: turn loaded status data into one AuditResult the report can render.

This module is the only place that knows the shape of the whole audit. It runs three
independent checks over the same data (workstream signal reconciliation, program signal
reconciliation, and rollup integrity), then the temporal confession-lag pass, and collects
the summary counts the README and the gate depend on. It holds no thresholds and does no
I/O beyond what loader.py already did: the policy decides, this module only arranges.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .confession import ConfessionResult, confession_lag
from .config import Policy
from .loader import StatusData
from .rag import Rag
from .reconcile import Direction, UnitAudit, classify, reconcile_unit
from .rollup import RollupAudit, audit_rollup, expected_program_rag
from .signals import signals_from_row


@dataclass(frozen=True)
class AuditResult:
    """Everything the report and the gate need, computed once."""

    workstream_audits: list[UnitAudit]
    program_audits: list[UnitAudit]
    rollup_audits: list[RollupAudit]
    confessions: list[ConfessionResult]
    policy: Policy
    names: dict[str, str] = field(default_factory=dict)

    # --- summary counts, all derived so they can never drift from the records above ---

    @property
    def total_reports(self) -> int:
        """Every reported cell the audit reconciled: workstream-weeks plus program-weeks."""
        return len(self.workstream_audits) + len(self.program_audits)

    @property
    def optimistic_workstream_weeks(self) -> int:
        return sum(1 for a in self.workstream_audits if a.direction == Direction.OPTIMISTIC)

    @property
    def optimistic_program_weeks(self) -> int:
        return sum(1 for a in self.program_audits if a.direction == Direction.OPTIMISTIC)

    @property
    def green_over_trouble_program_weeks(self) -> int:
        """The headline: program-weeks reported Green while the signals said Amber or Red."""
        return sum(
            1
            for a in self.program_audits
            if a.reported == Rag.GREEN and a.computed in (Rag.AMBER, Rag.RED)
        )

    @property
    def rollup_violations(self) -> int:
        return sum(1 for r in self.rollup_audits if r.is_violation)

    @property
    def programs_never_confessed(self) -> int:
        return sum(1 for c in self.confessions if c.never_confessed)

    @property
    def confession_lags(self) -> list[int]:
        """Positive confession lags, one per program that eventually confessed late."""
        return sorted(c.lag_weeks for c in self.confessions if c.lag_weeks > 0)

    @property
    def max_confession_lag(self) -> int:
        lags = self.confession_lags
        return max(lags) if lags else 0

    @property
    def blocking_optimistic(self) -> int:
        """Optimistic program-weeks at/above the policy severity floor: what the gate counts."""
        return sum(
            1
            for a in self.program_audits
            if a.direction == Direction.OPTIMISTIC and a.severity >= self.policy.min_severity
        )

    def gate_passed(self) -> bool:
        """True when blocking optimistic program-weeks stay within the allowed budget."""
        return self.blocking_optimistic <= self.policy.max_optimistic_allowed


def _objective_program_series(
    data: StatusData, program_id: str, policy: Policy
) -> tuple[list[int], list[Rag], list[Rag]]:
    """Per-week objective and reported program RAG series for one program, aligned by week."""
    ws = data.workstreams[data.workstreams["program_id"] == program_id]
    pg = data.programs[data.programs["program_id"] == program_id].sort_values("week")
    weeks: list[int] = []
    objective: list[Rag] = []
    reported: list[Rag] = []
    for _, prow in pg.iterrows():
        week = int(prow["week"])
        week_ws = ws[ws["week"] == week]
        computed_rags = [
            reconcile_unit(
                program_id,
                str(r["workstream_id"]),
                week,
                r["reported_rag"],
                signals_from_row(r),
                policy,
            ).computed
            for _, r in week_ws.iterrows()
        ]
        weeks.append(week)
        objective.append(expected_program_rag(computed_rags, "worst_of"))
        reported.append(prow["reported_rag"])
    return weeks, objective, reported


def run_audit(data: StatusData, policy: Policy) -> AuditResult:
    """Run every check over the loaded data and return the aggregated result.

    The program-level objective RAG is always rolled up from the computed workstream RAGs
    with "worst_of", independent of the rollup *integrity* rule: the question "what do the
    signals say this program is" has one honest answer (as red as its reddest part), whereas
    the rollup rule is a separate lever used only to test the reporter's own consistency.
    """
    workstream_audits: list[UnitAudit] = []
    for _, row in data.workstreams.iterrows():
        workstream_audits.append(
            reconcile_unit(
                program_id=str(row["program_id"]),
                workstream_id=str(row["workstream_id"]),
                week=int(row["week"]),
                reported=row["reported_rag"],
                signals=signals_from_row(row),
                policy=policy,
            )
        )

    program_audits: list[UnitAudit] = []
    rollup_audits: list[RollupAudit] = []
    confessions: list[ConfessionResult] = []

    for program_id in data.program_ids:
        weeks, objective, reported = _objective_program_series(data, program_id, policy)
        ws = data.workstreams[data.workstreams["program_id"] == program_id]

        for week, obj_rag, rep_rag in zip(weeks, objective, reported, strict=True):
            program_audits.append(
                UnitAudit(
                    program_id=program_id,
                    workstream_id=None,
                    week=week,
                    reported=rep_rag,
                    computed=obj_rag,
                    direction=classify(rep_rag, obj_rag),
                    severity=abs(int(rep_rag) - int(obj_rag)),
                    reasons=(f"signals roll up to {obj_rag} across workstreams",)
                    if obj_rag != Rag.GREEN
                    else (),
                )
            )
            reported_ws_rags = [
                r["reported_rag"] for _, r in ws[ws["week"] == week].iterrows()
            ]
            rollup_audits.append(
                audit_rollup(program_id, week, rep_rag, reported_ws_rags, policy)
            )

        confessions.append(confession_lag(program_id, weeks, objective, reported))

    return AuditResult(
        workstream_audits=workstream_audits,
        program_audits=program_audits,
        rollup_audits=rollup_audits,
        confessions=confessions,
        policy=policy,
        names=data.names,
    )
