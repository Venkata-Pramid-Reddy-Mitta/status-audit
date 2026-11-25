"""Screenshot the real HTML report, framed by heading, with a legibility check on the badge.

The screenshot is generated from the tool's own report, so a reviewer can regenerate it. Three
rules, each learned from a failure: frame by a named heading rather than a pixel offset (a hard
crop drifts the first time a paragraph grows), pass full_page=True even with a clip (Chromium
clamps a clip to the viewport otherwise), and read the verdict badge's computed colour back and
fail if it is invisible, because a screenshot tool is the only thing in the pipeline that can
see pixels. If the report HTML is missing, it is built first, so the shot is never of stale data.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_HTML = REPO_ROOT / "docs" / "report.html"
OUT_PNG = REPO_ROOT / "docs" / "img" / "report-headline.png"
MANIFEST = REPO_ROOT / "docs" / "img" / "screenshot-manifest.json"


def _ensure_report() -> None:
    import os

    env = {"PYTHONPATH": str(REPO_ROOT / "src")}
    result = subprocess.run(
        [sys.executable, "-m", "status_audit.cli", "audit",
         "--html", str(REPORT_HTML), "--quiet"],
        cwd=REPO_ROOT, env={**os.environ, **env},
    )
    # Exit 1 means the audit ran and found discrepancies, which is the normal case on the
    # committed data; only exit 2 (the tool could not run) is a real failure here.
    if result.returncode == 2:
        raise SystemExit("audit failed to produce the report")


def main() -> int:
    from playwright.sync_api import sync_playwright

    _ensure_report()
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 1200})
        page.goto(REPORT_HTML.as_uri())

        # Frame from the Verdict heading to the Confession lag heading.
        frame = page.evaluate(
            """() => {
                const hs = [...document.querySelectorAll('h2')];
                const start = hs.find(h => h.textContent.includes('Verdict'));
                const end = hs.find(h => h.textContent.includes('Confession lag'));
                if (!start || !end) return null;
                const top = start.getBoundingClientRect().top + window.scrollY - 60;
                const bottom = end.getBoundingClientRect().top + window.scrollY - 20;
                return {top, bottom, width: document.body.scrollWidth};
            }"""
        )
        if frame is None:
            raise SystemExit("expected headings not found; the report changed shape")

        badge = page.evaluate(
            """() => {
                const b = document.querySelector('.badge');
                if (!b) return null;
                const s = getComputedStyle(b);
                return {color: s.color, background: s.backgroundColor,
                        visible: b.offsetWidth > 0 && b.offsetHeight > 0};
            }"""
        )
        if badge is None or not badge["visible"]:
            raise SystemExit("verdict badge is invisible: aborting rather than shipping it")
        if badge["color"] == badge["background"]:
            raise SystemExit(f"verdict badge has no contrast: {badge}")

        page.screenshot(
            path=str(OUT_PNG),
            clip={"x": 0, "y": frame["top"], "width": min(frame["width"], 900),
                  "height": frame["bottom"] - frame["top"]},
            full_page=True,
        )
        browser.close()

    MANIFEST.write_text(
        json.dumps({"image": str(OUT_PNG.relative_to(REPO_ROOT)),
                    "framed_by": ["Verdict", "Confession lag"],
                    "badge": badge}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {OUT_PNG.relative_to(REPO_ROOT)}; "
          f"badge {badge['color']} on {badge['background']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
