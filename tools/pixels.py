"""Shared pixel-art data for the Minecraft theme (pet sprite + CLI banner).

Everything is generated procedurally from small seeded-noise textures so the
art is original (fan-made), deterministic, and easy to tweak.
"""

from __future__ import annotations

import random

# Creeper-ish greens, light -> dark.
CREEPER_GREENS = ["#a6e08f", "#7cc96a", "#5daa4a", "#4b9a3a", "#3a8a2f", "#2c6e24"]
CREEPER_FACE = "#101a0e"

# Classic 8x8 creeper face mask (1 = dark).
FACE_8 = [
    "........",
    ".XX..XX.",
    ".XX..XX.",
    "...XX...",
    "..XXXX..",
    "..XXXX..",
    "..X..X..",
    "........",
]

GRASS_TOP = ["#8ad45c", "#79c24e", "#6bb545", "#5da23b"]
DIRT = ["#9b6b43", "#86593a", "#7a4f2e", "#5c3a21"]


def noise_texture(w: int, h: int, palette: list[str], seed: int, weights: list[int] | None = None) -> list[list[str]]:
    """A stable w x h grid of palette colors (same seed -> same texture)."""
    rng = random.Random(seed)
    weights = weights or [1] * len(palette)
    return [[rng.choices(palette, weights)[0] for _ in range(w)] for _ in range(h)]


def creeper_head(size: int = 16, face_dx: int = 0, seed: int = 7) -> list[list[str]]:
    """size x size head texture with the face stamped in (scaled from 8x8)."""
    tex = noise_texture(size, size, CREEPER_GREENS, seed, [2, 4, 6, 5, 3, 2])
    k = size // 8
    for fy, row in enumerate(FACE_8):
        for fx, c in enumerate(row):
            if c != "X":
                continue
            for yy in range(k):
                for xx in range(k):
                    x = fx * k + xx + face_dx
                    y = fy * k + yy
                    if 0 <= x < size and 0 <= y < size:
                        tex[y][x] = CREEPER_FACE
    return tex


def grass_block_front(w: int = 16, h: int = 16, seed: int = 3) -> list[list[str]]:
    """Front face of a grass block: grass band with drips over dirt."""
    rng = random.Random(seed)
    dirt = noise_texture(w, h, DIRT, seed + 1, [2, 4, 4, 2])
    grass = noise_texture(w, h, GRASS_TOP, seed + 2)
    for x in range(w):
        depth = 3 + (rng.random() < 0.45) + (rng.random() < 0.2)
        for y in range(depth):
            dirt[y][x] = grass[y][x]
    return dirt


# --- high-detail (32x32) textures: smooth value noise instead of per-pixel dither ---

def value_noise(w: int, h: int, cell: int, seed: int) -> list[list[float]]:
    """Tileable smooth noise in [0, 1] (bilinear between random lattice points)."""
    rng = random.Random(seed)
    gw, gh = max(1, w // cell), max(1, h // cell)
    lat = [[rng.random() for _ in range(gw)] for _ in range(gh)]
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            fx, fy = x / cell, y / cell
            x0, y0 = int(fx) % gw, int(fy) % gh
            x1, y1 = (x0 + 1) % gw, (y0 + 1) % gh
            tx, ty = fx - int(fx), fy - int(fy)
            tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
            a = lat[y0][x0] * (1 - tx) + lat[y0][x1] * tx
            b = lat[y1][x0] * (1 - tx) + lat[y1][x1] * tx
            row.append(a * (1 - ty) + b * ty)
        out.append(row)
    return out


def fbm(w: int, h: int, seed: int) -> list[list[float]]:
    n1, n2, n3 = value_noise(w, h, 8, seed), value_noise(w, h, 4, seed + 1), value_noise(w, h, 2, seed + 2)
    return [[0.55 * n1[y][x] + 0.3 * n2[y][x] + 0.15 * n3[y][x] for x in range(w)] for y in range(h)]


def _ramp(palette: list[str], t: float) -> str:
    t = min(0.999, max(0.0, t))
    return palette[int(t * len(palette))]


GRASS_HD = ["#4f8f37", "#5c9e3e", "#69ad46", "#77bb4f", "#86c75b", "#98d36a"]
DIRT_HD = ["#5b3d27", "#6a4830", "#79543a", "#876045", "#966d50"]


def grass_top_hd(n: int = 32, seed: int = 31) -> list[list[str]]:
    rng = random.Random(seed)
    f = fbm(n, n, seed)
    tex = [[_ramp(GRASS_HD, 0.15 + f[y][x] * 0.75) for x in range(n)] for y in range(n)]
    for _ in range(n * 2):  # short bright blades
        x, y = rng.randrange(n), rng.randrange(n - 1)
        tex[y][x] = GRASS_HD[-1]
        tex[y + 1][x] = GRASS_HD[-2]
    for _ in range(n // 2):  # tiny shadow specks
        tex[rng.randrange(n)][rng.randrange(n)] = GRASS_HD[0]
    return tex


def dirt_hd(n: int = 32, seed: int = 41, pebbles: bool = True) -> list[list[str]]:
    rng = random.Random(seed)
    f = fbm(n, n, seed)
    tex = [[_ramp(DIRT_HD, 0.1 + f[y][x] * 0.8) for x in range(n)] for y in range(n)]
    if pebbles:
        for _ in range(n // 4):
            x, y = rng.randrange(n - 2), rng.randrange(n - 2)
            tex[y][x], tex[y][x + 1], tex[y + 1][x] = "#a08a76", "#8c7866", "#7a6656"
            tex[y + 1][x + 1] = "#4a3322"
    return tex


def grass_side_hd(n: int = 32, seed: int = 51) -> list[list[str]]:
    """Side face: rounded grass overhang with soft drips, a shadow line, pebbly dirt."""
    tex = dirt_hd(n, seed)
    top = grass_top_hd(n, seed + 7)
    edge = value_noise(n, 1, 4, seed + 3)[0]
    for x in range(n):
        depth = 5 + int(edge[x] * 6)
        for y in range(depth):
            tex[y][x] = top[y][x] if y < depth - 1 else GRASS_HD[0]
        if depth < n:
            tex[depth][x] = "#3e2a1b"  # shadow under the turf
    return tex
