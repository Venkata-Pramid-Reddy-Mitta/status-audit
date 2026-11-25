"""Experiment: how much of the headline is the program, and how much is the amber SPI line?

Answers the README's boundary question. Sweeps the single most load-bearing threshold and
reports how the headline count moves, so the reader can see which part of the finding is
robust to the policy and which part is an artefact of where the amber line is drawn.
"""

from __future__ import annotations

from _common import load, write

from status_audit.sensitivity import sweep_amber_spi

NAME = "threshold_sensitivity"
GRID = [0.90, 0.925, 0.95, 0.975, 1.0]


def run() -> dict:
    data, policy = load()
    points = sweep_amber_spi(data, policy, GRID)
    rows = [
        {
            "amber_below_spi": p.amber_below_spi,
            "green_over_trouble_program_weeks": p.green_over_trouble_program_weeks,
            "optimistic_program_weeks": p.optimistic_program_weeks,
        }
        for p in points
    ]
    at_default = next(r for r in rows if r["amber_below_spi"] == policy.amber_below_spi)
    at_strictest = max(rows, key=lambda r: r["amber_below_spi"])
    at_loosest = min(rows, key=lambda r: r["amber_below_spi"])
    return {
        "default_amber_below_spi": policy.amber_below_spi,
        "headline_at_default": at_default["green_over_trouble_program_weeks"],
        "headline_at_strictest": at_strictest["green_over_trouble_program_weeks"],
        "headline_at_loosest": at_loosest["green_over_trouble_program_weeks"],
        "grid": rows,
    }


def main() -> None:
    data = run()
    write(NAME, data)
    print("Threshold sensitivity: amber SPI line vs headline count")
    print(f"  {'amber_spi':>10}{'green-over-trouble':>22}{'optimistic':>14}")
    for r in data["grid"]:
        print(f"  {r['amber_below_spi']:>10.3f}"
              f"{r['green_over_trouble_program_weeks']:>22}"
              f"{r['optimistic_program_weeks']:>14}")
    print(f"  robust floor (loosest line):  {data['headline_at_loosest']}")
    print(f"  inflated (strictest line):    {data['headline_at_strictest']}")


if __name__ == "__main__":
    main()
