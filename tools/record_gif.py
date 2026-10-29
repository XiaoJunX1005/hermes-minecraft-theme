"""Record docs/preview.gif from docs/preview.html with headless Chrome.

Each frame is a fresh headless screenshot of preview.html#t=<ms>; a tiny script
in the page pauses every CSS animation at that time, so frames are exact.

    python tools/record_gif.py [path-to-chrome]
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
FRAMES, STEP_MS, SIZE = 24, 200, (1100, 680)

CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_chrome() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    for c in CANDIDATES:
        if Path(c).is_file() or shutil.which(c):
            return c
    raise SystemExit("Chrome/Edge not found; pass its path as an argument")


def main() -> None:
    chrome = find_chrome()
    page = (ROOT / "docs" / "preview.html").resolve().as_uri()
    tmp = Path(tempfile.mkdtemp(prefix="mcgif-"))

    def shot(i: int) -> Path:
        out = tmp / f"f{i:03d}.png"
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--window-size={SIZE[0]},{SIZE[1]}", "--virtual-time-budget=3000",
                        f"--user-data-dir={tmp / f'p{i}'}", f"--screenshot={out}",
                        f"{page}#t={i * STEP_MS}"], capture_output=True, timeout=60)
        return out

    with ThreadPoolExecutor(6) as pool:
        paths = list(pool.map(shot, range(FRAMES)))
    ims = [Image.open(p).convert("RGB").resize((880, 544), Image.LANCZOS) for p in paths]
    # one shared palette sampled from several frames so every colour that appears mid-loop survives
    strip = Image.new("RGB", (880, 544 * 4))
    for k, i in enumerate((0, FRAMES // 4, FRAMES // 2, 3 * FRAMES // 4 + 2)):
        strip.paste(ims[i], (0, 544 * k))
    pal = strip.quantize(colors=220, method=Image.Quantize.MEDIANCUT)
    q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in ims]
    out = ROOT / "docs" / "preview.gif"
    q[0].save(out, save_all=True, append_images=q[1:], duration=STEP_MS, loop=0, optimize=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print("wrote", out, f"({out.stat().st_size // 1024} KiB, {len(q)} frames)")


if __name__ == "__main__":
    main()
