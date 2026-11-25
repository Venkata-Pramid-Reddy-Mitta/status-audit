"""Record a terminal demo as a replay of real captured output, not a screen recording.

Each command is run for real; its stdout, exit code and wall time are captured. A self-contained
HTML player then types the command and reveals that captured output, paced by the measured
duration, and Playwright records the page to webm, which ffmpeg transcodes to an MP4 and an
autoplaying GIF. Every line on screen is real output. The order is the argument, not the feature
list: the baseline first, then the confession lag, then the number no status report can give
(sensitivity), then the rollup contradiction, then the receipts. The manifest records every
command with its exit code and duration.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IMG = REPO_ROOT / "docs" / "img"
VIDEO = REPO_ROOT / "docs" / "video"

COMMANDS = [
    ["python", "-m", "status_audit.cli", "audit"],
    ["python", "experiments/exp_confession_lag.py"],
    ["python", "experiments/exp_threshold_sensitivity.py"],
    ["python", "experiments/exp_rollup_rule.py"],
    ["python", "tools/check_numbers.py"],
]


def _env() -> dict:
    return {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}


def _capture() -> list[dict]:
    # Warm the import once so the first captured segment does not pay for it.
    subprocess.run(["python", "-c", "import status_audit"], cwd=REPO_ROOT, env=_env(),
                   capture_output=True)
    segments = []
    for cmd in COMMANDS:
        start = time.perf_counter()
        proc = subprocess.run(cmd, cwd=REPO_ROOT, env=_env(), capture_output=True, text=True)
        duration = time.perf_counter() - start
        segments.append({
            "command": " ".join(c if c != "python" else "python" for c in cmd),
            "stdout": proc.stdout.rstrip("\n"),
            "exit_code": proc.returncode,
            "duration_s": round(duration, 3),
        })
    return segments


def _player_html(segments: list[dict]) -> str:
    data = json.dumps(segments)
    return """<!doctype html><html><head><meta charset="utf-8"><style>
    html,body{margin:0;background:#0d1117;}
    #t{font-family:'DejaVu Sans Mono',monospace;font-size:15px;line-height:1.45;
       color:#d7dde3;padding:18px 22px;white-space:pre-wrap;}
    .cmd{color:#7ee787;} .prompt{color:#58a6ff;} .exit0{color:#7ee787;} .exit1{color:#e3b341;}
    </style></head><body><div id="t"></div>
    <script>
    const SEGMENTS = __DATA__;
    const term = document.getElementById('t');
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML;}
    async function type(text){
      const span=document.createElement('span');span.className='cmd';term.appendChild(span);
      for(const ch of text){span.innerHTML+=esc(ch);await sleep(18);}
      term.appendChild(document.createTextNode('\\n'));
    }
    async function run(){
      await sleep(600);  // dark empty terminal hold, so the GIF loop starts clean
      for(const seg of SEGMENTS){
        const p=document.createElement('span');p.className='prompt';p.textContent='$ ';
        term.appendChild(p);
        await type(seg.command);
        const pace=Math.max(250, Math.min(2200, seg.duration_s*1000));
        await sleep(pace);
        const out=document.createElement('span');out.innerHTML=esc(seg.stdout)+'\\n';
        term.appendChild(out);
        const ex=document.createElement('span');
        ex.className=seg.exit_code===0?'exit0':'exit1';
        ex.textContent='[exit '+seg.exit_code+']\\n\\n';
        term.appendChild(ex);
        window.scrollTo(0, document.body.scrollHeight);
        await sleep(700);
      }
      document.title='DEMO_DONE';
    }
    run();
    </script></body></html>""".replace("__DATA__", data)


def _total_ms(segments: list[dict]) -> int:
    total = 0
    for seg in segments:
        total += len(seg["command"]) * 18
        total += max(250, min(2200, int(seg["duration_s"] * 1000)))
        total += 700
    return total + 2600  # includes the 600 ms opening hold plus a tail buffer


def main() -> int:
    from playwright.sync_api import sync_playwright

    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg not found; it is required to build the MP4 and GIF")

    IMG.mkdir(parents=True, exist_ok=True)
    VIDEO.mkdir(parents=True, exist_ok=True)
    segments = _capture()
    player = VIDEO / "player.html"
    player.write_text(_player_html(segments), encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 900, "height": 620},
            record_video_dir=str(VIDEO), record_video_size={"width": 900, "height": 620},
        )
        page = context.new_page()
        page.goto(player.as_uri())
        page.wait_for_timeout(_total_ms(segments))
        webm_page = page
        context.close()  # finalises the webm
        webm = Path(webm_page.video.path())
        browser.close()

    mp4 = VIDEO / "demo.mp4"
    gif = IMG / "demo.gif"
    palette = VIDEO / "palette.png"
    # Skip the browser's initial pre-paint frame (a white flash) so the loop starts on the
    # dark empty terminal.
    trim = ["-ss", "0.3"]
    subprocess.run(["ffmpeg", "-y", *trim, "-i", str(webm), "-movflags", "+faststart",
                    "-pix_fmt", "yuv420p", "-vf", "scale=900:-2", str(mp4)],
                   check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", *trim, "-i", str(webm), "-vf",
                    "fps=10,scale=760:-1:flags=lanczos,palettegen", str(palette)],
                   check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", *trim, "-i", str(webm), "-i", str(palette), "-lavfi",
                    "fps=10,scale=760:-1:flags=lanczos[x];[x][1:v]paletteuse", str(gif)],
                   check=True, capture_output=True)

    (VIDEO / "manifest.json").write_text(
        json.dumps({"segments": segments, "gif": str(gif.relative_to(REPO_ROOT)),
                    "mp4": str(mp4.relative_to(REPO_ROOT))}, indent=2),
        encoding="utf-8",
    )
    webm.unlink(missing_ok=True)
    palette.unlink(missing_ok=True)
    size_mb = gif.stat().st_size / 1e6
    print(f"wrote {gif.relative_to(REPO_ROOT)} ({size_mb:.1f} MB) and {mp4.relative_to(REPO_ROOT)}")
    if size_mb > 5:
        print("warning: GIF exceeds 5 MB; consider fewer frames or a smaller scale")
    return 0


if __name__ == "__main__":
    sys.exit(main())
