"""A floating voxel island with a tree and a glowing lantern, rendered as a
turntable sprite by a tiny orthographic DDA ray caster (pure Python + Pillow)."""

from __future__ import annotations

import math
import random

from PIL import Image

from pixels import LEAF, MOSS, SLATE, SOIL, BARK, hex_rgb

N = 12                 # grid is N x N x N, island centred at (6, *, 6)
LANTERN = "#ffcf6e"
POST = "#8a7a66"


def build_island() -> dict[tuple[int, int, int], tuple[str, bool]]:
    """(x, y, z) -> (hex colour, emissive)."""
    rng = random.Random(4)
    vox: dict[tuple[int, int, int], tuple[str, bool]] = {}
    for x in range(N):
        for z in range(N):
            d = math.hypot(x + 0.5 - 6, z + 0.5 - 6) + rng.uniform(-0.35, 0.35)
            if d < 5.0:
                vox[(x, 6, z)] = (rng.choice(MOSS), False)
            for y, r, pal in ((5, 4.4, SOIL), (4, 3.7, SOIL + SLATE[:1]), (3, 3.0, SLATE),
                              (2, 2.1, SLATE), (1, 1.2, SLATE[1:])):
                if d < r:
                    vox[(x, y, z)] = (rng.choice(pal), False)
    # tree
    for y in (7, 8, 9):
        vox[(3, y, 4)] = (rng.choice(BARK), False)
    for x in range(2, 5):
        for z in range(3, 6):
            for y in (9, 10):
                if (x, y, z) != (3, 9, 4) and not (y == 10 and (x, z) in ((2, 3), (4, 5))):
                    vox[(x, y, z)] = (rng.choice(LEAF), False)
    vox[(3, 11, 4)] = (LEAF[0], False)
    # lantern on a post
    vox[(8, 7, 7)] = (POST, False)
    vox[(8, 8, 7)] = (POST, False)
    vox[(8, 9, 7)] = (LANTERN, True)
    vox[(8, 10, 7)] = (POST, False)
    # flowers / pebbles
    vox[(6, 7, 8)] = ("#e58fb0", False)
    vox[(9, 7, 4)] = ("#f2b36b", False)
    vox[(5, 7, 3)] = ("#d8d2c4", False)
    return vox


LIGHT = (0.45, 0.85, 0.30)
_ln = math.sqrt(sum(c * c for c in LIGHT))
LIGHT = tuple(c / _ln for c in LIGHT)


def _cast(vox, o, d):
    # slab test against the grid box
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


def render(size: int, frames: int, pitch_deg: float = 30.0) -> list[Image.Image]:
    vox = build_island()
    pitch = math.radians(pitch_deg)
    half = 8.4
    out = []
    for f in range(frames):
        yaw = 2 * math.pi * f / frames + math.radians(20)
        d = (math.cos(pitch) * math.sin(yaw), -math.sin(pitch), math.cos(pitch) * math.cos(yaw))
        right = (math.cos(yaw), 0.0, -math.sin(yaw))
        up = (d[1] * right[2] - d[2] * right[1], d[2] * right[0] - d[0] * right[2], d[0] * right[1] - d[1] * right[0])
        c = (6.0, 6.2, 6.0)
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
                    if axis is None:
                        axis = 1
                    n[axis] = -step[axis]
                    k = 0.42 + 0.58 * max(0.0, sum(n[i] * LIGHT[i] for i in range(3)))
                    r, g, b = int(r * k), int(g * k), int(b * k)
                img.putpixel((px, py), (r, g, b, 255))
        # 1px dark outline for crisp pixel-art edges
        src = img.copy()
        for py in range(size):
            for px in range(size):
                if src.getpixel((px, py))[3]:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x2, y2 = px + dx, py + dy
                    if 0 <= x2 < size and 0 <= y2 < size and src.getpixel((x2, y2))[3]:
                        img.putpixel((px, py), (12, 13, 17, 255))
                        break
        out.append(img)
    return out
