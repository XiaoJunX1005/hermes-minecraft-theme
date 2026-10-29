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
    rng = random.Random({"overworld": 4, "nether": 6, "end": 8, "snow": 10, "cherry": 12}[biome])
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


OUTLINE = {"nether": (86, 40, 52, 255), "end": (92, 70, 120, 255)}


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
