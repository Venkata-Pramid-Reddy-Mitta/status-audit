"""The command line: one entry point, exit codes that a pipeline can branch on.

The exit code is the product here, not the printed table. A CI step that runs this needs to
tell three outcomes apart: the audit ran and the reporting was trustworthy (0), the audit ran
and found optimistic misreporting over budget (1), and the audit could not run at all (2). The
middle case is the whole reason the tool exists, so it has its own code rather than being
folded into "error"; conflating "the answer is no" with "I could not compute an answer" is the
mistake that makes a gate useless.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .audit import run_audit
from .config import PolicyError, load_policy
from .generate import write_fixtures
from .loader import DataError, load_status_data
from .report import render_html, render_json, render_text

EXIT_OK = 0  # audit ran, reporting within the policy's optimism budget
EXIT_FINDINGS = 1  # audit ran, optimistic misreporting over budget was found
EXIT_ERROR = 2  # the audit could not run (bad data, bad policy, missing file)

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="status-audit",
        description="Recompute program RAG from objective signals and reconcile it.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("audit", help="run the audit over a data directory")
    audit.add_argument("--data", type=Path, default=_REPO_ROOT / "data",
                       help="directory holding the three status CSVs")
    audit.add_argument("--policy", type=Path, default=_REPO_ROOT / "policy.toml",
                       help="policy TOML file")
    audit.add_argument("--html", type=Path, default=None, help="also write an HTML report here")
    audit.add_argument("--json", type=Path, default=None, help="also write the JSON record here")
    audit.add_argument("--quiet", action="store_true", help="suppress the terminal report")

    gen = sub.add_parser("generate", help="regenerate the committed CSV fixtures")
    gen.add_argument("--data", type=Path, default=_REPO_ROOT / "data")
    gen.add_argument("--seed", type=int, default=None)
    return parser


def _run_audit(args: argparse.Namespace, out=None, err=None) -> int:
    # Resolve the streams at call time, not at import time: a default of sys.stdout in the
    # signature binds the stream that existed when the module was imported, which is not the
    # stream a test (or a caller that redirects) has swapped in.
    out = sys.stdout if out is None else out
    err = sys.stderr if err is None else err
    try:
        data = load_status_data(args.data)
        policy = load_policy(args.policy)
    except (DataError, PolicyError) as exc:
        print(f"status-audit: {exc}", file=err)
        return EXIT_ERROR

    result = run_audit(data, policy)

    if args.html is not None:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(render_html(result), encoding="utf-8")
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(render_json(result), encoding="utf-8")

    if not args.quiet:
        print(render_text(result), file=out)

    return EXIT_OK if result.gate_passed() else EXIT_FINDINGS


def _run_generate(args: argparse.Namespace, out=None) -> int:
    out = sys.stdout if out is None else out
    seed_kwargs = {} if args.seed is None else {"seed": args.seed}
    write_fixtures(args.data, **seed_kwargs)
    print(f"status-audit: wrote fixtures to {args.data}", file=out)
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch. Returns the process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "audit":
        return _run_audit(args)
    if args.command == "generate":
        return _run_generate(args)
    parser.error(f"unknown command: {args.command}")  # pragma: no cover
    return EXIT_ERROR  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
