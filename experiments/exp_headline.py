"""Experiment: how much trouble did a green report hide, across the whole portfolio?

Answers the README's first question. Reconciles every reported cell and counts the
program-weeks where the report said Green while the recomputed colour was Amber or Red, split
by how far apart they were.
"""

from __future__ import annotations

from _common import audit, write

NAME = "headline"


def run() -> dict:
    result = audit()
    green_over_red = sum(
        1 for a in result.program_audits if int(a.reported) == 0 and int(a.computed) == 2
    )
    green_over_amber = sum(
        1 for a in result.program_audits if int(a.reported) == 0 and int(a.computed) == 1
    )
    return {
        "total_reports": result.total_reports,
        "workstream_weeks": len(result.workstream_audits),
        "program_weeks": len(result.program_audits),
        "programs": len({a.program_id for a in result.program_audits}),
        "green_over_trouble_program_weeks": result.green_over_trouble_program_weeks,
        "green_over_red_program_weeks": green_over_red,
        "green_over_amber_program_weeks": green_over_amber,
        "optimistic_program_weeks": result.optimistic_program_weeks,
        "optimistic_workstream_weeks": result.optimistic_workstream_weeks,
    }


def main() -> None:
    data = run()
    write(NAME, data)
    print("Headline: green reports over amber/red signals")
    print(f"  reports reconciled                 {data['total_reports']}")
    print(f"  program-weeks Green over trouble   {data['green_over_trouble_program_weeks']}")
    print(f"    of which Green over Red          {data['green_over_red_program_weeks']}")
    print(f"    of which Green over Amber        {data['green_over_amber_program_weeks']}")
    print(f"  optimistic workstream-weeks        {data['optimistic_workstream_weeks']}")


if __name__ == "__main__":
    main()
