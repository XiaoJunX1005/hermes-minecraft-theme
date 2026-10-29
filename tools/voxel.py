"""Floating voxel islands for five worlds, rendered as turntable sprites by a
tiny orthographic DDA ray caster (pure Python + Pillow). All art is original.

    from voxel import render, BIOMES
    frames = render(size=48, frames=24, biome="nether")
"""

from __future__ import annotations

import math
import random

from PIL import Image

N = 12  # grid is N x N x N, island centred at (6, *, 6)

Vox = dict[tuple[int, int, int], tuple[str, bool]]  # (x,y,z) -> (hex, emissive)


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# --- per-biome palettes: top surface, 2 under-layers, deep core ---------------------
PAL = {
    "overworld": dict(top=["#8fbf6a", "#7fb069", "#6d9d5a", "#5e8c4f"], mid=["#8a6a4f", "#7a5c43", "#6b5039"],
                      low=["#6f7480", "#626772", "#565a64"], core=["#565a64", "#4a4e57"]),
    "nether": dict(top=["#b0303a", "#9a2832", "#8a222c", "#c23d3f"], mid=["#6e2a2a", "#622424", "#7a3030"],
                   low=["#3a3238", "#332c31", "#2b252a"], core=["#2b252a", "#231e22"]),
    "end": dict(top=["#e6e2a8", "#dcd79a", "#d0cb8e", "#ece8b6"], mid=["#c9c48a", "#bdb87e", "#d0cb8e"],
                low=["#2a1e3a", "#22182f", "#31233f"], core=["#1d1428", "#22182f"]),
    "snow": dict(top=["#f4f8fc", "#e8eff6", "#dde7f0", "#ffffff"], mid=["#8a6a4f", "#7a5c43", "#6b5039"],
                 low=["#6f7480", "#626772", "#565a64"], core=["#565a64", "#4a4e57"]),
    "cherry": dict(top=["#8fbf6a", "#7fb069", "#9ac874", "#6d9d5a"], mid=["#8a6a4f", "#7a5c43", "#6b5039"],
                   low=["#6f7480", "#626772", "#565a64"], core=["#565a64", "#4a4e57"]),
}
PAL.update({
    "ocean": dict(top=["#e8dca8", "#ddd09a", "#d2c48e", "#efe4b4"], mid=["#5fa89c", "#4f9a8e", "#6cb4a6"],
                  low=["#3d7f78", "#357069", "#2e6560"], core=["#24504c", "#2e6560"]),
    "lush": dict(top=["#6fae46", "#5f9d3a", "#7cba4a", "#4f8a32"], mid=["#9aa4b0", "#8a94a0", "#a8b0bc"],
                 low=["#6f7480", "#626772", "#565a64"], core=["#565a64", "#4a4e57"]),
    "desert": dict(top=["#e8d8a0", "#ddca8e", "#f0e2b0", "#d6c088"], mid=["#d8c088", "#cbb27a", "#c4a870"],
                   low=["#b89a68", "#a88a5a", "#9c7e50"], core=["#9c7e50", "#8a6e44"]),
    "mushroom": dict(top=["#8a7a98", "#7a6a88", "#9a8aa8", "#6e6080"], mid=["#8a6a4f", "#7a5c43", "#6b5039"],
                     low=["#6f7480", "#626772", "#565a64"], core=["#565a64", "#4a4e57"]),
    "deepdark": dict(top=["#0f3a44", "#12303a", "#0c2a34", "#1a4a54"], mid=["#2a2e36", "#24282f", "#30343c"],
                     low=["#1c1f25", "#22262d"], core=["#16181d", "#1c1f25"]),
})
BIOMES = list(PAL)


def _base(rng: random.Random, pal: dict) -> Vox:
    vox: Vox = {}
    for x in range(N):
        for z in range(N):
            d = math.hypot(x + 0.5 - 6, z + 0.5 - 6) + rng.uniform(-0.35, 0.35)
            if d < 5.0:
                vox[(x, 6, z)] = (rng.choice(pal["top"]), False)
            for y, r, key in ((5, 4.4, "mid"), (4, 3.7, "mid"), (3, 3.0, "low"), (2, 2.1, "low"), (1, 1.2, "core")):
                if d < r:
                    vox[(x, y, z)] = (rng.choice(pal[key]), False)
    return vox


def _blob(vox: Vox, rng, cx, cz, ys, rad, colors, skip=()):
    for x in range(cx - rad, cx + rad + 1):
        for z in range(cz - rad, cz + rad + 1):
            for y in ys:
                if (x, y, z) in skip or (abs(x - cx) == rad and abs(z - cz) == rad):
                    continue
                if 0 <= x < N and 0 <= z < N and 0 <= y < N:
                    vox[(x, y, z)] = (rng.choice(colors), False)


def build_island(biome: str = "overworld") -> Vox:
    rng = random.Random({"overworld": 4, "nether": 6, "end": 8, "snow": 10, "cherry": 12, "ocean": 14, "lush": 16, "desert": 18, "mushroom": 20, "deepdark": 22}[biome])
    vox = _base(rng, PAL[biome])

    if biome == "overworld":
        for y in (7, 8, 9):
            vox[(3, y, 4)] = (rng.choice(["#6b4a35", "#5c3f2d"]), False)
        _blob(vox, rng, 3, 4, (9, 10), 1, ["#5fa56c", "#4f8f5f", "#457f55", "#3c704b"], skip={(3, 9, 4)})
        vox[(3, 11, 4)] = ("#5fa56c", False)
        for y in (7, 8):
            vox[(8, y, 7)] = ("#8a7a66", False)
        vox[(8, 9, 7)] = ("#ffcf6e", True)
        vox[(8, 10, 7)] = ("#8a7a66", False)
        vox[(6, 7, 8)] = ("#e58fb0", False)
        vox[(9, 7, 4)] = ("#f2b36b", False)
        for p in ((7, 6, 3), (8, 6, 3), (7, 6, 4)):  # little pond
            vox[p] = ("#4c8fd6", False)

    elif biome == "nether":
        for p in ((7, 6, 6), (8, 6, 6), (7, 6, 7), (8, 6, 5), (6, 6, 7)):  # lava pool
            vox[p] = (rng.choice(["#ff8a2a", "#ffa63a", "#f2701e"]), True)
        for y in (7, 8, 9):  # crimson fungus: dark stem, bright cap
            vox[(3, y, 4)] = ("#4a1e3a", False)
        _blob(vox, rng, 3, 4, (10,), 1, ["#e0343c", "#f04848", "#c82a33"])
        _blob(vox, rng, 3, 4, (11,), 0, ["#f04848"])
        for y in (7, 8):  # small warped fungus (teal) for contrast
            vox[(8, y, 8)] = ("#3a2a4a", False)
        for p in ((8, 9, 8), (9, 9, 8), (8, 9, 9), (7, 9, 8)):
            vox[p] = (rng.choice(["#1fa59a", "#2bc0b0", "#17877f"]), False)
        vox[(4, 9, 5)] = ("#ffbe5c", True)  # shroomlight
        for p in ((9, 7, 3), (9, 8, 3), (9, 7, 4)):  # basalt spike
            vox[p] = ("#4a4650", False)
        vox[(5, 7, 9)] = ("#d2453a", False)

    elif biome == "end":
        for y in (7, 8, 9, 10):  # obsidian pillar
            vox[(8, y, 7)] = ("#1f1530", False)
        vox[(8, 11, 7)] = ("#f08cff", True)  # end crystal
        for y in (7, 8, 9):  # chorus plant
            vox[(3, y, 4)] = ("#7a4f8f", False)
        vox[(4, 9, 4)] = ("#7a4f8f", False)
        vox[(2, 8, 4)] = ("#7a4f8f", False)
        for p in ((3, 10, 4), (4, 10, 4), (2, 9, 4)):
            vox[p] = ("#c9a6e0", False)
        for p in ((10, 9, 2), (1, 10, 9)):  # tiny satellite rocks
            vox[p] = ("#dcd79a", False)

    elif biome == "snow":
        vox[(3, 7, 4)] = ("#4a3426", False)  # spruce: stepped cone
        for y, r in ((8, 2), (9, 1), (10, 1), (11, 0)):
            _blob(vox, rng, 3, 4, (y,), r, ["#2f5a43", "#284e3a", "#355f48"])
        for p in ((1, 8, 4), (5, 8, 4), (3, 8, 2), (3, 8, 6), (2, 10, 4), (4, 10, 4), (3, 11, 4)):
            vox[p] = ("#f4f8fc", False)  # snow on the branch tips
        vox[(8, 7, 7)] = ("#a8d8ff", False)  # ice block
        vox[(8, 8, 7)] = ("#cdeaff", False)
        vox[(6, 7, 8)] = ("#8ab8e8", True)  # soul-ish lantern

    elif biome == "ocean":
        for p in ((7, 6, 6), (8, 6, 6), (7, 6, 7), (8, 6, 7), (6, 6, 7)):
            vox[p] = (rng.choice(["#2f7fd0", "#3a8ee0", "#2a70bc"]), False)
        for x, z, h in ((3, 4, 5), (4, 3, 3), (2, 6, 4)):
            for y in range(7, 7 + h):
                vox[(x, y, z)] = (rng.choice(["#3f8a3a", "#4a9a42", "#357a31"]), False)
        for p, c in (((9, 7, 4), "#f06a8a"), ((9, 8, 4), "#f58aa4"), ((5, 7, 9), "#f2c64a"), ((6, 7, 9), "#7a8cf0")):
            vox[p] = (c, False)
        vox[(9, 7, 8)] = ("#bfeef0", True)

    elif biome == "lush":
        for y in (7, 8):
            vox[(4, y, 5)] = ("#6b4a35", False)
        _blob(vox, rng, 4, 5, (9, 10), 1, ["#5f9d3a", "#4f8a32", "#6fae46"])
        for p in ((3, 10, 4), (5, 9, 6), (4, 10, 6), (3, 9, 5)):
            vox[p] = ("#e58fd0", False)
        for p in ((8, 6, 7), (8, 6, 8), (9, 6, 7)):
            vox[p] = ("#4c8fd6", False)
        for y in (7, 8):
            vox[(8, y, 4)] = ("#5f9d3a", False)
        for p in ((7, 9, 4), (8, 9, 4), (9, 9, 4), (8, 9, 3)):
            vox[p] = ("#7cba4a", False)
        vox[(6, 6, 11)] = ("#4f8a32", False)
        vox[(6, 5, 11)] = ("#4f8a32", False)
        vox[(6, 4, 11)] = ("#ff9a3a", True)

    elif biome == "desert":
        for y in (7, 8, 9):
            vox[(3, y, 4)] = ("#5f9d3a", False)
        vox[(2, 8, 4)] = ("#5f9d3a", False)
        vox[(2, 9, 4)] = ("#5f9d3a", False)
        vox[(9, 7, 7)] = ("#8a6a3a", False)
        for x in range(6, 9):
            for z in (8, 9):
                vox[(x, 7, z)] = ("#e0c98a", False)
        vox[(7, 8, 8)] = ("#d07a3a", False)

    elif biome == "mushroom":
        for y in (7, 8, 9):
            vox[(4, y, 5)] = ("#e8e0d0", False)
        _blob(vox, rng, 4, 5, (10,), 2, ["#d03a30", "#c02a24", "#e04a40"])
        _blob(vox, rng, 4, 5, (11,), 1, ["#d03a30"])
        for p in ((3, 10, 3), (6, 10, 6), (2, 10, 5), (5, 11, 4)):
            vox[p] = ("#f0f0f0", False)
        vox[(9, 7, 8)] = ("#e8e0d0", False)
        for p in ((9, 8, 8), (8, 8, 8), (10, 8, 8), (9, 8, 7), (9, 8, 9)):
            vox[p] = ("#b07a4a", False)

    elif biome == "deepdark":
        vox[(6, 7, 6)] = ("#0f3a44", False)
        vox[(6, 8, 6)] = ("#2fd8e8", True)
        vox[(3, 7, 4)] = ("#d8d0b8", False)
        vox[(3, 8, 4)] = ("#e8e0c8", False)
        for y in (7, 8, 9, 10):
            vox[(9, y, 8)] = ("#4a4f5a", False)
        vox[(9, 11, 8)] = ("#2fd8e8", True)

    elif biome == "cherry":
        for y in (7, 8, 9):
            vox[(4, y, 5)] = ("#4a2f2a", False)
        vox[(5, 9, 5)] = ("#4a2f2a", False)
        _blob(vox, rng, 4, 5, (10, 11), 2, ["#f7b8d2", "#f0a3c4", "#e98fb6", "#fbd0e2"])
        _blob(vox, rng, 4, 5, (12 - 1,), 1, ["#fbd0e2", "#f7b8d2"])
        for p in ((7, 6, 7), (8, 6, 7), (7, 6, 8)):
            vox[p] = ("#4c9fd6", False)
        for _ in range(6):
            x, z = rng.randrange(2, 10), rng.randrange(2, 10)
            if (x, 6, z) in vox and (x, 7, z) not in vox:
                vox[(x, 7, z)] = ("#f7b8d2", False)
    return vox


LIGHT = (0.45, 0.85, 0.30)
_ln = math.sqrt(sum(c * c for c in LIGHT))
LIGHT = tuple(c / _ln for c in LIGHT)


def _cast(vox: Vox, o, d):
    t0, t1 = -1e9, 1e9
    for i in range(3):
        if abs(d[i]) < 1e-12:
            if not 0 <= o[i] <= N:
                return None
            continue
        a, b = (0 - o[i]) / d[i], (N - o[i]) / d[i]
        if a > b:
            a, b = b, a
        t0, t1 = max(t0, a), min(t1, b)
    if t0 > t1 or t1 < 0:
        return None
    t = max(t0, 0) + 1e-6
    p = [o[i] + d[i] * t for i in range(3)]
    cell = [min(N - 1, max(0, int(math.floor(p[i])))) for i in range(3)]
    step = [1 if d[i] > 0 else -1 for i in range(3)]
    tmax, tdelta = [], []
    for i in range(3):
        if abs(d[i]) < 1e-12:
            tmax.append(1e9)
            tdelta.append(1e9)
        else:
            nxt = cell[i] + (1 if d[i] > 0 else 0)
            tmax.append(t + (nxt - p[i]) / d[i])
            tdelta.append(abs(1 / d[i]))
    axis = None
    while all(0 <= cell[i] < N for i in range(3)):
        hit = vox.get(tuple(cell))
        if hit:
            return hit, axis, step
        axis = min(range(3), key=lambda i: tmax[i])
        cell[axis] += step[axis]
        tmax[axis] += tdelta[axis]
    return None


OUTLINE = {"nether": (86, 40, 52, 255), "end": (92, 70, 120, 255), "deepdark": (40, 110, 120, 255)}


def render(size: int, frames: int, biome: str = "overworld", pitch_deg: float = 30.0) -> list[Image.Image]:
    vox = build_island(biome)
    edge = OUTLINE.get(biome, (12, 13, 17, 255))
    pitch = math.radians(pitch_deg)
    half = 8.4
    out = []
    for f in range(frames):
        yaw = 2 * math.pi * f / frames + math.radians(20)
        d = (math.cos(pitch) * math.sin(yaw), -math.sin(pitch), math.cos(pitch) * math.cos(yaw))
        right = (math.cos(yaw), 0.0, -math.sin(yaw))
        up = (d[1] * right[2] - d[2] * right[1], d[2] * right[0] - d[0] * right[2], d[0] * right[1] - d[1] * right[0])
        c = (6.0, 6.4, 6.0)
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        for py in range(size):
            for px in range(size):
                u = (px + 0.5) / size * 2 * half - half
                v = half - (py + 0.5) / size * 2 * half
                o = tuple(c[i] + right[i] * u + up[i] * v - d[i] * 30 for i in range(3))
                hit = _cast(vox, o, d)
                if not hit:
                    continue
                (col, emissive), axis, step = hit
                r, g, b = hex_rgb(col)
                if not emissive:
                    n = [0.0, 0.0, 0.0]
                    n[1 if axis is None else axis] = -step[1 if axis is None else axis]
                    k = 0.42 + 0.58 * max(0.0, sum(n[i] * LIGHT[i] for i in range(3)))
                    r, g, b = int(r * k), int(g * k), int(b * k)
                img.putpixel((px, py), (r, g, b, 255))
        src = img.copy()
        for py in range(size):
            for px in range(size):
                if src.getpixel((px, py))[3]:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x2, y2 = px + dx, py + dy
                    if 0 <= x2 < size and 0 <= y2 < size and src.getpixel((x2, y2))[3]:
                        img.putpixel((px, py), edge)
                        break
        out.append(img)
    return out
