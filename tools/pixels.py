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
