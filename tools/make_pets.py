"""HD pets: 3D box models rendered to 96x104 pixel art (2px per pixel, 192x208 cells).

Sheet: 16 columns x 9 rows (Codex row order). The walk rows (running-right / -left)
use all 16 columns - the desktop roaming walk reads every non-blank column - while
the other states use 6 (Hermes plays at most 6 frames per state over 1100 ms).

Run:  python tools/make_pets.py [slug ...]   -> pets/<slug>/, docs/pets/<slug>.gif, docs/pets.gif
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageDraw, ImageFont

import pet3d as P

ROOT = Path(__file__).resolve().parent.parent
STATES = ["idle", "running-right", "running-left", "waving", "jumping", "failed", "waiting", "running", "review"]
WALK = {"running-right", "running-left"}
COLS, WALK_N, STATE_N = 16, 16, 6
TAU = 2 * math.pi
FRONT_YAW = math.radians(-22)
SIDE_YAW = math.radians(62)
MARGIN = 2          # grid pixels kept clear on every side
KW = dict[str, Any]


def nframes(state: str) -> int:
    return WALK_N if state in WALK else STATE_N


def phase(state: str, f: int) -> float:
    return TAU * f / nframes(state)


def facing(state: str) -> int:
    return 1 if state == "running-right" else -1


def gbbox(parts: list[P.Part], names: tuple[str, ...] = ()) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for p in parts:
        if names and p.name not in names:
            continue
        hx, hy, hz = p.half
        for a in (-hx, hx):
            for b in (-hy, hy):
                for c in (-hz, hz):
                    gx, gy = P.project(P.add(P.mv(p.M, (a, b, c)), p.t))
                    xs.append(gx)
                    ys.append(gy)
    return min(xs), min(ys), max(xs), max(ys)


def common(state: str, f: int, parts: list[P.Part], over: P.FX, head: tuple[str, ...] = ("head",)) -> None:
    """Hearts / bubble / sweat / book, placed from the head's screen box and kept inside the cell."""
    hx0, hy0, hx1, _ = gbbox(parts, head)
    ax0 = gbbox(parts)[0]
    if state == "waving":
        for k in range(2):
            age = (f + 3 * k) % 6
            x = hx1 + 1 if k == 0 else hx0 - 10
            x = min(max(x, MARGIN + 1), P.GRID_W - MARGIN - 10)
            P.heart(over, x, max(MARGIN + 1, hy0 + 8 - age * 2.6), 255 - age * 38)
    elif state == "waiting":
        P.bubble(over, int(min(P.GRID_W - MARGIN - 20, hx1 + 2)), int(max(MARGIN, hy0 - 5)), 1 + f // 2)
    elif state == "running":
        P.sweat(over, min(P.GRID_W - MARGIN - 4, hx1), max(MARGIN + 1, hy0 + 2 + (f % 3) * 2))
    elif state == "review":
        P.book(over, int(max(MARGIN, ax0 - 8)), int(P.GROUND - 12), f)


def walk_dust(under: P.FX, f: int, face: int, rear: float, starts: tuple[int, ...] = (4, 12)) -> None:
    gx, gy = P.project((-face * rear, 0.0, 0.0))
    for start in starts:
        age = (f - start) % WALK_N
        if age < 4:
            P.puff(under, gx - face * age * 1.4, gy - 1 - age * 0.8, 1.6 + age * 0.7, 200 - age * 48)


def stars_ring(over: P.FX, parts: list[P.Part], f: int, n: int = 3) -> None:
    x0, y0, x1, _ = gbbox(parts, ("head",))
    cx, cy = (x0 + x1) / 2, max(MARGIN + 3, y0 - 3)
    for k in range(n):
        a = TAU * f / 6 + k * TAU / n
        P.star(over, cx + math.cos(a) * 9, cy + math.sin(a) * 2.5, 255)


def burst(over: P.FX, cx: float, cy: float, f: int, r0: float = 11) -> None:
    """Smoke that pushes out from the body: ring at f4, wider and fainter at f5, a wisp at f0."""
    if f == 4:
        P.puff(over, cx, cy, 6, 215)
        for k in range(8):
            a = k * TAU / 8 + 0.3
            P.puff(over, cx + math.cos(a) * r0, cy + math.sin(a) * r0 * 0.75, 4.5, 225, dark=k % 2 == 1)
    elif f == 5:
        for k in range(8):
            a = k * TAU / 8 + 0.7
            P.puff(over, cx + math.cos(a) * (r0 + 6), cy + math.sin(a) * (r0 + 6) * 0.75 - 2, 3, 120, dark=True)
    elif f == 0:
        P.puff(over, cx + 2, cy - r0 - 4, 2.5, 70, dark=True)


def body_center(parts: list[P.Part], names: tuple[str, ...]) -> tuple[float, float]:
    x0, y0, x1, y1 = gbbox(parts, names)
    return (x0 + x1) / 2, (y0 + y1) / 2


# ================================================================== creeper =============
GREEN = [(28, 66, 26), (38, 86, 34), (48, 106, 42), (60, 126, 50), (74, 146, 58), (92, 166, 70), (116, 188, 88), (150, 212, 116)]
EYE, EYE_RIM, MOUTH, MOUTH_RIM = (16, 26, 16), (34, 54, 30), (18, 30, 18), (40, 66, 34)
MOUTH_MASK = ({(u, v) for v in range(12, 15) for u in range(10, 14)} |
              {(u, v) for v in range(15, 18) for u in range(7, 17)} |
              {(u, v) for v in range(18, 21) for u in list(range(7, 10)) + list(range(14, 17))})


def _ceye(kind: str, x: int, y: int, look: float):
    if kind == "blink":
        return EYE if y >= 4 else None
    if kind == "squint":
        return EYE if 2 <= y <= 3 else None
    if kind == "happy":
        return EYE if (y == 2 and x in (2, 3)) or (y == 3 and x in (1, 4)) or (y == 4 and x in (0, 5)) else None
    if kind == "x":
        return EYE if x == y or x == 5 - y else None
    gx = 3 + round(look * 1.4)
    gy = 4 if kind == "down" else 1
    if (x, y) in ((gx, gy), (max(0, gx - 1), gy)):
        return (58, 88, 52)
    return EYE_RIM if (x in (0, 5) or y in (0, 5)) else EYE


def creeper_head_tex(eyes: str, look: float) -> P.Tex:
    def tex(face, u, v, W, H):
        if face == "front":
            for ex in (3, 15):
                if ex <= u < ex + 6 and 6 <= v < 12:
                    c = _ceye(eyes, u - ex, v - 6, look)
                    return c if c else -0.04
            if (u, v) in MOUTH_MASK:
                inner = all((u + du, v + dv) in MOUTH_MASK for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                return MOUTH if inner else MOUTH_RIM
        if face in P.SIDES and v >= H - 2:
            return -0.08
        return None
    return tex


def _shade_ends(face, u, v, W, H):
    if face in P.SIDES and v >= H - 3:
        return -0.1
    if face in P.SIDES and v <= 1:
        return -0.06
    return None


def creeper_parts(yaw=FRONT_YAW, lift=0.0, dx=0.0, sc=(1.0, 1.0, 1.0), roll=0.0, pitch=0.0,
                  hy=0.0, hp=0.0, hr=0.0, hdy=0.0, legs=(0.0, 0.0, 0.0, 0.0), eyes="open", look=0.0) -> list[P.Part]:
    root = P.Rig(P.chain(P.rot_y(yaw), P.scale(*sc)), (dx, lift, 0.0))
    hips = root.child((0, 6, 0), P.chain(P.rot_z(roll), P.rot_x(pitch)))
    neck = hips.child((0, 12, 0), P.chain(P.rot_y(hy), P.rot_x(hp), P.rot_z(hr)))
    parts = [hips.box("body", (0, 6, 0), (4, 6, 2), _shade_ends, GREEN, 1),
             neck.box("head", (0, 4 + hdy, 0), (4, 4, 4), creeper_head_tex(eyes, look), GREEN, 0)]
    for k, (x, z) in enumerate(((-2, 4), (2, 4), (-2, -4), (2, -4))):
        leg = root.child((x, 6, z), P.rot_x(legs[k]))
        parts.append(leg.box(f"leg{k}", (0, -3, 0), (2, 3, 2), _shade_ends, GREEN, 2 + k))
    return parts


def creeper_frame(state: str, f: int) -> Image.Image:
    under, over = P.FX(), P.FX()
    p = phase(state, f)
    flash = 0.0
    kw: KW = {}
    if state == "idle":
        kw = dict(sc=(1, 1 + 0.02 * math.sin(p), 1), hdy=0.2 * math.sin(p), hy=-0.06 + 0.08 * math.sin(p), look=math.sin(p) * 0.6)
    elif state in WALK:
        a = 0.46 * math.sin(p)
        kw = dict(yaw=SIDE_YAW * facing(state), lift=-6 * (1 - math.cos(a)), legs=(-a, a, a, -a), roll=0.025 * math.sin(2 * p),
                  hy=0.06 * math.sin(p - 0.8), hp=-0.04 * math.cos(2 * p), look=0.8)
        walk_dust(under, f, facing(state), 3.2)
    elif state == "waving":
        w = math.sin(p)
        kw = dict(legs=(-1.05 - 0.28 * w, 0.06, 0.0, 0.0), roll=-0.05 - 0.03 * w, pitch=-0.05, hr=0.08 * w, hy=-0.1, eyes="happy")
    elif state == "jumping":
        # crouch, push off, rise (legs trail), apex (tucked, front reaches), fall (legs reach down), land
        lift = [0.0, 1.4, 2.7, 3.2, 1.9, 0.0][f]
        sy = [0.84, 1.1, 1.05, 1.0, 1.03, 0.9][f]
        front = [0.18, 0.3, -0.18, -0.38, -0.16, 0.12][f]
        back = [-0.18, -0.42, 0.25, 0.42, 0.12, -0.12][f]
        sx = 1 + (1 - sy) * 0.5
        kw = dict(lift=lift, sc=(sx, sy, sx), legs=(front, front * 0.9, back, back * 0.9), hp=[0.1, -0.08, -0.12, -0.04, 0.05, 0.1][f],
                  eyes="happy" if f in (2, 3) else "open")
        if f in (1, 5):
            for side in (-1, 1):
                gx, gy = P.project((side * 4.5, 0, 2))
                P.puff(under, gx + side * 2, gy - 1, 2.6, 180)
    elif state == "failed":
        s = [1.0, 1.03, 1.06, 1.09, 1.0, 1.0][f]
        flash = [0.0, 0.3, 0.55, 0.85, 0.0, 0.0][f]
        kw = dict(sc=(s, s, s), dx=[0.2, -0.25, 0.3, -0.3, 0, 0][f], eyes=["squint", "squint", "squint", "squint", "x", "x"][f],
                  hp=[0, 0, 0, 0, 0.12, 0.18][f])
    elif state == "waiting":
        kw = dict(hy=0.4 * math.sin(p), look=math.sin(p), sc=(1, 1 + 0.015 * math.sin(2 * p), 1))
    elif state == "running":
        a = 0.5 * math.sin(p)
        kw = dict(legs=(-a, a, a, -a), lift=-6 * (1 - math.cos(a)), roll=0.03 * math.sin(p), hy=-0.08, look=-0.3)
    elif state == "review":
        kw = dict(hp=0.3 + 0.04 * math.sin(p), hy=-0.3 + 0.05 * math.sin(p), eyes="down", look=-0.6)
    parts = creeper_parts(**kw)
    P.shadow(under, (kw.get("dx", 0.0), 0, 0), P.footprint(4.5, 6, kw.get("yaw", FRONT_YAW)), kw.get("lift", 0.0))
    common(state, f, parts, over)
    if state == "failed":
        cx, cy = body_center(parts, ("body",))
        burst(over, cx, cy, f, 12)
    return P.render(parts, under, over, flash=flash)


# ================================================================== pig ==================
PINK = [(150, 78, 92), (178, 98, 112), (204, 122, 134), (224, 146, 156), (238, 168, 176), (246, 188, 194), (252, 206, 210), (255, 224, 226)]
SNOUT = [(172, 88, 104), (196, 110, 126), (214, 132, 146), (230, 152, 164), (240, 172, 182), (248, 192, 200)]
HOOF = (96, 62, 60)
PIG_DARK = (52, 30, 36)


def pig_head_tex(eyes: str, look: float) -> P.Tex:
    def tex(face, u, v, W, H):
        if face == "front":
            for ex, inner_right in ((3, True), (15, False)):
                if ex <= u < ex + 6 and 9 <= v < 12:
                    x, y = u - ex, v - 9
                    if eyes == "blink":
                        return PIG_DARK if y == 2 else None
                    if eyes == "happy":
                        return PIG_DARK if (y == 0 and x in (2, 3)) or (y == 1 and x in (1, 4)) or (y == 2 and x in (0, 5)) else None
                    if eyes == "x":
                        return PIG_DARK if (y == 1 and x in (2, 3)) or (y in (0, 2) and x in (1, 4)) else None
                    split = 3 + round(look)
                    dark = x >= split if inner_right else x < 6 - split
                    return (26, 18, 22) if dark else (244, 240, 236)
        if face in P.SIDES and v >= H - 2:
            return -0.08
        return None
    return tex


def pig_snout_tex(face, u, v, W, H):
    if face == "front" and 2 <= v <= 5 and (u in (2, 3) or u in (W - 4, W - 3)):
        return (112, 50, 66)
    return 0.12


def pig_leg_tex(face, u, v, W, H):
    if face in P.SIDES and v >= H - 3:
        return HOOF
    if face == "bottom":
        return HOOF
    return -0.05


def pig_parts(yaw=FRONT_YAW, lift=0.0, dx=0.0, sc=(1.0, 1.0, 1.0), roll=0.0, pitch=0.0, hy=0.0, hp=0.0, hr=0.0,
              legs=(0.0, 0.0, 0.0, 0.0), eyes="open", look=0.0, tail=0.0) -> list[P.Part]:
    root = P.Rig(P.chain(P.rot_y(yaw), P.scale(*sc)), (dx, lift, 0.0))
    hips = root.child((0, 5, -3.33), P.chain(P.rot_z(roll), P.rot_x(pitch)))
    parts = [hips.box("body", (0, 3.67, 0), (4.33, 3.67, 7.33), _shade_ends, PINK, 1)]
    neck = hips.child((0, 4.67, 7.33), P.chain(P.rot_y(hy), P.rot_x(hp), P.rot_z(hr)))
    parts.append(neck.box("head", (0, 0.33, 2.67), (4, 4, 3.67), pig_head_tex(eyes, look), PINK, 0))
    parts.append(neck.box("snout", (0, -1.67, 7.0), (2, 1.5, 0.67), pig_snout_tex, SNOUT, 2))
    tl = hips.child((0, 6.33, -7.33), P.rot_x(tail))
    parts.append(tl.box("tail", (0, 0.33, -0.5), (0.5, 0.5, 0.5), None, PINK, 3))
    for k, (x, z) in enumerate(((-2.33, 4.67), (2.33, 4.67), (-2.33, -5.0), (2.33, -5.0))):
        leg = root.child((x, 5, z - 3.33), P.rot_x(legs[k]))
        parts.append(leg.box(f"leg{k}", (0, -2.5, 0), (1.67, 2.5, 1.67), pig_leg_tex, PINK, 4 + k))
    return parts


def pig_frame(state: str, f: int) -> Image.Image:
    under, over = P.FX(), P.FX()
    p = phase(state, f)
    kw: KW = {}
    if state == "idle":
        kw = dict(sc=(1, 1 + 0.018 * math.sin(p), 1), hp=0.04 * math.sin(p), look=0.6 * math.sin(p), tail=0.4 * math.sin(2 * p))
    elif state in WALK:
        a = 0.44 * math.sin(p)
        kw = dict(yaw=SIDE_YAW * facing(state), lift=-5 * (1 - math.cos(a)), legs=(-a, a, a, -a), roll=0.02 * math.sin(2 * p),
                  hp=0.06 * math.sin(2 * p), tail=0.5 * math.sin(2 * p))
        walk_dust(under, f, facing(state), 10)
    elif state == "waving":
        w = math.sin(p)
        kw = dict(legs=(-1.0 - 0.3 * w, 0.0, 0.0, 0.0), roll=0.05, hr=0.1 * w, eyes="happy", tail=0.6 * w)
    elif state == "jumping":
        lift = [0.0, 2.4, 5.6, 6.8, 3.8, 0.0][f]
        sy = [0.86, 1.1, 1.04, 1.0, 1.03, 0.9][f]
        t = [-0.1, 0.25, 0.45, 0.55, 0.3, -0.08][f]
        sx = 1 + (1 - sy) * 0.5
        kw = dict(lift=lift, sc=(sx, sy, sx), legs=(-t, -t, t, t), eyes="happy" if f in (2, 3) else "open", hp=[0.08, -0.1, -0.12, -0.05, 0.05, 0.08][f])
    elif state == "failed":
        kw = dict(roll=[0.12, -0.12, 0.08, -0.06, 0.03, 0][f], hr=[-0.15, 0.15, -0.1, 0.08, -0.04, 0][f], eyes="x",
                  sc=(1, [0.94, 0.97, 1, 1, 1, 1][f], 1), legs=(0.12, -0.12, -0.1, 0.1))
    elif state == "waiting":
        kw = dict(hy=0.35 * math.sin(p), look=math.sin(p), tail=0.4 * math.sin(2 * p))
    elif state == "running":
        a = 0.55 * math.sin(p)
        kw = dict(legs=(-a, a, a, -a), lift=-5 * (1 - math.cos(a)), roll=0.03 * math.sin(p), hr=-0.05, tail=0.6 * math.sin(2 * p))
    elif state == "review":
        kw = dict(hy=-0.32, hp=0.32 + 0.06 * math.sin(p), look=-0.5)
    parts = pig_parts(**kw)
    P.shadow(under, (kw.get("dx", 0.0), 0, 0), P.footprint(4.8, 10.5, kw.get("yaw", FRONT_YAW)), kw.get("lift", 0.0))
    common(state, f, parts, over)
    if state == "failed":
        stars_ring(over, parts, f)
    return P.render(parts, under, over, outline=(86, 40, 52))


# ================================================================== chicken ==============
WHITE = [(150, 150, 146), (176, 176, 170), (198, 198, 192), (216, 216, 210), (230, 230, 224), (240, 240, 236), (248, 248, 244), (255, 255, 252)]
YEL = [(170, 110, 20), (200, 140, 30), (226, 168, 48), (240, 192, 70), (250, 214, 100)]
RED = [(130, 22, 26), (166, 32, 34), (196, 48, 44), (220, 70, 60), (236, 96, 84)]
CH_EYE = (26, 20, 18)


def chicken_head_tex(eyes: str) -> P.Tex:
    def tex(face, u, v, W, H):
        if face == "front":
            for ex in (1, W - 5):
                if ex <= u < ex + 4 and 6 <= v < 10:
                    x, y = u - ex, v - 6
                    if eyes == "blink":
                        return CH_EYE if y == 3 else None
                    if eyes == "happy":
                        return CH_EYE if (y == 1 and x in (1, 2)) or (y == 2 and x in (0, 3)) else None
                    if eyes == "x":
                        return CH_EYE if x == y or x == 3 - y else None
                    if eyes == "wide":
                        return (250, 250, 250) if (x, y) == (1, 1) else CH_EYE
                    return (200, 200, 200) if (x, y) == (1, 1) else CH_EYE
        return None
    return tex


def chicken_parts(yaw=FRONT_YAW, lift=0.0, dx=0.0, sc=(1.0, 1.0, 1.0), roll=0.0, pitch=0.0, hy=0.0, hp=0.0, hr=0.0, hz=0.0,
                  legs=(0.0, 0.0), wings=(0.0, 0.0), eyes="open") -> list[P.Part]:
    root = P.Rig(P.chain(P.rot_y(yaw), P.scale(*sc)), (dx, lift, 0.0))
    hips = root.child((0, 5, -2), P.chain(P.rot_z(roll), P.rot_x(pitch)))
    parts = [hips.box("body", (0, 4.5, -0.5), (4.5, 4.5, 6), _shade_ends, WHITE, 1)]
    neck = hips.child((0, 9, 5 + hz), P.chain(P.rot_y(hy), P.rot_x(hp), P.rot_z(hr)))
    parts.append(neck.box("head", (0, 3.5, 0.5), (3, 4.5, 2.33), chicken_head_tex(eyes), WHITE, 0))
    parts.append(neck.box("beak", (0, 3.33, 4.33), (3, 1.33, 1.5), None, YEL, 2))
    parts.append(neck.box("wattle", (0, 1.17, 3.83), (1.5, 1.17, 1.0), None, RED, 3))
    for k, x in enumerate((-4.2, 4.2)):
        sgn = -1 if x < 0 else 1
        wing = hips.child((x, 8.3, -0.5), P.rot_z(sgn * wings[k]))
        parts.append(wing.box(f"wing{k}", (sgn * 0.5, -2.67, 0), (0.67, 2.67, 4), lambda *_: -0.06, WHITE, 4 + k))
    for k, x in enumerate((-1.67, 1.67)):
        leg = root.child((x, 5, -1.5), P.rot_x(legs[k]))
        parts.append(leg.box(f"leg{k}", (0, -2.5, 0), (0.5, 2.5, 0.5), None, YEL, 6 + k))
        parts.append(leg.box(f"foot{k}", (0, -4.67, 0.83), (1.17, 0.33, 1.5), None, YEL, 8 + k))
    return parts


def chicken_frame(state: str, f: int) -> Image.Image:
    under, over = P.FX(), P.FX()
    p = phase(state, f)
    kw: KW = {}
    if state == "idle":
        kw = dict(sc=(1, 1 + 0.02 * math.sin(p), 1), hp=0.05 * math.sin(p), hy=[0, 0, 0.2, 0.2, 0, 0][f], wings=(0.03, 0.03))
    elif state in WALK:
        a = 0.6 * math.sin(p)
        kw = dict(yaw=SIDE_YAW * facing(state), lift=-5 * (1 - math.cos(a)), legs=(-a, a), hz=0.9 * math.sin(2 * p),
                  hp=-0.1 * math.sin(2 * p), roll=0.03 * math.sin(p), wings=(0.08, 0.08))
        walk_dust(under, f, facing(state), 7)
    elif state == "waving":
        w = math.sin(p)
        kw = dict(wings=(0.05, 1.0 + 0.45 * w), roll=-0.06, hr=0.12 * w, eyes="happy")
    elif state == "jumping":
        lift = [0.0, 2.2, 5.0, 6.0, 3.4, 0.0][f]
        sy = [0.86, 1.1, 1.03, 1.0, 1.03, 0.9][f]
        fl = [0.15, 1.1, 0.4, 1.15, 0.5, 0.1][f]
        t = [0.0, 0.3, 0.6, 0.6, 0.35, 0.0][f]
        sx = 1 + (1 - sy) * 0.5
        kw = dict(lift=lift, sc=(sx, sy, sx), wings=(fl, fl), legs=(t, t), eyes="happy" if f == 3 else "open")
    elif state == "failed":
        kw = dict(lift=[0.0, 0.0, 2.2, 1.0, 0.0, 0.0][f], sc=(1, [1, 0.9, 1.08, 1.02, 0.94, 1][f], 1),
                  wings=([0.05, 0.3, 1.3, 0.9, 0.35, 0.1][f],) * 2, eyes=["open", "wide", "wide", "wide", "x", "x"][f],
                  hp=[0, -0.15, -0.2, -0.1, 0.1, 0.15][f])
    elif state == "waiting":
        kw = dict(hy=[0.0, 0.42, 0.42, -0.42, -0.42, 0.0][f], hp=0.04)
    elif state == "running":
        a = 0.7 * math.sin(p)
        fl = 0.5 + 0.35 * abs(math.sin(2 * p))
        kw = dict(legs=(-a, a), lift=-5 * (1 - math.cos(a)), wings=(fl, fl), roll=0.04 * math.sin(p), hz=0.6 * math.sin(2 * p))
    elif state == "review":
        kw = dict(hy=-0.3, hp=[0.3, 0.75, 0.3, 0.7, 0.3, 0.55][f], hz=[0, 1.0, 0, 0.9, 0, 0.6][f])
    parts = chicken_parts(**kw)
    P.shadow(under, (kw.get("dx", 0.0), 0, 0), P.footprint(4.8, 7.5, kw.get("yaw", FRONT_YAW)), kw.get("lift", 0.0))
    common(state, f, parts, over)
    if state == "failed" and f >= 2:
        cx, cy = body_center(parts, ("body",))
        age = f - 2
        for k in range(6):
            a = k * TAU / 6 + 0.4
            r = 9 + age * 4
            P.feather(over, cx + math.cos(a) * r, cy + math.sin(a) * r * 0.6 + age * 2, 255 - age * 50, flip=k % 2 == 0)
    return P.render(parts, under, over, outline=(96, 96, 90))


# ================================================================== slime ================
SHELL = [(52, 120, 44), (66, 146, 54), (84, 170, 66), (104, 190, 80), (126, 206, 98), (150, 220, 120), (178, 234, 148), (206, 244, 182)]
CORE = [(30, 86, 30), (38, 104, 36), (48, 122, 44), (60, 140, 52), (74, 156, 62), (90, 170, 74)]
SL_FACE = (18, 46, 20)
SLIME_GROUND = 90.0


def slime_core_tex(eyes: str, look: float) -> P.Tex:
    def tex(face, u, v, W, H):
        if face != "front":
            return None
        sh = round(look)
        if eyes == "x":  # bold 2-px X eyes and a wobbly frown, on a lighter core for contrast
            for ex in (3 + sh, 13 + sh):
                if ex <= u < ex + 6 and 5 <= v < 11:
                    x, y = u - ex, v - 5
                    return SL_FACE if (x - y) in (0, 1) or (x + y) in (4, 5) else 0.25
            if (8 + sh <= u < 14 + sh and v == 14) or (u in (8 + sh, 13 + sh) and v == 15) or (u in (10 + sh, 11 + sh) and v == 13):
                return SL_FACE
            return 0.22
        for ex in (4 + sh, 14 + sh):
            if ex <= u < ex + 4 and 5 <= v < 10:
                x, y = u - ex, v - 5
                if eyes == "blink":
                    return SL_FACE if y == 4 else 0.1
                if eyes == "x":
                    return SL_FACE if x == min(3, y) or x == max(0, 3 - y) else 0.1
                if eyes == "happy":
                    return SL_FACE if (y == 2 and x in (1, 2)) or (y == 3 and x in (0, 3)) else 0.1
                if eyes == "down":
                    return SL_FACE if y >= 2 else 0.1
                return SL_FACE
        if 9 + sh <= u < 13 + sh and 13 <= v < 15:
            return SL_FACE
        return None
    return tex


def slime_shell_tex(face, u, v, W, H):
    if face == "front" and 2 <= u <= 4 and 2 <= v <= 3:
        return P.Glow((236, 252, 226))
    if u <= 0 or v <= 0 or u >= W - 1 or v >= H - 1:
        return 0.16
    return None


def slime_alpha(clear: float = 1.0) -> P.Alpha:
    def a(face, u, v, W, H):
        edge = u <= 0 or v <= 0 or u >= W - 1 or v >= H - 1
        return 0.82 if edge else 0.42 * clear
    return a


def slime_parts(yaw=FRONT_YAW, lift=0.0, dx=0.0, sc=(1.0, 1.0, 1.0), roll=0.0, pitch=0.0, cdy=0.0, cdx=0.0,
                eyes="open", look=0.0, clear=1.0) -> list[P.Part]:
    root = P.Rig(P.chain(P.rot_y(yaw), P.rot_z(roll), P.rot_x(pitch), P.scale(*sc)), (dx, lift, 0.0))
    return [root.box("shell", (0, 6.33, 0), (6.33, 6.33, 6.33), slime_shell_tex, SHELL, 1, alpha=slime_alpha(clear)),
            root.box("head", (cdx, 4.0 + cdy, 1.0), (3.67, 3.67, 3.67), slime_core_tex(eyes, look), CORE, 0)]


WALK_SY = [1.0, 0.82, 0.9, 1.16, 1.1, 1.04, 1.0, 0.98, 0.98, 1.0, 1.03, 1.06, 0.78, 0.9, 1.04, 1.0]
WALK_LIFT = [0.0, 0.0, 0.0] + [4.4 * math.sin(math.pi * (k + 1) / 10) for k in range(9)] + [0.0, 0.0, 0.0, 0.0]


def slime_frame(state: str, f: int) -> Image.Image:
    P.set_ground(SLIME_GROUND)
    under, over = P.FX(), P.FX()
    p = phase(state, f)
    kw: KW = {}

    def sq(sy: float) -> tuple[float, float, float]:
        sx = 1 + (1 - sy) * 0.6
        return (sx, sy, sx)

    if state == "idle":
        kw = dict(sc=sq(1 + 0.04 * math.sin(p)), cdy=0.3 * math.sin(p - 1.2), look=0.6 * math.sin(p))
    elif state in WALK:
        sy = WALK_SY[f]
        kw = dict(yaw=SIDE_YAW * facing(state), lift=WALK_LIFT[f], sc=sq(sy), cdy=-0.6 * (sy - 1) * 3 if f in (1, 12) else 0.4 * (sy - 1) * 3,
                  pitch=0.06 if 3 <= f <= 11 else 0.0, look=0.8)
        for start in (12,):
            age = (f - start) % WALK_N
            if age < 4:
                for side in (-1, 1):
                    gx, gy = P.project((side * 7.0, 0, 3))
                    P.puff(under, gx + side * age * 1.5, gy - age, 1.6 + age * 0.6, 190 - age * 45)
    elif state == "waving":
        w = math.sin(p)
        kw = dict(roll=0.12 * w, sc=sq(1 + 0.05 * math.sin(2 * p)), cdx=0.4 * w, eyes="happy")
    elif state == "jumping":
        kw = dict(lift=[0.0, 1.5, 5.8, 7.4, 4.0, 0.0][f], sc=sq([0.7, 1.25, 1.08, 0.98, 1.06, 0.75][f]),
                  cdy=[-0.5, -0.8, -0.3, 0.3, 0.6, -0.4][f], eyes="happy" if f in (2, 3) else "open")
    elif state == "failed":
        sy = [1.0, 0.85, 0.7, 0.56, 0.6, 0.8][f]
        sx = [1.0, 1.1, 1.2, 1.3, 1.28, 1.12][f]
        kw = dict(sc=(sx, sy, sx), eyes="x" if f >= 2 else "blink", cdy=-0.4 if f >= 2 else 0.0, clear=0.5 if f >= 2 else 1.0)
    elif state == "waiting":
        kw = dict(sc=sq(1 + 0.03 * math.sin(2 * p)), look=1.2 * math.sin(p), cdy=0.2 * math.sin(p))
    elif state == "running":
        lift = 1.8 * abs(math.sin(p))
        kw = dict(lift=lift, sc=sq(1.06 if lift > 0.6 else 0.86), cdy=0.3 * math.sin(2 * p))
    elif state == "review":
        kw = dict(pitch=0.14, eyes="down", look=-0.8, cdy=-0.2)
    parts = slime_parts(**kw)
    sc = kw.get("sc", (1, 1, 1))
    P.shadow(under, (0, 0, 0), P.footprint(6.6 * sc[0], 6.6 * sc[2], kw.get("yaw", FRONT_YAW)), kw.get("lift", 0.0))
    common(state, f, parts, over, ("shell",))
    if state == "failed" and f >= 2:
        cx, cy = body_center(parts, ("shell",))
        age = f - 2
        for k in range(6):
            a = math.pi + k * math.pi / 5
            r = 12 + age * 4
            P.drop(over, cx + math.cos(a) * r * 1.4, cy + math.sin(a) * r * 0.8 + age * age * 1.5, 255 - age * 45)
    if state == "failed" and f >= 2:
        # dizzy face drawn on top of the jelly so it still reads when the pet is scaled down
        x0, y0, x1, y1 = gbbox(parts, ("head",))
        cx, cy = (x0 + x1) / 2, y0 + (y1 - y0) * 0.42
        for ex in (cx - 5, cx + 5):
            for k in range(-2, 3):
                for t in (0, 1):
                    over.put(ex + k + t, cy + k, (14, 38, 16, 255))
                    over.put(ex + k + t, cy - k, (14, 38, 16, 255))
        for k in range(-3, 4):
            over.put(cx + k, cy + 6 - (1 if abs(k) < 2 else 0), (14, 38, 16, 255))
    img = P.render(parts, under, over, outline=(26, 70, 26))
    P.set_ground(93.0)
    return img


# ================================================================== bee ==================
BEE_Y = [(150, 100, 10), (186, 130, 20), (214, 160, 30), (234, 186, 46), (246, 204, 70), (252, 220, 100), (255, 234, 140), (255, 244, 180)]
BEE_BROWN = (78, 48, 24)
BEE_DARK = [(30, 22, 16), (44, 32, 24), (60, 44, 32), (80, 60, 44)]
WINGS = [(170, 196, 220), (190, 214, 236), (206, 228, 246), (224, 240, 252), (240, 248, 255)]
BEE_EYE = (22, 16, 12)


def bee_tex(eyes: str, angry: bool) -> P.Tex:
    def tex(face, u, v, W, H):
        if face == "front":
            for ex in (3, 20):
                if ex <= u < ex + 7 and 10 <= v < 21:
                    x, y = u - ex, v - 10
                    col = (170, 30, 30) if angry else BEE_EYE
                    if eyes == "blink":
                        return col if y >= 8 else None
                    if eyes == "happy":
                        return col if (y == 5 and 2 <= x <= 4) or (y == 6 and x in (1, 5)) or (y == 7 and x in (0, 6)) else None
                    if eyes == "x":
                        return col if abs(x - y * 6 / 10) < 1.1 or abs(x - (6 - y * 6 / 10)) < 1.1 else None
                    if eyes == "down":
                        return col if y >= 3 else None
                    if (x, y) in ((1, 1), (2, 1), (1, 2)):
                        return (250, 250, 240)
                    return col
            if angry and 6 <= v <= 7 and (3 <= u <= 9 or 20 <= u <= 26):
                return BEE_BROWN
            return None
        if face == "back":
            return BEE_BROWN if v >= H // 2 - 4 and v <= H // 2 + 4 and abs(u - W / 2) < 6 else None
        if face == "right":
            fr = u / W
        elif face == "left":
            fr = 1 - u / W
        elif face == "top":
            fr = 1 - v / H
        else:
            fr = v / H
        if 0.3 <= fr < 0.46 or 0.62 <= fr < 0.78 or fr >= 0.93:
            return BEE_BROWN
        return None
    return tex


def bee_parts(yaw=FRONT_YAW, lift=0.0, dx=0.0, sc=(1.0, 1.0, 1.0), roll=0.0, pitch=0.0, hy=0.0, wing=0.0,
              eyes="open", angry=False) -> list[P.Part]:
    root = P.Rig(P.chain(P.rot_y(yaw), P.scale(*sc)), (dx, lift, 0.0))
    body = root.child((0, 11, 0), P.chain(P.rot_y(hy), P.rot_z(roll), P.rot_x(pitch)))
    parts = [body.box("head", (0, 0, 0), (5, 5, 6.67), bee_tex(eyes, angry), BEE_Y, 0),
             body.box("stinger", (0, -0.67, -7.33), (0.5, 0.5, 0.67), None, BEE_DARK, 1)]
    for k, x in enumerate((-1.67, 1.67)):
        ant = body.child((x, 5, 5.33), P.rot_x(-0.55))
        parts.append(ant.box(f"ant{k}", (0, 1.33, 0), (0.33, 1.33, 0.33), None, BEE_DARK, 2 + k))
    for k, sgn in enumerate((-1, 1)):
        wr = body.child((sgn * 1.33, 5.17, -1.0), P.rot_z(sgn * wing))
        parts.append(wr.box(f"wing{k}", (sgn * 2.67, 0.17, 0), (2.67, 0.17, 3.33), None, WINGS, 4 + k, alpha=0.5))
    for k, (x, z) in enumerate(((-2, 3), (2, 3), (-2, 0), (2, 0), (-2, -3), (2, -3))):
        parts.append(body.box(f"leg{k}", (x, -5.5, z), (0.33, 0.5, 0.33), None, BEE_DARK, 6 + k))
    return parts


def bee_frame(state: str, f: int) -> Image.Image:
    under, over = P.FX(), P.FX()
    p = phase(state, f)
    flash = 0.0
    wing = 0.95 if f % 2 == 0 else -0.25
    kw: KW = dict(wing=wing)
    if state == "idle":
        kw.update(lift=0.8 * math.sin(p), pitch=0.05 * math.sin(p), hy=0.05 * math.sin(p))
    elif state in WALK:
        kw.update(yaw=SIDE_YAW * facing(state), lift=0.9 * math.sin(2 * p), pitch=0.16, roll=0.04 * math.sin(p))
        gx, gy = P.project((-facing(state) * 7.5, 11, 0))
        for k in range(3):
            P.speed(over, gx - facing(state) * 1, gy - 4 + k * 4 + (f % 2), 5 + (k + f) % 3, 150, trail_left=facing(state) > 0)
    elif state == "waving":
        w = math.sin(p)
        kw.update(roll=0.2 * w, hy=0.15 * w, dx=0.8 * w, eyes="happy", lift=0.5 * abs(w))
    elif state == "jumping":
        kw.update(roll=TAU * f / 6, lift=[0.0, 1.6, 3.0, 3.6, 2.2, 0.6][f], eyes="happy")
    elif state == "failed":
        kw.update(pitch=[0.0, -0.3, 0.32, 0.12, -0.08, 0.0][f], sc=(1, 1, [1, 1, 0.84, 1, 1, 1][f]),
                  lift=[0.0, 0.3, 0.0, -1.5, -2.5, -1.0][f], roll=[0, 0, 0, 0.15, -0.12, 0.05][f],
                  eyes=["open", "open", "x", "x", "x", "blink"][f], angry=f < 3)
        flash = [0, 0, 0.45, 0, 0, 0][f]
    elif state == "waiting":
        kw.update(hy=0.4 * math.sin(p), lift=0.6 * math.sin(2 * p))
    elif state == "running":
        kw.update(dx=1.2 * math.sin(2 * p), roll=0.12 * math.sin(2 * p), pitch=0.12, lift=0.6 * math.sin(p))
    elif state == "review":
        kw.update(hy=-0.25, pitch=0.28, eyes="down", lift=-1.5 + 0.3 * math.sin(p))
    parts = bee_parts(**kw)
    P.shadow(under, (kw.get("dx", 0.0), 0, 0), P.footprint(5, 6.67, kw.get("yaw", FRONT_YAW)), 6 + kw.get("lift", 0.0), alpha=(60, 34))
    common(state, f, parts, over)
    if state == "failed" and f >= 3:
        stars_ring(over, parts, f)
    if state == "failed" and f == 2:
        x0, y0, x1, _ = gbbox(parts, ("head",))
        for k in range(5):
            P.spark(over, x1 + 2 + (k % 2) * 2, y0 + 6 + k * 4, 230)
    return P.render(parts, under, over, flash=flash, outline=(64, 40, 10), outline_soft=(150, 170, 190))


# ================================================================== enderman ============
ENDER = [(12, 9, 16), (18, 14, 24), (24, 19, 32), (32, 26, 42), (42, 34, 54), (54, 44, 68), (68, 56, 84), (84, 70, 102)]
EYE_OUT, EYE_IN = (204, 72, 240), (252, 196, 255)
GRASS = [(56, 110, 40), (70, 134, 50), (88, 158, 62), (110, 180, 76), (136, 200, 96)]
DIRT = [(84, 56, 36), (104, 70, 44), (124, 86, 54), (144, 102, 66), (160, 118, 80)]


def ender_head_tex(eyes: str, glow: float) -> P.Tex:
    def tex(face, u, v, W, H):
        if face == "front" and 9 <= v < 12:
            for ex in (2, 13):
                if ex <= u < ex + 6:
                    x = u - ex
                    if eyes == "closed":
                        return (90, 40, 110) if v == 11 else None
                    if eyes == "angry":
                        return P.Glow((255, 120, 200) if 2 <= x <= 3 else (230, 40, 120))
                    k = 0.75 + 0.25 * glow
                    c = EYE_IN if (2 <= x <= 3 and v == 10) else EYE_OUT
                    return P.Glow((int(c[0] * k), int(c[1] * k), int(c[2] * k)))
            return -0.05
        return None
    return tex


def ender_limb_tex(face, u, v, W, H):
    """Lit edge on the light-facing corner so the thin limbs still read when the pet is scaled down."""
    if (face == "front" and u == 0) or (face == "left" and u == W - 1):
        return 0.3
    return None


def grass_tex(face, u, v, W, H):
    if face == "top":
        return None
    if face == "bottom":
        return (124, 86, 54)
    if v <= 2 or (v == 3 and (u * 7) % 3 == 0):
        return (88, 158, 62)
    return DIRT[int(P.hash2(u, v, 5) * len(DIRT))]


def enderman_parts(yaw=FRONT_YAW, lift=0.0, dx=0.0, sc=(1.0, 1.0, 1.0), roll=0.0, pitch=0.0, hy=0.0, hp=0.0, hr=0.0,
                   arms=(0.0, 0.0), spread=(0.0, 0.0), legs=(0.0, 0.0), eyes="open", glow=1.0, jaw=0.0,
                   block=False) -> list[P.Part]:
    root = P.Rig(P.chain(P.rot_y(yaw), P.scale(*sc)), (dx, lift, 0.0))
    hips = root.child((0, 12, 0), P.chain(P.rot_z(roll), P.rot_x(pitch)))
    parts = [hips.box("body", (0, 4.5, 0), (2.67, 4.5, 1.67), _shade_ends, ENDER, 1)]
    neck = hips.child((0, 9, 0), P.chain(P.rot_y(hy), P.rot_x(hp), P.rot_z(hr)))
    if jaw > 0:
        parts.append(neck.box("head", (0, 4.67, 0), (3.5, 2.33, 3.5), ender_head_tex(eyes, glow), ENDER, 0))
        parts.append(neck.box("jaw", (0, 1.17 - jaw, 0), (3.5, 1.17, 3.5), None, ENDER, 2))
        parts.append(neck.box("mouth", (0, 2.33 - jaw / 2, 0.3), (3.0, jaw / 2 + 0.2, 3.0), lambda *a: P.Glow((60, 10, 54)), ENDER, 3))
    else:
        parts.append(neck.box("head", (0, 3.5, 0), (3.5, 3.5, 3.5), ender_head_tex(eyes, glow), ENDER, 0))
    for k, x in enumerate((-3.67, 3.67)):
        sgn = -1 if x < 0 else 1
        arm = hips.child((x, 8.67, 0), P.chain(P.rot_x(arms[k]), P.rot_z(sgn * spread[k])))
        parts.append(arm.box(f"arm{k}", (0, -6, 0), (1, 6, 1), ender_limb_tex, ENDER, 4 + k))
    for k, x in enumerate((-1.33, 1.33)):
        leg = root.child((x, 12, 0), P.rot_x(legs[k]))
        parts.append(leg.box(f"leg{k}", (0, -6, 0), (1, 6, 1), ender_limb_tex, ENDER, 6 + k))
    if block:
        parts.append(hips.box("block", (0, 4.33, 11.0), (2.67, 2.67, 2.67), grass_tex, GRASS, 8))
    return parts


def ender_particles(over: P.FX, parts: list[P.Part], f: int, n: int, k0: int = 0, alpha: int = 220) -> None:
    x0, y0, x1, y1 = gbbox(parts, ("body", "head"))
    for k in range(k0, k0 + n):
        sx = x0 - 4 + P.hash2(k, 3, 11) * (x1 - x0 + 8)
        sy = y1 - P.hash2(k, 5, 13) * (y1 - y0) - (f * 3 + k * 5) % 18
        P.portal(over, sx, max(MARGIN, sy), alpha - ((f * 3 + k * 5) % 18) * 9)


def enderman_frame(state: str, f: int) -> Image.Image:
    under, over = P.FX(), P.FX()
    p = phase(state, f)
    flash, dissolve = 0.0, 0.0
    kw: KW = {}
    if state == "idle":
        kw = dict(roll=0.02 * math.sin(p), arms=(0.05 * math.sin(p), -0.05 * math.sin(p)), glow=0.6 + 0.4 * math.sin(p), hy=0.06 * math.sin(p))
    elif state in WALK:
        a = 0.42 * math.sin(p)
        kw = dict(yaw=SIDE_YAW * facing(state), legs=(-a, a), arms=(0.36 * math.sin(p), -0.36 * math.sin(p)),
                  lift=-12 * (1 - math.cos(a)), roll=0.02 * math.sin(2 * p), hp=0.03 * math.cos(2 * p))
        walk_dust(under, f, facing(state), 3.5)
    elif state == "waving":
        w = math.sin(p)
        kw = dict(arms=(0.05, -2.3 - 0.22 * w), spread=(0.0, 0.18 + 0.12 * w), hr=0.1 * w, hy=-0.1)
    elif state == "jumping":
        dissolve = [0.0, 0.35, 0.7, 0.5, 0.2, 0.0][f]
        flash = [0.0, 0.55, 0.3, 0.45, 0.15, 0.0][f]
        kw = dict(lift=[0.0, 0.0, 0.6, 1.2, 0.6, 0.0][f], arms=(0.2, -0.2), spread=(0.25, 0.25))
    elif state == "failed":
        kw = dict(jaw=[0.0, 0.7, 1.3, 1.5, 1.3, 0.7][f], hp=[0, -0.12, -0.22, -0.25, -0.22, -0.12][f],
                  dx=[0, 0.25, -0.25, 0.3, -0.3, 0.15][f], eyes="angry" if f else "open", spread=(0.3, 0.3), arms=(-0.15, -0.15))
    elif state == "waiting":
        kw = dict(block=True, arms=(-1.2, -1.2), hy=0.3 * math.sin(p), hp=0.12, glow=0.7 + 0.3 * math.sin(p))
    elif state == "running":
        a = 0.55 * math.sin(p)
        kw = dict(legs=(-a, a), arms=(0.5 * math.sin(p), -0.5 * math.sin(p)), lift=-12 * (1 - math.cos(a)), roll=0.03 * math.sin(p))
    elif state == "review":
        kw = dict(arms=(-1.0, -1.0), hp=0.35 + 0.04 * math.sin(p), hy=0.05 * math.sin(p))
    parts = enderman_parts(**kw)
    P.shadow(under, (kw.get("dx", 0.0), 0, 0), P.footprint(4.5, 2.5, kw.get("yaw", FRONT_YAW)), kw.get("lift", 0.0))
    if state == "review":
        # book held in both hands instead of on the ground
        x0, y0, x1, y1 = gbbox(parts, ("arm0", "arm1"))
        P.book(over, int((x0 + x1) / 2 - 11), int(y1 - 10), f)
    else:
        common(state, f, parts, over)
    if state == "idle":
        ender_particles(over, parts, f, 3)
    elif state == "jumping":
        x0, y0, x1, y1 = gbbox(parts, ("body", "head"))
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        r = [5, 11, 17, 20, 12, 6][f]
        for k in range(10):
            a = k * TAU / 10 + f * 0.4
            P.portal(over, cx + math.cos(a) * r, cy + math.sin(a) * r * 1.3, 240 if f in (1, 2, 3) else 150)
    elif state in ("failed", "running") or state in WALK:
        ender_particles(over, parts, f, 4 if state == "failed" else 2, alpha=240)
    return P.render(parts, under, over, flash=flash, flash_rgb=(190, 90, 255), outline=(128, 94, 176), dissolve=dissolve, keep=(0,))


# ================================================================== lantern =============
COPPER = [(70, 38, 24), (96, 54, 32), (124, 72, 40), (150, 92, 50), (176, 114, 62), (198, 136, 78), (216, 160, 98), (232, 186, 124)]
PATINA = (72, 176, 150)
LFACE = (70, 38, 22)


def _glass_rgb(t: float, g: float) -> tuple[int, int, int]:
    if g < 0.12:
        return (86, 90, 100)
    hot, warm, edge = (255, 238, 176), (246, 184, 96), (206, 126, 60)
    a, b, k = (hot, warm, t / 0.55) if t < 0.55 else (warm, edge, min(1.0, (t - 0.55) / 0.45))
    dim = 0.35 + 0.65 * g
    return (int((a[0] * (1 - k) + b[0] * k) * dim), int((a[1] * (1 - k) + b[1] * k) * dim), int((a[2] * (1 - k) + b[2] * k) * dim))


def glass_tex(eyes: str, glow: float, look: float) -> P.Tex:
    def tex(face, u, v, W, H):
        if face == "front":
            sh = round(look)
            for ex in (8 + sh, 15 + sh):
                if ex <= u < ex + 3 and 10 <= v < 14:
                    x, y = u - ex, v - 10
                    if eyes == "blink":
                        if y == 3:
                            return LFACE
                    elif eyes == "happy":
                        if (y == 1 and x == 1) or (y == 2 and x in (0, 2)):
                            return LFACE
                    elif eyes == "sad":
                        if (y == 2 and x in (0, 1, 2)) or (y == 1 and x == (2 if ex < 12 else 0)):
                            return LFACE
                    elif eyes == "down":
                        if y >= 2:
                            return LFACE
                    else:
                        return LFACE
            if eyes != "sad" and ((v == 17 and 11 + sh <= u <= 14 + sh) or (v == 16 and u in (10 + sh, 15 + sh))):
                return LFACE
            if eyes == "sad" and ((v == 16 and 11 + sh <= u <= 14 + sh) or (v == 17 and u in (10 + sh, 15 + sh))):
                return LFACE
            if glow >= 0.12 and v == 15 and (5 + sh <= u <= 6 + sh or 19 + sh <= u <= 20 + sh):
                return P.Glow((240, 140, 120))
        elif face in P.SIDES and u == W // 2:
            return COPPER[3]
        t = max(abs(u - (W - 1) / 2) / (W / 2), abs(v - (H - 1) / 2) / (H / 2))
        return P.Glow(_glass_rgb(min(1.0, t), glow))
    return tex


def copper_tex(face, u, v, W, H):
    if P.hash2(u, v, 41) < 0.06:
        return PATINA
    return None


def lantern_parts(yaw=FRONT_YAW, lift=0.0, dx=0.0, sc=(1.0, 1.0, 1.0), roll=0.0, pitch=0.0, swing=0.0, feet=(0.0, 0.0),
                  eyes="open", glow=1.0, look=0.0) -> list[P.Part]:
    root = P.Rig(P.chain(P.rot_y(yaw), P.scale(*sc)), (dx, lift, 0.0))
    body = root.child((0, 0, 0), P.chain(P.rot_z(roll), P.rot_x(pitch)))
    parts: list[P.Part] = []
    for k, x in enumerate((-2.67, 2.67)):
        parts.append(root.box(f"foot{k}", (x, 0.67 + feet[k], 0.67), (1.0, 0.67, 1.33), None, COPPER, 10 + k))
    parts += [body.box("base", (0, 2.0, 0), (5, 0.67, 5), copper_tex, COPPER, 1),
              body.box("head", (0, 7.33, 0), (4.33, 4.67, 4.33), glass_tex(eyes, glow, look), COPPER, 0),
              body.box("cap", (0, 12.67, 0), (5, 0.67, 5), copper_tex, COPPER, 2),
              body.box("roof", (0, 14.0, 0), (3.33, 0.67, 3.33), copper_tex, COPPER, 3),
              body.box("knob", (0, 15.33, 0), (0.67, 0.67, 0.67), None, COPPER, 4)]
    for k, (x, z) in enumerate(((-4.33, 4.33), (4.33, 4.33), (-4.33, -4.33), (4.33, -4.33))):
        parts.append(body.box(f"post{k}", (x, 7.33, z), (0.67, 4.67, 0.67), None, COPPER, 5 + k))
    hd = body.child((0, 16.0, 0), P.rot_z(swing))
    parts += [hd.box("hpost0", (-2.0, 1.33, 0), (0.33, 1.33, 0.33), None, COPPER, 12),
              hd.box("hpost1", (2.0, 1.33, 0), (0.33, 1.33, 0.33), None, COPPER, 13),
              hd.box("hbar", (0, 2.67, 0), (2.33, 0.33, 0.33), None, COPPER, 14)]
    return parts


def lantern_frame(state: str, f: int) -> Image.Image:
    under, over = P.FX(), P.FX()
    p = phase(state, f)
    flick = 0.08 * (P.hash2(f, len(state), 3) - 0.5)
    kw: KW = {}
    if state == "idle":
        kw = dict(glow=0.82 + 0.12 * math.sin(p) + flick, swing=0.15 * math.sin(p), lift=0.2 * math.sin(p), look=0.6 * math.sin(p))
    elif state in WALK:
        hop = max(0.0, math.sin(2 * p))
        kw = dict(yaw=SIDE_YAW * facing(state), lift=1.4 * hop, roll=0.06 * math.sin(p), pitch=0.05, swing=0.35 * math.sin(p - 0.7),
                  feet=(0.5 * max(0.0, math.sin(p)), 0.5 * max(0.0, -math.sin(p))), glow=0.85 + flick, look=0.8)
        if f % 4 == 1:
            x0, y0, x1, y1 = gbbox(lantern_parts(**kw), ("head",))
            ex = x0 - 3 if facing(state) > 0 else x1 + 3
            P.spark(over, ex, y0 + 4 + (f % 8), 220)
    elif state == "waving":
        w = math.sin(p)
        kw = dict(roll=0.1 * w, swing=0.5 * math.sin(p - 0.6), eyes="happy", glow=1.0)
    elif state == "jumping":
        sy = [0.88, 1.1, 1.04, 1.0, 1.03, 0.9][f]
        sx = 1 + (1 - sy) * 0.5
        kw = dict(lift=[0.0, 1.8, 4.4, 5.4, 3.0, 0.0][f], sc=(sx, sy, sx), swing=[0, -0.3, -0.45, -0.1, 0.35, 0.2][f],
                  eyes="happy" if f in (2, 3) else "open", glow=1.0)
    elif state == "failed":
        g = [0.8, 0.5, 0.25, 0.06, 0.0, 0.3][f]
        kw = dict(glow=g, eyes="open" if f < 2 else "sad", roll=[0, 0.04, -0.04, 0.02, 0, 0][f], swing=[0, 0.2, -0.2, 0.1, 0, 0][f],
                  pitch=[0, 0, 0.05, 0.1, 0.12, 0.08][f])
    elif state == "waiting":
        kw = dict(look=1.2 * math.sin(p), glow=0.75 + 0.15 * math.sin(p), swing=0.1 * math.sin(p))
    elif state == "running":
        hop = abs(math.sin(p))
        kw = dict(lift=1.2 * hop, feet=(0.5 * max(0.0, math.sin(p)), 0.5 * max(0.0, -math.sin(p))), swing=0.3 * math.sin(p - 0.6),
                  roll=0.05 * math.sin(p), glow=0.9 + flick)
    elif state == "review":
        kw = dict(pitch=0.16, eyes="down", glow=1.0, swing=0.08 * math.sin(p))
    parts = lantern_parts(**kw)
    g = kw.get("glow", 1.0)
    cx, cy = P.project((kw.get("dx", 0.0), 0, 0))
    if g >= 0.12:
        P.glow_disc(under, cx, cy, 26, 7, (255, 190, 90), int(110 * g))
    P.shadow(under, (0, 0, 0), P.footprint(4.5, 4.5, kw.get("yaw", FRONT_YAW)), kw.get("lift", 0.0), alpha=(70, 40))
    common(state, f, parts, over)
    if state == "failed" and f >= 3:
        x0, y0, x1, _ = gbbox(parts, ("knob",))
        age = f - 3
        for k in range(3):
            P.puff(over, (x0 + x1) / 2 + math.sin(age + k) * 2, y0 - 3 - k * 4 - age * 3, 2 + k * 0.6, 170 - k * 40 - age * 20, dark=True)
    if state == "failed" and f == 5:
        x0, y0, x1, y1 = gbbox(parts, ("head",))
        P.spark(over, (x0 + x1) / 2, (y0 + y1) / 2, 255)
    return P.render(parts, under, over, outline=(54, 30, 18))


# ================================================================== registry / build =====
SPECIES: dict[str, dict[str, Any]] = {
    "creeper": dict(name="Creeper", desc="接近遊戲比例的苦力怕：立體方塊、四腳交替走路，失敗時會膨脹、閃光、冒煙。", frame=creeper_frame),
    "pig": dict(name="Pig", desc="粉紅色的豬：短腿小跑、會揮蹄子，失敗時頭暈冒星星。", frame=pig_frame),
    "chicken": dict(name="Chicken", desc="白色的雞：走路時頭一伸一縮、會拍翅膀，嚇到時羽毛亂飛。", frame=chicken_frame),
    "slime": dict(name="Slime", desc="半透明的史萊姆：一彈一彈地跳，裡面的臉看得到，失敗時攤平噴出黏液。", frame=slime_frame),
    "bee": dict(name="Bee", desc="毛茸茸的蜜蜂：半透明翅膀一直拍，揮手時會跳搖擺舞，跳躍時翻滾一圈。", frame=bee_frame),
    "enderman": dict(name="Enderman", desc="終界使者：長手長腳、紫色眼睛，跳躍時傳送，等待時抱著一塊草方塊。", frame=enderman_frame),
    "lantern": dict(name="Lantern", desc="原創的銅製小燈籠：發光的玻璃臉，提把會晃，失敗時火光熄滅再點亮。", frame=lantern_frame),
}


# Pet folders from earlier versions -> the species that replaced them (installers migrate these).
RETIRED = {"creeper-blocky": "creeper", "creeper-carved": "creeper", "creeper-tall": "creeper", "creeper-buddy": "creeper", "lantern-buddy": "lantern", "mc-pig": "pig", "mc-chicken": "chicken", "mc-slime": "slime", "mc-bee": "bee", "mc-enderman": "enderman"}


def frames_for(slug: str) -> dict[str, list[Image.Image]]:
    fn = SPECIES[slug]["frame"]
    out: dict[str, list[Image.Image]] = {}
    for s in STATES:
        fr: list[Image.Image] = []
        for f in range(nframes(s)):
            P.set_ground(93.0)
            try:
                fr.append(fn(s, f))
            finally:
                P.set_ground(93.0)
        out[s] = fr
    return out


def check(slug: str, frames: dict[str, list[Image.Image]]) -> list[str]:
    """Every frame non-blank and at least MARGIN grid pixels from each edge."""
    m = MARGIN * P.PX
    bad: list[str] = []
    for s, fr in frames.items():
        for i, im in enumerate(fr):
            bb = im.getchannel("A").getbbox()
            if not bb:
                bad.append(f"{slug}/{s}#{i}: blank")
            elif bb[0] < m or bb[1] < m or bb[2] > P.FRAME_W - m or bb[3] > P.FRAME_H - m:
                bad.append(f"{slug}/{s}#{i}: bbox {bb}")
    return bad


def build(slug: str) -> list[str]:
    """Render, validate, and only then write pets/<slug>/ and its preview. Returns the problems found."""
    sp = SPECIES[slug]
    frames = frames_for(slug)
    bad = check(slug, frames)
    if bad:
        return bad
    sheet = Image.new("RGBA", (COLS * P.FRAME_W, len(STATES) * P.FRAME_H), (0, 0, 0, 0))
    for r, s in enumerate(STATES):
        for c, im in enumerate(frames[s]):
            sheet.alpha_composite(im, (c * P.FRAME_W, r * P.FRAME_H))
    out = ROOT / "pets" / slug
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "spritesheet.png.tmp"
    sheet.save(tmp, format="PNG", optimize=True)
    tmp.replace(out / "spritesheet.png")
    (out / "pet.json").write_text(json.dumps({"id": slug, "displayName": sp["name"], "description": sp["desc"],
                                              "spritesheetPath": "spritesheet.png"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    preview(slug, frames)
    return []


DURATIONS = [70] * 14 + [60] * 2       # 16 steps = 1100 ms (GIF delays are in 10 ms units)


def _quantize(imgs: list[Image.Image], probes: list[int]) -> list[Image.Image]:
    w, h = imgs[0].size
    mosaic = Image.new("RGB", (w, h * len(probes)))
    for k, i in enumerate(probes):
        mosaic.paste(imgs[i], (0, h * k))
    pal = mosaic.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    return [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in imgs]


def preview(slug: str, frames: dict[str, list[Image.Image]]) -> None:
    """docs/pets/<slug>.gif: every state at 1:1 on one shared 1100 ms clock."""
    fp = Path(r"C:\Windows\Fonts\msjh.ttc")
    font = ImageFont.truetype(str(fp), 15) if fp.exists() else None
    cw, ch = P.FRAME_W, P.FRAME_H + 22
    out = []
    for step in range(WALK_N):
        img = Image.new("RGB", (cw * 5, ch * 2), (30, 32, 38))
        d = ImageDraw.Draw(img)
        for k, s in enumerate(STATES):
            fr = frames[s]
            im = fr[step * len(fr) // WALK_N]
            x, y = (k % 5) * cw, (k // 5) * ch
            img.paste(im, (x, y + 22), im)
            d.text((x + 6, y + 3), s, fill=(200, 200, 200), font=font)
        out.append(img)
    q = _quantize(out, [0, 3, 8, 11, 14])
    dst = ROOT / "docs" / "pets"
    dst.mkdir(parents=True, exist_ok=True)
    q[0].save(dst / f"{slug}.gif", save_all=True, append_images=q[1:], duration=DURATIONS, loop=0, optimize=True)


def overview(order: list[str]) -> None:
    """docs/pets.gif: all pets walking right (row 1) and their idle/wave/jump loops (row 2)."""
    sheets = {n: Image.open(ROOT / "pets" / n / "spritesheet.png").convert("RGBA") for n in order}
    W, H = P.FRAME_W, P.FRAME_H
    out = []
    for step in range(WALK_N):
        img = Image.new("RGB", (W * len(order), H), (30, 32, 38))
        for i, n in enumerate(order):
            fr = sheets[n].crop((step * W, H, step * W + W, 2 * H))
            img.paste(fr, (i * W, 0), fr)
        out.append(img)
    q = _quantize(out, [0, 5, 10])
    q[0].save(ROOT / "docs" / "pets.gif", save_all=True, append_images=q[1:], duration=DURATIONS, loop=0, optimize=True)


def hero_pixels(slug: str = "creeper") -> dict[tuple[int, int], tuple]:
    """48x52 logical pixels of the idle pose (CLI banner hero; same shape as the old head_pixels)."""
    im = SPECIES[slug]["frame"]("idle", 0).resize((48, 52), Image.Resampling.NEAREST)
    out: dict[tuple[int, int], tuple] = {}
    for y in range(52):
        for x in range(48):
            c = im.getpixel((x, y))
            if isinstance(c, tuple) and c[3] > 0:
                out[(x, y)] = c
    return out


if __name__ == "__main__":
    slugs = sys.argv[1:] or list(SPECIES)
    problems: list[str] = []
    for slug in slugs:
        bad = build(slug)
        problems += bad
        print("built", slug if not bad else f"{slug}: NOT written, {len(bad)} problems")
    for b in problems[:40]:
        print("  ", b)
    if problems:
        sys.exit(1)
    if not sys.argv[1:]:
        overview(list(SPECIES))
