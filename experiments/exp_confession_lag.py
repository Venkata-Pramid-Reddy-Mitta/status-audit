"""Experiment: how many weeks did each program stay green after its signals turned?

Answers the README's confession-lag question. Reports, per program, the first objectively
non-green week, the first reported non-green week, and the gap, plus the programs that never
confessed within the horizon.
"""

from __future__ import annotations

from _common import audit, write

NAME = "confession_lag"


def run() -> dict:
    result = audit()
    rows = []
    for c in sorted(result.confessions, key=lambda x: x.program_id):
        rows.append({
            "program_id": c.program_id,
            "name": result.names.get(c.program_id, c.program_id),
            "objective_onset_week": c.objective_onset_week,
            "reported_onset_week": c.reported_onset_week,
            "lag_weeks": c.lag_weeks,
            "never_confessed": c.never_confessed,
        })
    return {
        "programs_never_confessed": result.programs_never_confessed,
        "confession_lags": result.confession_lags,
        "max_confession_lag": result.max_confession_lag,
        "per_program": rows,
    }


def main() -> None:
    data = run()
    write(NAME, data)
    print("Confession lag per program")
    print(f"  {'program':<12}{'signals wk':>12}{'report wk':>11}{'lag':>6}  verdict")
    for r in data["per_program"]:
        onset = r["objective_onset_week"] if r["objective_onset_week"] is not None else "-"
        rep = r["reported_onset_week"] if r["reported_onset_week"] is not None else "-"
        verdict = "never confessed" if r["never_confessed"] else (
            f"{r['lag_weeks']}w late" if r["lag_weeks"] > 0 else "on time/conservative"
        )
        print(f"  {r['program_id']:<12}{str(onset):>12}{str(rep):>11}"
              f"{r['lag_weeks']:>6}  {verdict}")
    print(f"  programs that never confessed: {data['programs_never_confessed']}")
    print(f"  longest confession lag: {data['max_confession_lag']} weeks")


if __name__ == "__main__":
    main()
