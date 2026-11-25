"""Render an AuditResult three ways: a JSON record, a terminal table, and an HTML report.

The three renderings serve three readers. The JSON is what the receipts re-measure and what
a Power BI or a downstream model would consume, so it is exhaustive and typed-down to plain
Python. The terminal table is what a PM sees in a pipeline step, so it leads with the verdict
and the headline. The HTML report is what gets screenshotted for evidence, so it carries a
verdict badge whose colour a pixel-level check can read back. Keeping all three in one module
means the headline number is defined once and cannot drift between the three surfaces.
"""

from __future__ import annotations

import html
import json

from .audit import AuditResult
from .confession import ConfessionResult
from .rag import Rag
from .reconcile import UnitAudit
from .rollup import RollupAudit

_RAG_HEX = {Rag.GREEN: "#1b7f3b", Rag.AMBER: "#b5790b", Rag.RED: "#b3261e"}


def _unit_dict(a: UnitAudit) -> dict:
    return {
        "program_id": a.program_id,
        "workstream_id": a.workstream_id,
        "week": a.week,
        "reported": str(a.reported),
        "computed": str(a.computed),
        "direction": a.direction.value,
        "severity": a.severity,
        "reasons": list(a.reasons),
    }


def _rollup_dict(r: RollupAudit) -> dict:
    return {
        "program_id": r.program_id,
        "week": r.week,
        "reported": str(r.reported),
        "expected": str(r.expected),
        "direction": r.direction.value,
        "rule": r.rule,
        "workstream_rags": [str(x) for x in r.workstream_rags],
        "is_violation": r.is_violation,
    }


def _confession_dict(c: ConfessionResult) -> dict:
    return {
        "program_id": c.program_id,
        "objective_onset_week": c.objective_onset_week,
        "reported_onset_week": c.reported_onset_week,
        "lag_weeks": c.lag_weeks,
        "never_confessed": c.never_confessed,
    }


def build_report_dict(result: AuditResult) -> dict:
    """Assemble the full, JSON-serializable audit record."""
    return {
        "summary": {
            "total_reports": result.total_reports,
            "workstream_weeks": len(result.workstream_audits),
            "program_weeks": len(result.program_audits),
            "optimistic_program_weeks": result.optimistic_program_weeks,
            "optimistic_workstream_weeks": result.optimistic_workstream_weeks,
            "green_over_trouble_program_weeks": result.green_over_trouble_program_weeks,
            "rollup_violations": result.rollup_violations,
            "programs_never_confessed": result.programs_never_confessed,
            "confession_lags": result.confession_lags,
            "max_confession_lag": result.max_confession_lag,
            "blocking_optimistic": result.blocking_optimistic,
            "gate_passed": result.gate_passed(),
        },
        "program_audits": [_unit_dict(a) for a in result.program_audits],
        "workstream_audits": [_unit_dict(a) for a in result.workstream_audits],
        "rollup_audits": [_rollup_dict(r) for r in result.rollup_audits],
        "confessions": [_confession_dict(c) for c in result.confessions],
    }


def render_json(result: AuditResult) -> str:
    """The audit record as pretty-printed JSON."""
    return json.dumps(build_report_dict(result), indent=2)


def render_text(result: AuditResult) -> str:
    """A compact terminal report: verdict first, then the headline and the per-program lags."""
    s = result
    verdict = "FAIL" if not s.gate_passed() else "PASS"
    lines = [
        f"status-audit verdict: {verdict}",
        f"  reports reconciled:            {s.total_reports}"
        f"  ({len(s.workstream_audits)} workstream-weeks, {len(s.program_audits)} program-weeks)",
        f"  program-weeks Green over trouble: {s.green_over_trouble_program_weeks}"
        f"  (the signals said Amber/Red, the report said Green)",
        f"  rollup integrity violations:   {s.rollup_violations}",
        f"  programs that never confessed: {s.programs_never_confessed}",
        f"  max confession lag (weeks):    {s.max_confession_lag}",
        "",
        "  per-program confession lag:",
    ]
    for c in sorted(s.confessions, key=lambda x: x.program_id):
        name = result.names.get(c.program_id, c.program_id)
        if c.never_confessed:
            tag = "NEVER CONFESSED"
        elif c.lag_weeks > 0:
            tag = (
                f"lag {c.lag_weeks}w (signals wk {c.objective_onset_week}, "
                f"report wk {c.reported_onset_week})"
            )
        else:
            tag = "no optimistic episode"
        lines.append(f"    {c.program_id} {name:<32} {tag}")
    return "\n".join(lines)


_STYLE = """
body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
       color: #1c1c1c; background: #ffffff; margin: 0; padding: 32px 40px; }
h1 { font-size: 24px; margin: 0 0 4px 0; }
h2 { font-size: 17px; margin: 28px 0 10px 0; border-bottom: 1px solid #e3e3e3;
     padding-bottom: 4px; }
.subtitle { color: #555; margin: 0 0 20px 0; }
.badge { display: inline-block; padding: 6px 14px; border-radius: 4px;
         color: #ffffff; font-weight: 700; font-size: 15px; letter-spacing: 0.3px; }
.badge-fail { background: #b3261e; }
.badge-pass { background: #1b7f3b; }
.headline { font-size: 15px; margin: 14px 0; }
.big { font-size: 30px; font-weight: 700; color: #b3261e; }
table { border-collapse: collapse; width: 100%; font-size: 13px; margin: 8px 0 4px 0; }
th, td { border: 1px solid #dcdcdc; padding: 6px 9px; text-align: left; }
th { background: #f4f4f4; }
.cell-rag { font-weight: 700; }
.note { color: #555; font-size: 12.5px; margin: 6px 0 0 0; }
"""


def _rag_cell(rag: Rag) -> str:
    return f'<td class="cell-rag" style="color:{_RAG_HEX[rag]}">{html.escape(str(rag))}</td>'


def render_html(result: AuditResult) -> str:
    """A self-contained HTML report with a verdict badge, for evidence capture.

    The badge class is `badge badge-fail` or `badge badge-pass`; the screenshot tool reads its
    computed colour back and fails if it is invisible, so these classes and the stylesheet must
    stay in lockstep. A test asserts that every class used here has a rule in `_STYLE`.
    """
    s = result
    passed = s.gate_passed()
    badge_class = "badge-pass" if passed else "badge-fail"
    badge_text = "PASS" if passed else "FAIL"

    confession_rows = []
    for c in sorted(s.confessions, key=lambda x: x.program_id):
        name = html.escape(result.names.get(c.program_id, c.program_id))
        if c.never_confessed:
            detail = "never confessed"
        elif c.lag_weeks > 0:
            detail = f"{c.lag_weeks} weeks late"
        else:
            detail = "on time or conservative"
        onset = c.objective_onset_week if c.objective_onset_week is not None else "-"
        rep = c.reported_onset_week if c.reported_onset_week is not None else "-"
        confession_rows.append(
            f"<tr><td>{html.escape(c.program_id)}</td><td>{name}</td>"
            f"<td>{onset}</td><td>{rep}</td><td>{detail}</td></tr>"
        )

    program_count = len({a.program_id for a in s.program_audits})
    optimistic = [a for a in s.program_audits if int(a.reported) < int(a.computed)]
    optimistic.sort(key=lambda a: (-a.severity, a.program_id, a.week))
    worst_rows = []
    for a in optimistic[:12]:
        name = html.escape(result.names.get(a.program_id, a.program_id))
        reason = html.escape(a.reasons[0]) if a.reasons else ""
        worst_rows.append(
            f"<tr><td>{html.escape(a.program_id)}</td><td>{name}</td><td>{a.week}</td>"
            f"{_rag_cell(a.reported)}{_rag_cell(a.computed)}<td>{reason}</td></tr>"
        )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>status-audit report</title><style>{_STYLE}</style></head>
<body>
<h1>Program status audit</h1>
<p class="subtitle">Independent recomputation of {program_count} programs over the horizon.</p>

<h2>Verdict</h2>
<p><span class="badge {badge_class}">{badge_text}</span></p>
<p class="note">The gate fails when optimistic program-weeks exceed the policy budget
({s.policy.max_optimistic_allowed} allowed at severity &ge; {s.policy.min_severity}).
Found {s.blocking_optimistic}.</p>

<h2>Headline findings</h2>
<p class="headline"><span class="big">{s.green_over_trouble_program_weeks}</span>
program-weeks were reported Green while the objective policy computed Amber or Red.</p>
<p class="headline">Of {s.total_reports} reconciled reports, {s.optimistic_program_weeks}
program-weeks were optimistic and {s.rollup_violations} program-weeks contradicted their own
workstreams under the rollup rule.</p>

<h2>Confession lag</h2>
<table><thead><tr><th>Program</th><th>Name</th><th>Signals turned (week)</th>
<th>Report turned (week)</th><th>Verdict</th></tr></thead>
<tbody>{''.join(confession_rows)}</tbody></table>
<p class="note">Confession lag is the gap between the first objectively non-green week and the
first reported non-green week. {s.programs_never_confessed} program never confessed within the
horizon; the longest confession lag was {s.max_confession_lag} weeks.</p>

<h2>Worst optimistic program-weeks</h2>
<table><thead><tr><th>Program</th><th>Name</th><th>Week</th><th>Reported</th>
<th>Computed</th><th>Why the signals disagreed</th></tr></thead>
<tbody>{''.join(worst_rows)}</tbody></table>

<h2>What this cannot establish</h2>
<p class="note">This audit reports disagreement between a report and a written policy, not
ground truth. A flagged week means the report and the policy disagree; it does not prove the
program was in trouble, because the policy thresholds are themselves a choice. The companion
sensitivity sweep prices that choice.</p>
</body></html>"""
