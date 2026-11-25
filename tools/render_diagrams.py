"""Render the README's architecture diagram to a committed SVG that GitHub shows reliably.

GitHub's own Mermaid rendering fails intermittently from inside its lazily loaded renderer,
so the diagram is rendered here to a static SVG and embedded with <img src>. Four fixes from
hard-won experience are applied (see references/ci-and-rendering-traps.md traps 7 to 10):
htmlLabels off so the SVG is valid XML and loads as an image, explicit width/height from the
viewBox so a browser has an aspect ratio, a painted light background so edge labels are legible
in a dark theme, and the source kept in a fence labelled mermaid-source so nothing re-renders it.

The mermaid library is an evidence-only dependency, not committed. Provide it via the MERMAID_JS
environment variable or at tools/vendor/mermaid.min.js (npm install mermaid, then copy
node_modules/mermaid/dist/mermaid.min.js there).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_SVG = REPO_ROOT / "docs" / "img" / "architecture.svg"
MANIFEST = REPO_ROOT / "docs" / "img" / "diagram-manifest.json"


def _mermaid_js() -> Path:
    candidate = os.environ.get("MERMAID_JS")
    if candidate and Path(candidate).exists():
        return Path(candidate)
    vendored = REPO_ROOT / "tools" / "vendor" / "mermaid.min.js"
    if vendored.exists():
        return vendored
    raise SystemExit(
        "mermaid.min.js not found. Set MERMAID_JS or run: npm install mermaid "
        "and copy node_modules/mermaid/dist/mermaid.min.js to tools/vendor/mermaid.min.js"
    )


def _extract_source() -> str:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    match = re.search(r"```mermaid-source\n(.*?)```", readme, re.DOTALL)
    if not match:
        raise SystemExit("no ```mermaid-source fence found in README.md")
    return match.group(1).strip()


def _fix_svg(svg: str) -> str:
    # Give the root <svg> intrinsic width/height from its viewBox so it loads as an <img>.
    viewbox = re.search(r'viewBox="([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)"', svg)
    if viewbox:
        width = round(float(viewbox.group(3)))
        height = round(float(viewbox.group(4)))
        svg = re.sub(r'(<svg[^>]*?)\swidth="[^"]*"', r"\1", svg, count=1)
        svg = re.sub(r'(<svg[^>]*?)\sheight="[^"]*"', r"\1", svg, count=1)
        svg = re.sub(r'style="[^"]*max-width:[^"]*"', "", svg, count=1)
        svg = svg.replace("<svg ", f'<svg width="{width}" height="{height}" ', 1)
        # Paint a light background rectangle so dark-theme edge labels stay legible.
        rect = f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>'
        svg = re.sub(r"(<svg[^>]*>)", r"\1" + rect, svg, count=1)
    return svg


def main() -> int:
    from playwright.sync_api import sync_playwright

    source = _extract_source()
    mermaid = _mermaid_js()
    OUT_SVG.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content("<!doctype html><html><body><div id='app'></div></body></html>")
        page.add_script_tag(path=str(mermaid))
        svg = page.evaluate(
            """async (src) => {
                mermaid.initialize({ startOnLoad: false, htmlLabels: false,
                    flowchart: { htmlLabels: false }, securityLevel: 'strict' });
                const { svg } = await mermaid.render('diagram', src);
                return svg;
            }""",
            source,
        )
        browser.close()

    svg = _fix_svg(svg)
    OUT_SVG.write_text(svg, encoding="utf-8")
    MANIFEST.write_text(
        json.dumps({"source_chars": len(source), "svg_bytes": len(svg),
                    "htmlLabels": False, "output": str(OUT_SVG.relative_to(REPO_ROOT))}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {OUT_SVG.relative_to(REPO_ROOT)} ({len(svg)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
