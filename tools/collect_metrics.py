"""Re-measure every published figure and write docs/metrics.json. Nothing is typed by hand.

The test count and coverage are read from the machine-readable pytest reports (junit XML and
coverage JSON), not scraped from a progress line, because a scraped line becomes whatever the
last run happened to print. Every other number is produced by running the experiments and
reading their JSON. The anchors dict ships alongside the values so check_numbers.py can guard
the prose. Run the suite as its own step and pass --skip-tests here, or let this script run it.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS = REPO_ROOT / "reports"
sys.path.insert(0, str(REPO_ROOT / "experiments"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import exp_confession_lag  # noqa: E402
import exp_direction_split  # noqa: E402
import exp_headline  # noqa: E402
import exp_rollup_rule  # noqa: E402
import exp_threshold_sensitivity  # noqa: E402


def _run_pytest() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable, "-m", "pytest",
            f"--junitxml={REPORTS / 'junit.xml'}",
            "--cov=status_audit",
            f"--cov-report=json:{REPORTS / 'coverage.json'}",
            "-q",
        ],
        cwd=REPO_ROOT,
        check=True,
        env={**_env()},
    )


def _env() -> dict:
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return env


def _tests_total() -> int:
    tree = ET.parse(REPORTS / "junit.xml")
    root = tree.getroot()
    # The root may be <testsuites> or a single <testsuite>; sum the tests attribute either way.
    suites = root.findall("testsuite") or [root]
    return sum(int(s.get("tests", 0)) for s in suites)


def _coverage_line_pct() -> int:
    data = json.loads((REPORTS / "coverage.json").read_text())
    return round(data["totals"]["percent_covered"])


def collect(skip_tests: bool) -> dict:
    if not skip_tests:
        _run_pytest()

    head = exp_headline.run()
    conf = exp_confession_lag.run()
    sens = exp_threshold_sensitivity.run()
    roll = exp_rollup_rule.run()
    direction = exp_direction_split.run()

    metrics = {
        "tests_total": _tests_total(),
        "coverage_line_pct": _coverage_line_pct(),
        "programs": head["programs"],
        "total_reports": head["total_reports"],
        "workstream_weeks": head["workstream_weeks"],
        "program_weeks": head["program_weeks"],
        "green_over_trouble": head["green_over_trouble_program_weeks"],
        "green_over_red": head["green_over_red_program_weeks"],
        "optimistic_workstream_weeks": head["optimistic_workstream_weeks"],
        "rollup_violations_worst_of": roll["violations_worst_of"],
        "rollup_violations_majority": roll["violations_majority"],
        "max_confession_lag": conf["max_confession_lag"],
        "programs_never_confessed": conf["programs_never_confessed"],
        "headline_robust_floor": sens["headline_at_loosest"],
        "headline_inflated": sens["headline_at_strictest"],
        "pessimistic_program_weeks": direction["program_level"]["pessimistic"],
    }

    anchors = {
        "tests_total": ["{} tests"],
        "coverage_line_pct": ["{}% line and branch coverage"],
        "programs": ["{} programs"],
        "total_reports": ["{} reconciled reports"],
        "workstream_weeks": ["{} at the workstream level"],
        "program_weeks": ["{} at the program level"],
        "green_over_trouble": ["{} program-weeks were reported", "{} green-over-trouble"],
        "green_over_red": ["{} of them Green over Red", "Green over Red in {}"],
        "optimistic_workstream_weeks": ["{} workstream-weeks were optimistic"],
        "rollup_violations_worst_of": ["{} rollup integrity violations"],
        "rollup_violations_majority": ["{} still contradict"],
        "max_confession_lag": ["{}-week confession lag"],
        "programs_never_confessed": ["{} program never confessed"],
        "headline_robust_floor": ["robust floor of {}"],
        "headline_inflated": ["inflates to {}"],
        "pessimistic_program_weeks": ["{} pessimistic program-weeks"],
    }

    return {
        "metrics": metrics,
        "anchors": anchors,
        "checked_documents": [
            "README.md",
            "docs/defense-guide.md",
            "docs/adr/ADR-003-confession-lag-is-signed.md",
            "docs/adr/ADR-005-synthetic-data-and-the-boundary.md",
        ],
        "note": "every value here is produced by running the suite and the experiments",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-measure every published figure.")
    parser.add_argument("--skip-tests", action="store_true",
                        help="read existing reports/junit.xml and reports/coverage.json")
    args = parser.parse_args()
    payload = collect(skip_tests=args.skip_tests)
    out = REPO_ROOT / "docs" / "metrics.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out} with {len(payload['metrics'])} metrics")


if __name__ == "__main__":
    main()
