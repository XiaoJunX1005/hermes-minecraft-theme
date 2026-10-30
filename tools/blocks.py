"""Per-world sidebar tiles: each world's signature block, 16x16, darkened for readable text.

Run:  python tools/blocks.py      -> C:/.../scratch preview (tools only; build_skin imports sidebar_tile)
"""

from __future__ import annotations

import random

from PIL import Image

RGB = tuple[int, int, int]
N = 16


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def _pick(r: random.Random, pal: list[RGB], w: list[int] | None = None) -> RGB:
    return r.choices(pal, weights=w or [1] * len(pal))[0]


def planks(pal: list[RGB], seam: RGB, seed: int) -> list[list[RGB]]:
    """Four planks, 4 px tall, dark seam under each, one end joint per plank, grain streaks."""
    r = _rng(seed)
    g = [[pal[0]] * N for _ in range(N)]
    for p in range(4):
        base = pal[(p * 2 + 1) % len(pal)]
        joint = (p * 5 + 3) % N
        for y in range(p * 4, p * 4 + 4):
            for x in range(N):
                c = base if r.random() < 0.7 else _pick(r, pal)
                if y == p * 4 + 3:
                    c = seam
                elif x == joint:
                    c = seam
                g[y][x] = c
        for _ in range(2):  # grain streak
            y, x0 = p * 4 + r.randint(0, 2), r.randint(0, N - 5)
            for x in range(x0, x0 + r.randint(3, 6)):
                if x < N and x != joint:
                    g[y][x] = pal[-1]
    return g


def bricks(pal: list[RGB], mortar: RGB, seed: int, bw: int = 8, bh: int = 4) -> list[list[RGB]]:
    r = _rng(seed)
    g = [[mortar] * N for _ in range(N)]
    for y in range(N):
        row, yy = y // bh, y % bh
        off = (bw // 2) if row % 2 else 0
        for x in range(N):
            xx = (x + off) % bw
            if yy == bh - 1 or xx == bw - 1:
                continue
            c = _pick(r, pal, [3, 2, 1][: len(pal)] + [1] * max(0, len(pal) - 3))
            if yy == 0:
                c = pal[-1] if r.random() < 0.6 else c
            g[y][x] = c
    return g


def speckle(pal: list[RGB], seed: int, w: list[int] | None = None) -> list[list[RGB]]:
    r = _rng(seed)
    return [[_pick(r, pal, w) for _ in range(N)] for _ in range(N)]


def bands(pal: list[RGB], seed: int) -> list[list[RGB]]:
    """Sandstone: smooth horizontal strata (light / mid bands) with a dark lip every 4 rows."""
    r = _rng(seed)
    g = []
    for y in range(N):
        yy = y % 4
        band = pal[3] if yy == 0 else pal[1] if yy in (1, 2) else pal[0]
        g.append([band if r.random() < 0.9 else pal[2] for _ in range(N)])
    return g


def _lum(c: RGB) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def darken(g: list[list[RGB]], target: float = 46.0, contrast: float = 0.72) -> list[list[RGB]]:
    """Scale so the mean luminance is ~target and squash contrast, so light sidebar text stays readable."""
    flat = [c for row in g for c in row]
    mean = [sum(c[i] for c in flat) / len(flat) for i in range(3)]
    k = target / max(1.0, _lum((int(mean[0]), int(mean[1]), int(mean[2]))))
    out = []
    for row in g:
        out.append([tuple(max(0, min(255, int((mean[i] + (c[i] - mean[i]) * contrast) * k))) for i in range(3)) for c in row])
    return out  # type: ignore[return-value]


def _img(g: list[list[RGB]]) -> Image.Image:
    im = Image.new("RGB", (N, N))
    im.putdata([c for row in g for c in row])
    return im


def sidebar_tile(biome: str) -> Image.Image:
    if biome == "overworld":      # oak planks
        g = darken(planks([(150, 118, 70), (162, 130, 78), (138, 108, 62), (176, 142, 88), (190, 156, 98)], (92, 70, 40), 1))
    elif biome == "cherry":       # cherry planks
        g = darken(planks([(232, 150, 168), (242, 170, 184), (216, 132, 152), (250, 190, 202), (255, 210, 220)], (140, 70, 92), 2), 46, 0.8)
    elif biome == "snow":         # packed ice: deep blue with a few pale fracture lines
        g = speckle([(96, 140, 210), (84, 126, 200), (108, 152, 220), (120, 166, 230)], 3, [4, 3, 2, 1])
        r = _rng(33)
        for _ in range(3):
            x, y = r.randint(0, N - 1), r.randint(0, N - 1)
            for k in range(r.randint(4, 7)):
                g[(y + k) % N][(x + k // 2) % N] = (170, 204, 244)
        g = darken(g, 34, 0.85)
    elif biome == "nether":       # nether bricks
        g = darken(bricks([(78, 24, 28), (66, 18, 22), (92, 30, 34), (104, 36, 38)], (40, 12, 16), 4), 38, 0.6)
    elif biome == "end":          # end stone bricks
        g = darken(bricks([(236, 232, 160), (226, 222, 148), (244, 240, 176), (250, 248, 190)], (120, 112, 70), 5), 42, 0.9)
    elif biome == "ocean":        # prismarine bricks
        g = darken(bricks([(90, 170, 150), (74, 150, 134), (104, 186, 166), (120, 200, 180)], (40, 92, 80), 6), 46)
    elif biome == "lush":         # moss block
        g = darken(speckle([(90, 130, 50), (80, 120, 44), (104, 146, 58), (70, 106, 40), (120, 160, 70)], 7, [4, 3, 3, 2, 1]), 46)
    elif biome == "desert":       # sandstone
        g = darken(bands([(120, 98, 56), (214, 194, 136), (186, 164, 108), (246, 234, 190)], 8), 46, 1.0)
    elif biome == "mushroom":     # mycelium
        g = speckle([(112, 96, 118), (98, 84, 104), (128, 112, 134), (84, 70, 90)], 9, [4, 4, 3, 2])
        r = _rng(99)
        for _ in range(9):
            x, y = r.randint(0, N - 2), r.randint(0, N - 2)
            g[y][x] = g[y][x + 1] = (214, 196, 216)
            g[y + 1][x] = (170, 150, 176)
        g = darken(g, 44, 1.0)
    elif biome == "deepdark":     # deepslate tiles with sculk creeping in
        g = darken(bricks([(60, 62, 70), (52, 54, 60), (68, 70, 78)], (28, 28, 32), 10, 8, 8), 34, 0.85)
        r = _rng(110)
        for _ in range(5):
            x, y = r.randint(0, N - 2), r.randint(8, N - 2)
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1), (-1, 1), (2, 1)):
                if 0 <= x + dx < N and 0 <= y + dy < N:
                    g[y + dy][x + dx] = (10, 40, 50)
        for x, y in ((3, 11), (13, 9)):
            g[y][x] = (30, 128, 138)
    else:
        raise KeyError(biome)
    return _img(g)


if __name__ == "__main__":
    from pathlib import Path
    from PIL import ImageDraw, ImageFont
    biomes = ["overworld", "cherry", "snow", "nether", "end", "ocean", "lush", "desert", "mushroom", "deepdark"]
    font = ImageFont.truetype(r"C:\Windows\Fonts\msjh.ttc", 14)
    W, H = 200, 190
    out = Image.new("RGB", (W * 5, H * 2))
    for k, b in enumerate(biomes):
        tile = sidebar_tile(b).resize((64, 64), Image.Resampling.NEAREST)
        panel = Image.new("RGB", (W, H))
        for y in range(0, H, 64):
            for x in range(0, W, 64):
                panel.paste(tile, (x, y))
        d = ImageDraw.Draw(panel)
        for i, t in enumerate([b, "新工作階段  Ctrl N", "技能與工具", "製作 Minecraft 風格", "今天稍早", "設定遠端連線"]):
            d.text((12, 10 + i * 28), t, fill=(235, 235, 235) if i else (123, 211, 74), font=font)
        out.paste(panel, ((k % 5) * W, (k // 5) * H))
    p = Path(r"C:\Users\sad79\AppData\Local\hermes\cache\scratch\sidebar_tiles.png")
    out.save(p)
    print(p)
