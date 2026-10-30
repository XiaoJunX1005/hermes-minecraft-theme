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
from make_pets import RETIRED, hero_pixels  # noqa: E402
from voxel import render as render_island  # noqa: E402
from blocks import sidebar_tile  # noqa: E402

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


def tex_grass_strip(top_pal=None, sub_pal=None, petals: bool = False) -> Image.Image:
    """32x24 tile: soft turf edge with rounded drips over dark ground (text sits on it)."""
    W, H = 32, 24
    top = grass_top_hd(W, 61, top_pal)
    dirt = dirt_hd(W, 62, pebbles=False, pal=sub_pal)
    edge = value_noise(W, 1, 4, 63)[0]
    rng = random.Random(64)
    out = [[None] * W for _ in range(H)]
    for x in range(W):
        depth = 4 + int(edge[x] * 4)
        for y in range(H):
            if y < depth:
                out[y][x] = top[y][x] if y < depth - 1 else top[0][0] if top_pal is None else (top_pal or ["#4f8f37"])[0]
            else:
                r, g, b = hex_rgb(dirt[y][x])
                k = 0.5 if y == depth else 0.36
                out[y][x] = (int(r * k), int(g * k), int(b * k), 255)
        if top_pal is None:
            out[depth - 1][x] = "#4f8f37"
    if petals:
        for _ in range(9):
            x, y = rng.randrange(W), rng.randrange(3)
            out[y][x] = rng.choice(["#f7b8d2", "#fbd0e2", "#e98fb6"])
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
    px = hero_pixels("creeper")
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
CJK = '"Microsoft JhengHei UI", "Microsoft JhengHei", "PingFang TC", "Noto Sans TC", "Segoe UI", sans-serif'
FONT_IMPORT = f'@font-face{{font-family:"Zpix";src:url("{ZPIX}") format("woff2");font-display:swap}}'
FONT_STACK = f'"Zpix", {CJK}'

ISLAND_SIZE, ISLAND_FRAMES = 48, 24   # shown at 144px (3x)
GRASS_TOP_DEF = None

# skin name -> world settings (all share the Zpix font and the same layout)
WORLDS = {
    "minecraft": dict(label="主世界", biome="overworld", accent="#7bd34a", splash="Also try Minecraft!",
                      star="white", cloud="white", glow="rgba(0, 0, 0, 0.45)", tint="transparent",
                      strip=(None, None, False)),
    "minecraft-nether": dict(label="地獄", biome="nether", accent="#ff6a3d", splash="Also try the Overworld!",
                             star="#ff9a4a", cloud="#ff5a3a", glow="rgba(255, 110, 40, 0.38)", tint="rgba(120, 20, 20, 0.10)",
                             strip=(["#7a1e28", "#8e2430", "#a82c36", "#c23d3f", "#d24a48", "#e05a50"],
                                    ["#4a1a1e", "#5a2024", "#6a282a", "#7a3030", "#8a3838"], False)),
    "minecraft-end": dict(label="終界", biome="end", accent="#c58cff", splash="The End?",
                          star="#e8d8ff", cloud="#b48cff", glow="rgba(200, 120, 255, 0.38)", tint="rgba(60, 20, 90, 0.12)",
                          strip=(["#c9c48a", "#d0cb8e", "#dcd79a", "#e6e2a8", "#ece8b6", "#f2eec0"],
                                 ["#140c1e", "#1d1428", "#22182f", "#2a1e3a", "#31233f"], False)),
    "minecraft-snow": dict(label="雪原", biome="snow", accent="#8fd3ff", splash="Brrr! Bring a coat!",
                           star="white", cloud="white", glow="rgba(140, 200, 255, 0.32)", tint="rgba(120, 170, 220, 0.06)",
                           strip=(["#c8d6e4", "#d6e2ee", "#e2ebf4", "#ecf2f8", "#f4f8fc", "#ffffff"], None, False)),
    "minecraft-cherry": dict(label="櫻花林", biome="cherry", accent="#ff9cc8", splash="Petals everywhere!",
                             star="#ffd6ea", cloud="#ffc0dc", glow="rgba(255, 150, 200, 0.32)", tint="rgba(255, 150, 200, 0.05)",
                             strip=(None, None, True)),
    "minecraft-ocean": dict(label="深海", biome="ocean", accent="#3fd0c8", splash="Just keep swimming!",
                            star="#9fe8ff", cloud="#6ab8d8", glow="rgba(80, 200, 220, 0.34)", tint="rgba(20, 70, 110, 0.14)",
                            strip=(["#c9bc84", "#d2c48e", "#ddd09a", "#e8dca8", "#efe4b4", "#f6ecc2"],
                                   ["#24504c", "#2e6560", "#357069", "#3d7f78", "#4f9a8e"], False)),
    "minecraft-lush": dict(label="繁茂洞穴", biome="lush", accent="#7cd05a", splash="Glow berries!",
                           star="#ffd08a", cloud="#9ad07a", glow="rgba(255, 170, 80, 0.30)", tint="rgba(60, 120, 60, 0.08)",
                           strip=(["#3f7a2a", "#4f8a32", "#5f9d3a", "#6fae46", "#7cba4a", "#8ac85a"],
                                  ["#5a606a", "#6a707a", "#7a808a", "#8a909a", "#9aa0aa"], False)),
    "minecraft-desert": dict(label="沙漠", biome="desert", accent="#e8c070", splash="Mind the cactus.",
                             star="#fff0c0", cloud="#f0d090", glow="rgba(255, 200, 110, 0.32)", tint="rgba(200, 160, 80, 0.08)",
                             strip=(["#c8b070", "#d6c088", "#ddca8e", "#e8d8a0", "#f0e2b0", "#f6ecc4"],
                                    ["#a88a5a", "#b89a68", "#c4a870", "#cbb27a", "#d8c088"], False)),
    "minecraft-mushroom": dict(label="蘑菇島", biome="mushroom", accent="#d070a0", splash="Moo!",
                               star="#f0d8ff", cloud="#c8a8d8", glow="rgba(220, 120, 180, 0.30)", tint="rgba(140, 90, 150, 0.08)",
                               strip=(["#5e5070", "#6e6080", "#7a6a88", "#8a7a98", "#9a8aa8", "#aa9ab8"], None, False)),
    "minecraft-deepdark": dict(label="深暗之域", biome="deepdark", accent="#2fd8e8", splash="Shhh... sneak.",
                               star="#6ff0ff", cloud="#2a6a7a", glow="rgba(40, 220, 230, 0.30)", tint="rgba(10, 40, 60, 0.18)",
                               strip=(["#081e24", "#0c2a34", "#0f3a44", "#12485a", "#1a5a6a", "#20d0e0"],
                                      ["#14161b", "#1a1d23", "#20242b", "#262a32", "#2c3038"], False)),
}
OLD_SKINS = ["minecraft-cubic", "minecraft-mixed", "minecraft-pixelify"]


def sheet_uri(frames: list[Image.Image], colors: int) -> str:
    w, h = frames[0].size
    sheet = Image.new("RGBA", (w * len(frames), h))
    for k, fr in enumerate(frames):
        sheet.paste(fr, (k * w, 0))
    return png_data_uri(sheet.quantize(colors=colors, method=Image.Quantize.FASTOCTREE))


def build() -> Path:
    OUT.mkdir(exist_ok=True)
    DOCS.mkdir(exist_ok=True)
    from make_icons import ICONS, atlas, F as THINK_F, S as THINK_S
    think = atlas()
    think_rows = "".join(
        f'[data-slot="aui_message-group"]:nth-child({len(ICONS)}n+{k + 1}) [data-slot="aui_response-loading"]::before'
        f'{{background-position-y:-{k * THINK_S * 2}px}}' for k in range(1, len(ICONS)))
    common = {
        "png:noise": png_data_uri(tex_noise()),
        "png:stone": png_data_uri(tex_stone()),
        "png:think": png_data_uri(think.quantize(colors=96, method=Image.Quantize.FASTOCTREE)),
    }
    src_css = (SRC / "desktop.css").read_text(encoding="utf-8")
    base_yaml = (SRC / "skin.base.yaml").read_text(encoding="utf-8").rstrip()
    base_yaml = re.sub(r"^#.*\n(#.*\n)*", "", base_yaml)
    hero, logo = banner_hero(), banner_logo()
    islands = {}
    for name, w in WORLDS.items():
        fr = render_island(ISLAND_SIZE, ISLAND_FRAMES, w["biome"])
        islands[name] = fr
        top_pal, sub_pal, petals = w["strip"]
        assets = dict(common, **{
            "png:island": sheet_uri(fr, 48),
            "png:grass_strip": png_data_uri(tex_grass_strip(top_pal, sub_pal, petals)),
            "png:sidebar": png_data_uri(sidebar_tile(w["biome"])),
            "svg:stars": svg_data_uri(stars_svg().replace('fill="white"', f'fill="{w["star"]}"')),
            "svg:clouds": svg_data_uri(clouds_svg().replace('fill="white"', f'fill="{w["cloud"]}"')),
        })
        css = src_css
        for k, v in {"font_import": FONT_IMPORT, "font_stack": FONT_STACK, "think_rows": think_rows,
                     "think_h": str(len(ICONS) * THINK_S * 2), "island_frames": str(ISLAND_FRAMES),
                     "island_duration": f"{ISLAND_FRAMES * 0.2:.1f}s", "splash": w["splash"],
                     "hero_glow": w["glow"], "sky_tint": w["tint"], "accent": w["accent"], "world": w["biome"]}.items():
            css = css.replace("{{" + k + "}}", v)
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
        body = re.sub(r'^description: "(.*)"$', lambda m: f'description: "{m.group(1)} · {w["label"]}"', body, count=1, flags=re.M)
        for key in ("ui_accent", "banner_accent", "input_rule"):
            body = re.sub(rf'^(  {key}: )"#[0-9a-fA-F]{{6}}"', rf'\1"{w["accent"]}"', body, count=1, flags=re.M)
        yaml_text = (
            "# Hermes × Minecraft skin — GENERATED by tools/build_skin.py, edit src/ instead.\n"
            "# https://github.com/XiaoJunX1005/hermes-minecraft-theme\n"
            + body + "\n\n"
            + "banner_logo: " + block_scalar(logo) + "\n\n"
            + "banner_hero: " + block_scalar(hero) + "\n\n"
            + "customCSS: " + block_scalar(css) + "\n"
        )
        (OUT / f"{name}.yaml").write_text(yaml_text, encoding="utf-8")
        print(f"wrote skins/{name}.yaml  (customCSS {len(css.encode())}/{CSS_CAP} bytes) — {w['label']}")
    for old in OLD_SKINS:
        (OUT / f"{old}.yaml").unlink(missing_ok=True)

    # README previews
    big = [Image.alpha_composite(Image.new("RGBA", (112, 112), (23, 25, 31, 255)),
                                 fr.resize((112, 112), Image.NEAREST)).convert("RGB") for fr in spin_frames(56, SPIN_FRAMES)] * 4
    gpal = big[0].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    q = [im.quantize(palette=gpal, dither=Image.Dither.NONE) for im in big]
    q[0].save(DOCS / "grass-block.gif", save_all=True, append_images=q[1:], duration=200, loop=0)
    cell = ISLAND_SIZE * 3
    gif = []
    for f in range(ISLAND_FRAMES):
        c = Image.new("RGBA", (cell * len(WORLDS), cell), (21, 23, 28, 255))
        for k, fr in enumerate(islands.values()):
            c.alpha_composite(fr[f].resize((cell, cell), Image.NEAREST), (k * cell, 0))
        gif.append(c.convert("RGB"))
    strip = Image.new("RGB", (gif[0].width, gif[0].height * 3))
    for k, f in enumerate((0, 8, 16)):
        strip.paste(gif[f], (0, gif[0].height * k))
    pal = strip.quantize(colors=200, method=Image.Quantize.MEDIANCUT)
    q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in gif]
    q[0].save(DOCS / "islands.gif", save_all=True, append_images=q[1:], duration=200, loop=0)
    z = 4  # thinking icons preview, 4x
    tg = []
    for f in range(THINK_F):
        c = Image.new("RGBA", (len(ICONS) * (THINK_S + 4) * z, (THINK_S + 4) * z), (24, 26, 32, 255))
        for k in range(len(ICONS)):
            cell = think.crop((f * THINK_S, k * THINK_S, (f + 1) * THINK_S, (k + 1) * THINK_S))
            c.alpha_composite(cell.resize((THINK_S * z, THINK_S * z), Image.NEAREST), (k * (THINK_S + 4) * z + 2 * z, 2 * z))
        tg.append(c.convert("RGB"))
    tp = tg[0].quantize(colors=160, method=Image.Quantize.MEDIANCUT)
    tq = [im.quantize(palette=tp, dither=Image.Dither.NONE) for im in tg]
    tq[0].save(DOCS / "thinking.gif", save_all=True, append_images=tq[1:], duration=150, loop=0)
    return OUT / "minecraft.yaml"


def hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env)
    local = os.environ.get("LOCALAPPDATA")
    if os.name == "nt" and local and (Path(local) / "hermes").is_dir():
        return Path(local) / "hermes"
    return Path.home() / ".hermes"


def _cfg(key: str) -> str:
    r = subprocess.run(["hermes", "config", "get", key], capture_output=True, text=True)
    lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
    return lines[-1] if lines else ""


def install(skin: Path, skin_name: str | None = None, pet: str | None = None) -> None:
    """Copy every world skin + all pets; drop the retired font-variant skins."""
    home = hermes_home()
    (home / "skins").mkdir(parents=True, exist_ok=True)
    for name in WORLDS:
        shutil.copy2(OUT / f"{name}.yaml", home / "skins" / f"{name}.yaml")
    for old in OLD_SKINS:
        (home / "skins" / f"{old}.yaml").unlink(missing_ok=True)
    for plug in sorted((ROOT / "desktop-plugins").glob("*/plugin.js")):
        dest = home / "desktop-plugins" / plug.parent.name
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(plug, dest / "plugin.js")
    cur_skin, cur_pet = _cfg("display.skin"), _cfg("display.pet.slug")  # read before old pets disappear
    for d in sorted((ROOT / "pets").iterdir()):
        if d.is_dir():
            shutil.copytree(d, home / "pets" / d.name, dirs_exist_ok=True)
    skin_name = skin_name or (cur_skin if cur_skin in WORLDS else "minecraft")
    want = RETIRED.get(cur_pet, cur_pet)
    pet = RETIRED.get(pet, pet) if pet else None
    pet = pet or (want if want and (home / "pets" / want).is_dir() else "creeper")
    if skin_name != cur_skin:
        subprocess.run(["hermes", "config", "set", "display.skin", skin_name], check=False)
    if pet != cur_pet:
        subprocess.run(["hermes", "pets", "select", pet], check=False)
    for old in RETIRED:  # pets from older versions of this project only, after the new one is selected
        shutil.rmtree(home / "pets" / old, ignore_errors=True)
    print(f"skin={skin_name} pet={pet}")
    print(f"installed into {home}")


if __name__ == "__main__":
    path = build()
    if "--install" in sys.argv:
        arg = lambda k: next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{k}=")), None)  # noqa: E731
        install(path, arg("skin"), arg("pet"))
