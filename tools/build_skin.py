"""Build skins/minecraft.yaml (Voxel Lantern) from src/ + generated pixel art.

    python tools/build_skin.py            # build
    python tools/build_skin.py --install  # build + copy into $HERMES_HOME and activate

Generates:
  skins/minecraft.yaml      the one file Hermes needs (CLI + TUI + desktop)
  docs/island.gif           README preview of the turning island
"""

from __future__ import annotations

import base64
import io
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_pet import SLUG, idle_grid  # noqa: E402
from voxel import render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT, DOCS = ROOT / "src", ROOT / "skins", ROOT / "docs"
CSS_CAP = 32768
HERO_SIZE, HERO_FRAMES = 56, 32
OLD_PETS = ["creeper-buddy"]


def png_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def svg_data_uri(svg: str) -> str:
    svg = re.sub(r">\s+<", "><", svg.strip())
    return "data:image/svg+xml," + quote(svg, safe=" =:/;,'-.()")


def stars_svg() -> str:
    """Static, faint stars that fade out toward the bottom of a 220px band."""
    rng = random.Random(2026)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="480" height="220" shape-rendering="crispEdges">']
    for _ in range(16):
        x, y = rng.randrange(0, 478), int(rng.random() ** 1.8 * 210)
        a = round(0.32 * (1 - y / 230), 2)
        fill = rng.choice(["#ffffff", "#ffffff", "#ffffff", "#f2b36b", "#4fc3a8"])
        s = 2 if rng.random() < 0.8 else 3
        parts.append(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="{fill}" opacity="{a}"/>')
    parts.append("</svg>")
    return "".join(parts)


LOGO = [
    "██╗  ██╗███████╗██████╗ ███╗   ███╗███████╗███████╗",
    "██║  ██║██╔════╝██╔══██╗████╗ ████║██╔════╝██╔════╝",
    "███████║█████╗  ██████╔╝██╔████╔██║█████╗  ███████╗",
    "██╔══██║██╔══╝  ██╔══██╗██║╚██╔╝██║██╔══╝  ╚════██║",
    "██║  ██║███████╗██║  ██║██║ ╚═╝ ██║███████╗███████║",
    "╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝",
]
LOGO_ROW_COLORS = ["#f6c98a", "#f2b36b", "#d9945a", "#a8865c", "#5fae95", "#4fc3a8"]


def banner_logo() -> str:
    lines = [f"[bold {c}]{row}[/]" for row, c in zip(LOGO, LOGO_ROW_COLORS)]
    lines.append("[dim #9a958c]              ▣  voxel lantern edition  ▣[/]")
    return "\n".join(lines)


def banner_hero() -> str:
    """Lantern Buddy in coloured block glyphs (every other row ≈ square cells)."""
    px = idle_grid()
    lines = []
    for y in range(0, 28, 2):
        segs, cur, run = [], None, 0
        for x in list(range(7, 25)) + [None]:
            c = None
            if x is not None:
                p = px.get((x, y)) or px.get((x, y + 1))
                c = "#%02x%02x%02x" % p[:3] if p else None
            if x is not None and c == cur:
                run += 1
                continue
            if run:
                segs.append(f"[{cur}]{'██' * run}[/]" if cur else "  " * run)
            cur, run = c, 1
        lines.append("".join(segs).rstrip())
    lines.append("[dim #f2b36b]      the lamp is lit[/]")
    return "\n".join(lines)


def minify_css(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    return css.replace(";}", "}").strip()


def block_scalar(text: str, indent: str = "  ") -> str:
    # explicit indent indicator: banner art lines may start with spaces
    return "|2-\n" + "\n".join(indent + line if line else "" for line in text.split("\n"))


def build() -> Path:
    OUT.mkdir(exist_ok=True)
    DOCS.mkdir(exist_ok=True)
    frames = render(HERO_SIZE, HERO_FRAMES)
    sheet = Image.new("RGBA", (HERO_SIZE * HERO_FRAMES, HERO_SIZE))
    for i, fr in enumerate(frames):
        sheet.paste(fr, (i * HERO_SIZE, 0))
    sheet_q = sheet.quantize(colors=48, method=Image.Quantize.FASTOCTREE)

    assets = {"png:hero": png_data_uri(sheet_q), "svg:stars": svg_data_uri(stars_svg())}
    css = (SRC / "desktop.css").read_text(encoding="utf-8")
    css = css.replace("{{hero_frames}}", str(HERO_FRAMES)).replace("{{hero_duration}}", "6.4s")
    used = sorted(set(re.findall(r'url\("\{\{([a-z]+:[a-z_]+)\}\}"\)', css)))
    for key in used:
        css = css.replace(f'url("{{{{{key}}}}}")', f"var(--vl-{key.split(':')[1].replace('_', '-')})")
    asset_vars = ":root{" + ";".join(
        f'--vl-{k.split(":")[1].replace("_", "-")}:url("{assets[k]}")' for k in used) + "}"
    css = asset_vars + minify_css(css)
    leftover = re.findall(r"\{\{[^}]+\}\}", css)
    if leftover:
        raise SystemExit(f"unresolved placeholders: {leftover}")
    if len(css.encode()) > CSS_CAP:
        raise SystemExit(f"customCSS is {len(css.encode())} bytes > {CSS_CAP} cap")

    base = (SRC / "skin.base.yaml").read_text(encoding="utf-8").rstrip()
    base = re.sub(r"^#.*\n(#.*\n)*", "", base)
    yaml_text = (
        "# Hermes · Voxel Lantern skin — GENERATED by tools/build_skin.py, edit src/ instead.\n"
        "# https://github.com/XiaoJunX1005/hermes-minecraft-theme\n"
        + base + "\n\n"
        + "banner_logo: " + block_scalar(banner_logo()) + "\n\n"
        + "banner_hero: " + block_scalar(banner_hero()) + "\n\n"
        + "customCSS: " + block_scalar(css) + "\n"
    )
    out = OUT / "minecraft.yaml"
    out.write_text(yaml_text, encoding="utf-8")

    big = [Image.alpha_composite(Image.new("RGBA", (168, 168), (21, 23, 28, 255)),
                                 fr.resize((168, 168), Image.NEAREST)).convert("RGB") for fr in frames]
    strip = Image.new("RGB", (168, 168 * 4))
    for k, i in enumerate((0, 8, 16, 24)):
        strip.paste(big[i], (0, 168 * k))
    pal = strip.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in big]
    q[0].save(DOCS / "island.gif", save_all=True, append_images=q[1:], duration=200, loop=0)

    print(f"wrote {out}  (customCSS {len(css.encode())}/{CSS_CAP} bytes)")
    return out


def hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env)
    local = os.environ.get("LOCALAPPDATA")
    if os.name == "nt" and local and (Path(local) / "hermes").is_dir():
        return Path(local) / "hermes"
    return Path.home() / ".hermes"


def install(skin: Path) -> None:
    home = hermes_home()
    (home / "skins").mkdir(parents=True, exist_ok=True)
    shutil.copy2(skin, home / "skins" / skin.name)
    shutil.copytree(ROOT / "pets" / SLUG, home / "pets" / SLUG, dirs_exist_ok=True)
    for old in OLD_PETS:
        shutil.rmtree(home / "pets" / old, ignore_errors=True)
    subprocess.run(["hermes", "config", "set", "display.skin", "minecraft"], check=False)
    subprocess.run(["hermes", "pets", "select", SLUG], check=False)
    print(f"installed into {home}")


if __name__ == "__main__":
    path = build()
    if "--install" in sys.argv:
        install(path)
