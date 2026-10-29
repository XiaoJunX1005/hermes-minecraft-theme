"""Build skins/minecraft.yaml from src/ (palette + CSS) and generated pixel art.

    python tools/build_skin.py            # build
    python tools/build_skin.py --install  # build + copy into $HERMES_HOME and activate

Generates:
  skins/minecraft.yaml          the one file Hermes needs (CLI + TUI + desktop)
  docs/grass-block.gif          README preview of the spinning block
"""

from __future__ import annotations

import base64
import io
import math
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
from pixels import DIRT, dirt_hd, grass_side_hd, grass_top_hd, noise_texture, value_noise  # noqa: E402,F401
from make_creeper import head_pixels  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT, DOCS = ROOT / "src", ROOT / "skins", ROOT / "docs"
CSS_CAP = 32768

SPIN_FRAMES = 8          # frames per 90° (a grass block looks identical every 90°)
SPIN_SIZE = 56          # rendered from 32x32 textures, shown at 112px (2x)


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def grid_png(grid: list[list[str | tuple]], alpha: int = 255) -> Image.Image:
    h, w = len(grid), len(grid[0])
    img = Image.new("RGBA", (w, h))
    for y in range(h):
        for x in range(w):
            c = grid[y][x]
            img.putpixel((x, y), c if isinstance(c, tuple) else hex_rgb(c) + (alpha,))
    return img


def png_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def svg_data_uri(svg: str) -> str:
    svg = re.sub(r">\s+<", "><", svg.strip())
    return "data:image/svg+xml," + quote(svg, safe=" =:/;,'-.()")


# --- textures ----------------------------------------------------------------------

def tex_noise() -> Image.Image:
    rng = random.Random(42)
    img = Image.new("RGBA", (16, 16))
    for y in range(16):
        for x in range(16):
            v = rng.random()
            img.putpixel((x, y), (255, 255, 255, 10) if v < 0.25 else (0, 0, 0, 26) if v < 0.5 else (0, 0, 0, 0))
    return img


def tex_stone() -> Image.Image:
    return grid_png(noise_texture(16, 16, ["#8f8f8f", "#7f7f7f", "#747474", "#686868", "#5c5c5c"], 5, [1, 3, 4, 3, 1]))


def tex_grass_strip() -> Image.Image:
    """32x24 tile: soft turf edge with rounded drips over dark dirt (text sits on the dirt)."""
    W, H = 32, 24
    top = grass_top_hd(W, 61)
    dirt = dirt_hd(W, 62, pebbles=False)
    edge = value_noise(W, 1, 4, 63)[0]
    out = []
    for y in range(H):
        out.append([None] * W)
    for x in range(W):
        depth = 4 + int(edge[x] * 4)
        for y in range(H):
            if y < depth:
                out[y][x] = top[y][x] if y < depth - 1 else "#4f8f37"
            else:
                r, g, b = hex_rgb(dirt[y][x])
                k = 0.5 if y == depth else 0.36
                out[y][x] = (int(r * k), int(g * k), int(b * k), 255)
    return grid_png(out)


# --- spinning grass block (tiny orthographic ray caster) --------------------------

def spin_frames(size: int = SPIN_SIZE, frames: int = SPIN_FRAMES) -> list[Image.Image]:
    T = 32
    top = grass_top_hd(T, 21)
    side = grass_side_hd(T, 3)
    bottom = dirt_hd(T, 23)
    pitch = math.radians(28)
    out = []
    for f in range(frames):
        yaw = math.radians(45 + 90 * f / frames)
        cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        R = 1.78
        for py in range(size):
            for px in range(size):
                u = (px + 0.5) / size * 2 * R - R
                v = R - (py + 0.5) / size * 2 * R
                # camera-space ray (u, v, +inf) -> dir (0,0,-1); undo pitch (X) then yaw (Y)
                ox, oy, oz = u, v, 5.0
                dx, dy, dz = 0.0, 0.0, -1.0
                oy, oz = oy * cp + oz * sp, -oy * sp + oz * cp
                dy, dz = dy * cp + dz * sp, -dy * sp + dz * cp
                ox, oz = ox * cy - oz * sy, ox * sy + oz * cy
                dx, dz = dx * cy - dz * sy, dx * sy + dz * cy
                tmin, tmax, axis = -1e9, 1e9, -1
                ok = True
                for i, (o, d) in enumerate(((ox, dx), (oy, dy), (oz, dz))):
                    if abs(d) < 1e-9:
                        if abs(o) > 1:
                            ok = False
                        continue
                    t1, t2 = (-1 - o) / d, (1 - o) / d
                    if t1 > t2:
                        t1, t2 = t2, t1
                    if t1 > tmin:
                        tmin, axis = t1, i
                    tmax = min(tmax, t2)
                if not ok or tmin > tmax or axis < 0:
                    continue
                hx, hy, hz = ox + dx * tmin, oy + dy * tmin, oz + dz * tmin
                clamp = lambda a: min(T - 1, max(0, int((a + 1) / 2 * T)))  # noqa: E731
                if axis == 1:
                    tex, tu, tv, light = (top, clamp(hx), clamp(hz), 1.0) if hy > 0 else (bottom, clamp(hx), clamp(hz), 0.5)
                elif axis == 0:
                    tex, tu, tv = side, clamp(hz if hx > 0 else -hz), clamp(-hy)
                    light = 0.62 + 0.18 * abs(math.cos(yaw))
                else:
                    tex, tu, tv = side, clamp(-hx if hz > 0 else hx), clamp(-hy)
                    light = 0.62 + 0.18 * abs(math.sin(yaw))
                r, g, b = hex_rgb(tex[tv][tu])
                img.putpixel((px, py), (int(r * light), int(g * light), int(b * light), 255))
        out.append(img)
    return out


# --- sky ---------------------------------------------------------------------------

def stars_svg() -> str:
    rng = random.Random(1337)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="420" height="300" shape-rendering="crispEdges">']
    for i in range(22):
        x, y, s = rng.randrange(0, 418), rng.randrange(0, 298), rng.choice((2, 2, 3))
        a = rng.choice((0.35, 0.5, 0.7))
        if i % 2:
            dur, beg = rng.uniform(2.5, 6), rng.uniform(0, 5)
            parts.append(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="white" opacity="{a}">'
                         f'<animate attributeName="opacity" values="{a};0.05;{a}" dur="{dur:.1f}s" begin="-{beg:.1f}s" repeatCount="indefinite"/></rect>')
        else:
            parts.append(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="white" opacity="{a * 0.6:.2f}"/>')
    parts.append("</svg>")
    return "".join(parts)


def clouds_svg() -> str:
    # blocky Minecraft clouds: unions of axis-aligned rectangles
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="72" shape-rendering="crispEdges">'
            '<g fill="white" opacity="0.05">'
            '<rect x="40" y="16" width="120" height="24"/><rect x="72" y="4" width="64" height="12"/><rect x="24" y="28" width="168" height="16"/>'
            '<rect x="360" y="32" width="96" height="20"/><rect x="384" y="20" width="56" height="12"/><rect x="340" y="44" width="140" height="12"/>'
            '</g></svg>')


# --- CLI banner art ----------------------------------------------------------------

LOGO = [
    "██╗  ██╗███████╗██████╗ ███╗   ███╗███████╗███████╗",
    "██║  ██║██╔════╝██╔══██╗████╗ ████║██╔════╝██╔════╝",
    "███████║█████╗  ██████╔╝██╔████╔██║█████╗  ███████╗",
    "██╔══██║██╔══╝  ██╔══██╗██║╚██╔╝██║██╔══╝  ╚════██║",
    "██║  ██║███████╗██║  ██║██║ ╚═╝ ██║███████╗███████║",
    "╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝",
]
LOGO_ROW_COLORS = ["#8ad45c", "#6bb545", "#9b6b43", "#86593a", "#7a4f2e", "#7f7f7f"]


def banner_logo() -> str:
    lines = [f"[bold {c}]{row}[/]" for row, c in zip(LOGO, LOGO_ROW_COLORS)]
    lines.append("[dim #a0a0a0]          ⛏  m i n e c r a f t   e d i t i o n  ⛏[/]")
    return "\n".join(lines)


def banner_hero() -> str:
    px = head_pixels()
    lines = []
    for y in range(3, 49, 2):
        segs, cur, run = [], None, 0
        for x in list(range(9, 41, 2)) + [None]:
            c = None
            if x is not None:
                p = px.get((x, y)) or px.get((x + 1, y))
                c = "#%02x%02x%02x" % p[:3] if p else None
            if x is not None and c == cur:
                run += 1
                continue
            if run:
                segs.append(f"[{cur}]{'██' * run}[/]" if cur else "  " * run)
            cur, run = c, 1
        line = "".join(segs).rstrip()
        if line:
            lines.append(line)
    lines.append("[dim #7bd34a]   ssss... boom?[/]")
    return "\n".join(lines)


# --- assemble ----------------------------------------------------------------------

def minify_css(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    css = css.replace(";}", "}")
    return css.strip()


def block_scalar(text: str, indent: str = "  ") -> str:
    # explicit indent indicator: banner art lines may start with spaces
    return "|2-\n" + "\n".join(indent + line if line else "" for line in text.split("\n"))


ZPIX = "https://cdn.jsdelivr.net/gh/SolidZORO/zpix-pixel-font/website/zpix.woff2"
CUBIC = "https://cdn.jsdelivr.net/gh/ACh-K/Cubic-11@main/fonts/web/Cubic_11.woff2"
PIXELIFY = "https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@400..700&display=swap"
CJK = '"Microsoft JhengHei UI", "Microsoft JhengHei", "PingFang TC", "Noto Sans TC", "Segoe UI", sans-serif'
LATIN = "U+0000-024F, U+2000-206F, U+20A0-20CF, U+2100-214F"

# skin name -> (label, font import CSS, --mc-font stack)
FONTS = {
    "minecraft": ("Zpix 全像素", f'@font-face{{font-family:"Zpix";src:url("{ZPIX}") format("woff2");font-display:swap}}',
                  f'"Zpix", {CJK}'),
    "minecraft-cubic": ("俐方體 11 號 全像素", f'@font-face{{font-family:"Cubic 11";src:url("{CUBIC}") format("woff2");font-display:swap}}',
                        f'"Cubic 11", {CJK}'),
    "minecraft-mixed": ("英數 Zpix 像素 + 中文正黑體",
                        f'@font-face{{font-family:"Zpix Latin";src:url("{ZPIX}") format("woff2");font-display:swap;unicode-range:{LATIN}}}',
                        f'"Zpix Latin", {CJK}'),
    "minecraft-pixelify": ("Pixelify Sans + 正黑體（初版）", f'@import url("{PIXELIFY}");', f'"Pixelify Sans", {CJK}'),
}


def build() -> Path:
    OUT.mkdir(exist_ok=True)
    DOCS.mkdir(exist_ok=True)
    frames = spin_frames()
    sheet = Image.new("RGBA", (SPIN_SIZE * SPIN_FRAMES, SPIN_SIZE))
    for i, fr in enumerate(frames):
        sheet.paste(fr, (i * SPIN_SIZE, 0))
    sheet_q = sheet.quantize(colors=64, method=Image.Quantize.FASTOCTREE)

    assets = {
        "png:noise": png_data_uri(tex_noise()),
        "png:stone": png_data_uri(tex_stone()),
        "png:grass_strip": png_data_uri(tex_grass_strip()),
        "png:spin": png_data_uri(sheet_q),
        "svg:stars": svg_data_uri(stars_svg()),
        "svg:clouds": svg_data_uri(clouds_svg()),
    }
    src_css = (SRC / "desktop.css").read_text(encoding="utf-8")
    base_yaml = (SRC / "skin.base.yaml").read_text(encoding="utf-8").rstrip()
    base_yaml = re.sub(r"^#.*\n(#.*\n)*", "", base_yaml)
    hero, logo = banner_hero(), banner_logo()
    out = OUT / "minecraft.yaml"
    for name, (label, font_import, stack) in FONTS.items():
        css = (src_css.replace("{{font_import}}", font_import).replace("{{font_stack}}", stack)
               .replace("{{spin_frames}}", str(SPIN_FRAMES))
               .replace("{{spin_duration}}", "1.6s")
               .replace("{{spin_duration_fast}}", "0.7s"))
        used = sorted(set(re.findall(r'url\("\{\{([a-z]+:[a-z_]+)\}\}"\)', css)))
        for key in used:
            css = css.replace(f'url("{{{{{key}}}}}")', f"var(--mc-{key.split(':')[1].replace('_', '-')})")
        asset_vars = ":root{" + ";".join(f'--mc-{k.split(":")[1].replace("_", "-")}:url("{assets[k]}")' for k in used) + "}"
        css = minify_css(css)
        imports = re.findall(r"@import[^;]+;", css)
        css = "".join(imports) + asset_vars + re.sub(r"@import[^;]+;", "", css)
        leftover = re.findall(r"\{\{[^}]+\}\}", css)
        if leftover:
            raise SystemExit(f"unresolved placeholders: {leftover}")
        if len(css.encode()) > CSS_CAP:
            raise SystemExit(f"{name}: customCSS is {len(css.encode())} bytes > {CSS_CAP} cap")
        body = re.sub(r"^name: .*$", f"name: {name}", base_yaml, count=1, flags=re.M)
        body = re.sub(r'^description: "(.*)"$', lambda m: f'description: "{m.group(1)} · 字型：{label}"', body, count=1, flags=re.M)
        yaml_text = (
            "# Hermes × Minecraft skin — GENERATED by tools/build_skin.py, edit src/ instead.\n"
            "# https://github.com/XiaoJunX1005/hermes-minecraft-theme\n"
            + body + "\n\n"
            + "banner_logo: " + block_scalar(logo) + "\n\n"
            + "banner_hero: " + block_scalar(hero) + "\n\n"
            + "customCSS: " + block_scalar(css) + "\n"
        )
        (OUT / f"{name}.yaml").write_text(yaml_text, encoding="utf-8")
        print(f"wrote skins/{name}.yaml  (customCSS {len(css.encode())}/{CSS_CAP} bytes) — {label}")

    big = [Image.alpha_composite(Image.new("RGBA", (112, 112), (23, 25, 31, 255)),
                                 fr.resize((112, 112), Image.NEAREST)).convert("RGB") for fr in frames] * 4
    gpal = big[0].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    pal = [im.quantize(palette=gpal, dither=Image.Dither.NONE) for im in big]
    pal[0].save(DOCS / "grass-block.gif", save_all=True, append_images=pal[1:], duration=200, loop=0)

    return out


def hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env)
    local = os.environ.get("LOCALAPPDATA")
    if os.name == "nt" and local and (Path(local) / "hermes").is_dir():
        return Path(local) / "hermes"
    return Path.home() / ".hermes"


def install(skin: Path, skin_name: str = "minecraft") -> None:
    """Copy every skin variant + both pets; keep anything else the user has installed."""
    home = hermes_home()
    (home / "skins").mkdir(parents=True, exist_ok=True)
    for name in FONTS:
        shutil.copy2(OUT / f"{name}.yaml", home / "skins" / f"{name}.yaml")
    for slug in ("creeper-buddy", "lantern-buddy"):
        if (ROOT / "pets" / slug).is_dir():
            shutil.copytree(ROOT / "pets" / slug, home / "pets" / slug, dirs_exist_ok=True)
    subprocess.run(["hermes", "config", "set", "display.skin", skin_name], check=False)
    subprocess.run(["hermes", "pets", "select", "creeper-buddy"], check=False)
    print(f"installed into {home}")


if __name__ == "__main__":
    path = build()
    if "--install" in sys.argv:
        pick = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--skin=")), "minecraft")
        install(path, pick)
