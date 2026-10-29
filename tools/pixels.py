"""Shared helpers + palette for the Voxel Lantern theme.

All art in this repo is original and generated procedurally by tools/.
"""

from __future__ import annotations

import random

# --- palette -------------------------------------------------------------------------
BG = "#15171c"
INK = "#ece6da"
TEAL = "#4fc3a8"       # primary accent (oxidised copper)
AMBER = "#f2b36b"      # lantern light
MOSS = ["#8fbf6a", "#7fb069", "#6d9d5a", "#5e8c4f"]
SOIL = ["#8a6a4f", "#7a5c43", "#6b5039"]
SLATE = ["#6f7480", "#626772", "#565a64", "#4a4e57"]
LEAF = ["#5fa56c", "#4f8f5f", "#457f55", "#3c704b"]
BARK = ["#6b4a35", "#5c3f2d"]


def noise_texture(w: int, h: int, palette: list[str], seed: int, weights: list[int] | None = None) -> list[list[str]]:
    """A stable w x h grid of palette colours (same seed -> same texture)."""
    rng = random.Random(seed)
    weights = weights or [1] * len(palette)
    return [[rng.choices(palette, weights)[0] for _ in range(w)] for _ in range(h)]


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
