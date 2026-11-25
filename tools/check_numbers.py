"""Fail the build when a document quotes a figure the code no longer produces.

Two directions. Forward: for every metric and every anchor phrase, if a checked document uses
that phrase, the number in it must equal the measured value, else the build fails on a stale
figure. Reverse: every bare number in the README that matches no metric is reported, so a
figure nothing re-measures cannot hide (code fences, inline code and HTML attributes are
excluded, because an example invocation is allowed to contain a made-up count).

Anchors are matched as "a number plus two or three words", never a whole clause, so a phrase
that wraps across a line in rendered markdown still matches (see references/receipts.md rule 2).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Numbers that legitimately appear in prose and are not audit metrics: policy thresholds,
# the python versions, ADR indices, and structural counts quoted as plain facts.
REVERSE_ALLOWLIST = {
    "0", "1", "2", "3", "4", "5",  # RAG indices, ADR numbers, small structural counts
    "0.85", "0.90", "0.95", "0.975", "1.0", "0.925",  # policy thresholds quoted in prose
    "3.11", "3.12", "3.13",  # python versions
    "2026",  # copyright year
    "100",  # coverage, also allow-listed as a metric value
    "001", "002", "003", "004", "005",  # ADR index labels in links
    # Objective/report onset weeks quoted from exp_confession_lag, and the war-story figure.
    "7", "10", "12", "14", "18", "19",
}


def _anchor_regex(template: str) -> re.Pattern:
    escaped = re.escape(template).replace(r"\{\}", r"(\d+(?:\.\d+)?)")
    return re.compile(escaped)


def _strip_code_and_html(markdown: str) -> str:
    text = re.sub(r"```.*?```", " ", markdown, flags=re.DOTALL)  # fenced code
    text = re.sub(r"`[^`]*`", " ", text)  # inline code
    text = re.sub(r"<[^>]+>", " ", text)  # HTML tags and their attributes
    return text


def check_forward(payload: dict, docs: dict[str, str]) -> tuple[list[str], set[str]]:
    failures: list[str] = []
    referenced: set[str] = set()
    metrics = payload["metrics"]
    anchors = payload["anchors"]
    for name, value in metrics.items():
        value_str = str(value)
        for anchor in anchors.get(name, []):
            pattern = _anchor_regex(anchor)
            for doc_name, text in docs.items():
                for match in pattern.finditer(text):
                    referenced.add(name)
                    found = match.group(1)
                    if found != value_str:
                        failures.append(
                            f"STALE: {doc_name} says '{match.group(0)}' but {name} = {value_str}"
                        )
    return failures, referenced


def check_reverse(metric_values: set[str], readme: str) -> list[str]:
    text = _strip_code_and_html(readme)
    unverified: list[str] = []
    for token in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", text):
        if token in metric_values or token in REVERSE_ALLOWLIST:
            continue
        unverified.append(token)
    return sorted(set(unverified))


def main() -> int:
    payload = json.loads((REPO_ROOT / "docs" / "metrics.json").read_text())
    docs: dict[str, str] = {}
    for rel in payload["checked_documents"]:
        path = REPO_ROOT / rel
        if not path.exists():
            print(f"check_numbers: missing checked document {rel}", file=sys.stderr)
            return 1
        docs[rel] = path.read_text(encoding="utf-8")

    failures, referenced = check_forward(payload, docs)
    gaps = [name for name in payload["metrics"] if name not in referenced]
    metric_values = {str(v) for v in payload["metrics"].values()}
    unverified = check_reverse(metric_values, docs.get("README.md", ""))

    for f in failures:
        print(f)
    if gaps:
        print(f"GAP: metrics produced but not quoted in any checked doc: {gaps}")
    if unverified:
        print(f"NOTE: README numbers matching no metric (verify by eye): {unverified}")

    if failures or gaps:
        print(f"check_numbers: FAIL ({len(failures)} stale, {len(gaps)} gaps)")
        return 1
    print(f"check_numbers: OK ({len(referenced)} metrics verified across {len(docs)} documents)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
