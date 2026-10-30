"""Tiny orthographic box renderer for the HD pets (pure Python + Pillow, no numpy).

A pet is a handful of boxes placed with a small transform hierarchy. Every logical
pixel of the 96x104 grid casts one ray; the nearest box face is textured per texel
(TPU texels per model unit, so front faces map ~1:1 to grid pixels), lit by one fixed
light and quantised to the part's palette. Parts may be translucent (slime jelly, bee
wings) and texels may glow (eyes, lantern glass). A dark outline and darkened seams
between overlapping parts keep it reading as pixel art. Each logical pixel becomes a
PX x PX block of the 192x208 cell.
"""

from __future__ import annotations

import math
from typing import Callable, Optional, Union

from PIL import Image

RGB = tuple[int, int, int]
RGBA = tuple[int, int, int, int]
Vec = tuple[float, float, float]
Mat = tuple[Vec, Vec, Vec]

GRID_W, GRID_H, PX = 96, 104, 2
FRAME_W, FRAME_H = GRID_W * PX, GRID_H * PX
S = 3.0             # grid pixels per model unit
TPU = 3             # texels per model unit
CX = 48.0
GROUND = 93.0       # grid row of the ground line (per species: set_ground)
PITCH = math.radians(18)
_CP, _SP = math.cos(PITCH), math.sin(PITCH)
D_AX: Vec = (0.0, -_SP, -_CP)


def set_ground(y: float) -> None:
    global GROUND
    GROUND = float(y)


def _norm(v: Vec) -> Vec:
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


LIGHT = _norm((-0.55, 0.75, 0.45))
I3: Mat = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def rot_x(a: float) -> Mat:
    c, s = math.cos(a), math.sin(a)
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def rot_y(a: float) -> Mat:
    c, s = math.cos(a), math.sin(a)
    return ((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c))


def rot_z(a: float) -> Mat:
    c, s = math.cos(a), math.sin(a)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def scale(x: float, y: float, z: float) -> Mat:
    return ((x, 0.0, 0.0), (0.0, y, 0.0), (0.0, 0.0, z))


def mm(a: Mat, b: Mat) -> Mat:
    def row(i: int) -> Vec:
        return (a[i][0] * b[0][0] + a[i][1] * b[1][0] + a[i][2] * b[2][0],
                a[i][0] * b[0][1] + a[i][1] * b[1][1] + a[i][2] * b[2][1],
                a[i][0] * b[0][2] + a[i][1] * b[1][2] + a[i][2] * b[2][2])
    return (row(0), row(1), row(2))


def chain(*ms: Mat) -> Mat:
    out = I3
    for m in ms:
        out = mm(out, m)
    return out


def mv(m: Mat, v: Vec) -> Vec:
    return (m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
            m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
            m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2])


def add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def inv3(m: Mat) -> Mat:
    (a, b, c), (d, e, f), (g, h, i) = m
    A, B, C = e * i - f * h, -(d * i - f * g), d * h - e * g
    det = a * A + b * B + c * C
    return ((A / det, -(b * i - c * h) / det, (b * f - c * e) / det),
            (B / det, (a * i - c * g) / det, -(a * f - c * d) / det),
            (C / det, -(a * h - b * g) / det, (a * e - b * d) / det))


def project(p: Vec) -> tuple[float, float]:
    """World point -> grid coordinates (float)."""
    return CX + p[0] * S, GROUND - (p[1] * _CP - p[2] * _SP) * S


def hash2(x: int, y: int, s: int) -> float:
    n = (x * 374761393 + y * 668265263 + s * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def _vn(x: float, y: float, s: int) -> float:
    x0, y0 = math.floor(x), math.floor(y)
    fx, fy = x - x0, y - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = hash2(x0, y0, s), hash2(x0 + 1, y0, s)
    c, d = hash2(x0, y0 + 1, s), hash2(x0 + 1, y0 + 1, s)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def mottle(tu: int, tv: int, seed: int) -> float:
    return 0.55 * _vn(tu / 2.6, tv / 2.6, seed) + 0.3 * _vn(tu / 1.3, tv / 1.3, seed + 9) + 0.15 * hash2(tu, tv, seed + 17)


class Glow:
    """An emissive texel colour: drawn as-is, no lighting."""

    __slots__ = ("rgb",)

    def __init__(self, rgb: RGB) -> None:
        self.rgb = rgb


TexResult = Union[None, float, RGB, Glow]
Tex = Callable[[str, int, int, int, int], TexResult]
Alpha = Union[float, Callable[[str, int, int, int, int], float]]

FACES = {(2, 1): "front", (2, -1): "back", (0, 1): "right", (0, -1): "left", (1, 1): "top", (1, -1): "bottom"}
SIDES = ("front", "back", "right", "left")


class Part:
    __slots__ = ("name", "half", "M", "t", "Mi", "tex", "pal", "pid", "alpha")

    def __init__(self, name: str, half: Vec, M: Mat, t: Vec, tex: Optional[Tex], pal: list[RGB], pid: int,
                 alpha: Alpha = 1.0) -> None:
        self.name, self.half, self.M, self.t, self.tex, self.pal, self.pid = name, half, M, t, tex, pal, pid
        self.alpha = alpha
        self.Mi = inv3(M)


class Rig:
    """A frame in the transform hierarchy."""

    def __init__(self, M: Mat = I3, t: Vec = (0.0, 0.0, 0.0)) -> None:
        self.M, self.t = M, t

    def child(self, pivot: Vec, R: Mat = I3) -> "Rig":
        return Rig(mm(self.M, R), add(mv(self.M, pivot), self.t))

    def box(self, name: str, center: Vec, half: Vec, tex: Optional[Tex], pal: list[RGB], pid: int,
            alpha: Alpha = 1.0) -> Part:
        return Part(name, half, self.M, add(mv(self.M, center), self.t), tex, pal, pid, alpha)

    def point(self, p: Vec) -> Vec:
        return add(mv(self.M, p), self.t)


def _hit(part: Part, o: Vec, d: Vec):
    t = part.t
    lo = mv(part.Mi, (o[0] - t[0], o[1] - t[1], o[2] - t[2]))
    ld = mv(part.Mi, d)
    tn, tf, ax, sg = -1e9, 1e9, -1, 0
    for i in range(3):
        h, oi, di = part.half[i], lo[i], ld[i]
        if abs(di) < 1e-12:
            if oi < -h or oi > h:
                return None
            continue
        t1, t2 = (-h - oi) / di, (h - oi) / di
        s = -1
        if t1 > t2:
            t1, t2, s = t2, t1, 1
        if t1 > tn:
            tn, ax, sg = t1, i, s
        if t2 < tf:
            tf = t2
        if tn > tf:
            return None
    return tn, ax, sg, (lo[0] + tn * ld[0], lo[1] + tn * ld[1], lo[2] + tn * ld[2])


def _uv(ax: int, sg: int, q: Vec, half: Vec) -> tuple[int, int, int, int]:
    hx, hy, hz = half
    if ax == 2:
        u, v, W, H = ((q[0] + hx) if sg > 0 else (hx - q[0])), hy - q[1], 2 * hx, 2 * hy
    elif ax == 0:
        u, v, W, H = ((hz - q[2]) if sg > 0 else (q[2] + hz)), hy - q[1], 2 * hz, 2 * hy
    else:
        u, v, W, H = q[0] + hx, ((q[2] + hz) if sg > 0 else (hz - q[2])), 2 * hx, 2 * hz
    TW, TH = max(1, round(W * TPU)), max(1, round(H * TPU))
    return min(TW - 1, max(0, int(u * TPU))), min(TH - 1, max(0, int(v * TPU))), TW, TH


def _shade(part: Part, ax: int, sg: int, q: Vec) -> tuple[RGB, float]:
    face = FACES[(ax, sg)]
    row = part.Mi[ax]                       # world normal = inverse-transpose * local axis
    nw = _norm((row[0] * sg, row[1] * sg, row[2] * sg))
    sh = 0.22 + 0.78 * max(0.0, nw[0] * LIGHT[0] + nw[1] * LIGHT[1] + nw[2] * LIGHT[2])
    tu, tv, TW, TH = _uv(ax, sg, q, part.half)
    a = part.alpha(face, tu, tv, TW, TH) if callable(part.alpha) else part.alpha
    res = part.tex(face, tu, tv, TW, TH) if part.tex else None
    if isinstance(res, Glow):
        return res.rgb, a
    if isinstance(res, tuple):
        k = 0.72 + 0.4 * sh
        return (min(255, int(res[0] * k)), min(255, int(res[1] * k)), min(255, int(res[2] * k))), a
    v = mottle(tu, tv, part.pid * 7 + ax * 2 + (sg > 0)) * 0.5 + sh * 0.72 - 0.12 + (res or 0.0)
    if face in SIDES:
        if tv == 0:
            v += 0.07
        elif tv == TH - 1:
            v -= 0.06
    elif face == "top":
        v += 0.06
    pal = part.pal
    return pal[min(len(pal) - 1, max(0, int(v * len(pal))))], a


class FX:
    """Sprite effects in grid coordinates, alpha-blended (under or over the model)."""

    def __init__(self) -> None:
        self.px: dict[tuple[int, int], RGBA] = {}

    def put(self, x: float, y: float, c: tuple[int, ...]) -> None:
        xi, yi = int(round(x)), int(round(y))
        if not (0 <= xi < GRID_W and 0 <= yi < GRID_H):
            return
        rgba: RGBA = (c[0], c[1], c[2], max(0, min(255, c[3] if len(c) > 3 else 255)))
        if rgba[3] <= 0:
            return
        old = self.px.get((xi, yi))
        self.px[(xi, yi)] = rgba if old is None else _blend(old, rgba)


def _blend(dst: RGBA, src: RGBA) -> RGBA:
    a = src[3] / 255.0
    if dst[3] == 0:
        return src
    da = dst[3] / 255.0
    oa = a + da * (1 - a)
    if oa <= 0:
        return (0, 0, 0, 0)
    return (int((src[0] * a + dst[0] * da * (1 - a)) / oa), int((src[1] * a + dst[1] * da * (1 - a)) / oa),
            int((src[2] * a + dst[2] * da * (1 - a)) / oa), int(oa * 255))


def render(parts: list[Part], under: Optional[FX] = None, over: Optional[FX] = None, flash: float = 0.0,
           flash_rgb: RGB = (255, 255, 255), outline: RGB = (14, 30, 14), outline_soft: Optional[RGB] = None,
           dissolve: float = 0.0) -> Image.Image:
    N = GRID_W * GRID_H
    col: list[Optional[RGB]] = [None] * N
    dep = [1e9] * N
    pid = [-1] * N
    tcol: list[Optional[RGB]] = [None] * N
    tdep = [1e9] * N
    ta = [0.0] * N
    for p in parts:
        hx, hy, hz = p.half
        xs: list[float] = []
        ys: list[float] = []
        for a in (-hx, hx):
            for b in (-hy, hy):
                for c in (-hz, hz):
                    gx, gy = project(add(mv(p.M, (a, b, c)), p.t))
                    xs.append(gx)
                    ys.append(gy)
        x0, x1 = max(0, int(min(xs)) - 1), min(GRID_W - 1, int(max(xs)) + 1)
        y0, y1 = max(0, int(min(ys)) - 1), min(GRID_H - 1, int(max(ys)) + 1)
        opaque = not callable(p.alpha) and p.alpha >= 1.0
        for gy in range(y0, y1 + 1):
            sy = (GROUND - (gy + 0.5)) / S
            oy, oz = sy * _CP + 100 * _SP, -sy * _SP + 100 * _CP
            for gx in range(x0, x1 + 1):
                h = _hit(p, ((gx + 0.5 - CX) / S, oy, oz), D_AX)
                if h is None:
                    continue
                i = gy * GRID_W + gx
                if opaque:
                    if h[0] < dep[i]:
                        dep[i], pid[i] = h[0], p.pid
                        col[i] = _shade(p, h[1], h[2], h[3])[0]
                elif h[0] < tdep[i]:
                    c3, al = _shade(p, h[1], h[2], h[3])
                    tdep[i], tcol[i], ta[i] = h[0], c3, al

    def nbrs(i: int) -> list[int]:
        x, y = i % GRID_W, i // GRID_W
        return [j for j, ok in ((i - 1, x > 0), (i + 1, x < GRID_W - 1), (i - GRID_W, y > 0), (i + GRID_W, y < GRID_H - 1))
                if ok]

    out: list[Optional[RGBA]] = [None] * N
    for i in range(N):
        c = col[i]
        tc = tcol[i] if tdep[i] < dep[i] else None
        if c is not None:
            for j in nbrs(i):
                if col[j] is not None and pid[j] != pid[i] and dep[j] < dep[i] - 0.6:
                    c = (int(c[0] * 0.55), int(c[1] * 0.55), int(c[2] * 0.55))
                    break
            if tc is not None:
                al = ta[i]
                c = (int(tc[0] * al + c[0] * (1 - al)), int(tc[1] * al + c[1] * (1 - al)), int(tc[2] * al + c[2] * (1 - al)))
            out[i] = (c[0], c[1], c[2], 255)
        elif tc is not None:
            out[i] = (tc[0], tc[1], tc[2], max(1, int(255 * ta[i])))
    if flash:
        fr, fg, fb = flash_rgb
        out = [None if o is None else (int(o[0] + (fr - o[0]) * flash), int(o[1] + (fg - o[1]) * flash),
                                       int(o[2] + (fb - o[2]) * flash), o[3]) for o in out]
    covered = [o is not None for o in out]
    for i in range(N):
        if covered[i]:
            continue
        hard = soft = False
        for j in nbrs(i):
            if covered[j]:
                if col[j] is not None:
                    hard = True
                else:
                    soft = True
        if hard or (soft and outline_soft is None):
            out[i] = (outline[0], outline[1], outline[2], 255)
        elif soft and outline_soft is not None:
            out[i] = (outline_soft[0], outline_soft[1], outline_soft[2], 210)
    if dissolve > 0:
        for i in range(N):
            if out[i] is not None and hash2(i % GRID_W, i // GRID_W, 977) < dissolve:
                out[i] = None
    data: list[RGBA] = []
    for i in range(N):
        xy = (i % GRID_W, i // GRID_W)
        px: RGBA = under.px.get(xy, (0, 0, 0, 0)) if under else (0, 0, 0, 0)
        o = out[i]
        if o is not None:
            px = o if o[3] == 255 else _blend(px, o)
        if over is not None and xy in over.px:
            px = _blend(px, over.px[xy])
        data.append(px)
    img = Image.new("RGBA", (GRID_W, GRID_H))
    img.putdata(data)
    return img.resize((FRAME_W, FRAME_H), Image.Resampling.NEAREST)


# ---- shared effect sprites (grid coordinates) --------------------------------------------
def footprint(hx: float, hz: float, yaw: float) -> tuple[float, float]:
    """World-axis half extents of a hx x hz footprint turned by yaw."""
    c, s = abs(math.cos(yaw)), abs(math.sin(yaw))
    return c * hx + s * hz, s * hx + c * hz


def shadow(fx: FX, center: Vec, ext: tuple[float, float], lift: float, rgb: RGB = (0, 0, 0),
           alpha: tuple[int, int] = (82, 48)) -> None:
    cx, cy = project((center[0], 0.0, center[2]))
    k = max(0.45, 1.0 - max(0.0, lift) / 14.0)
    rx = max(3.0, ext[0] * S * 1.05 * k)
    ry = max(1.5, ext[1] * S * _SP * 1.15 * k)
    ry = min(ry, GRID_H - 3 - cy)
    rx = min(rx, cx - 2, GRID_W - 3 - cx)
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            e = ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2
            if e <= 1:
                fx.put(x, y, (rgb[0], rgb[1], rgb[2], alpha[0] if e < 0.45 else alpha[1]))


def glow_disc(fx: FX, cx: float, cy: float, rx: float, ry: float, rgb: RGB, alpha: int) -> None:
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            d = math.sqrt(((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2)
            if d < 1:
                fx.put(x, y, (rgb[0], rgb[1], rgb[2], int(alpha * (1 - d) ** 1.4)))


def _sprite(fx: FX, x0: int, y0: int, rows: list[str], colors: dict[str, RGB], alpha: int = 255,
            outline: Optional[RGB] = None) -> None:
    pts = {(x, y): ch for y, r in enumerate(rows) for x, ch in enumerate(r) if ch != "."}
    alpha = max(0, min(255, alpha))
    if outline:
        for (x, y) in list(pts):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if (x + dx, y + dy) not in pts:
                    fx.put(x0 + x + dx, y0 + y + dy, (outline[0], outline[1], outline[2], alpha))
    for (x, y), ch in pts.items():
        c = colors[ch]
        fx.put(x0 + x, y0 + y, (c[0], c[1], c[2], alpha))


HEART = [".XX...XX.", "XHHX.XXXX", "XHXXXXXXX", "XXXXXXXXX", ".XXXXXXX.", "..XXXXX..", "...XXX...", "....X...."]


def heart(fx: FX, x: float, y: float, alpha: int = 255) -> None:
    _sprite(fx, int(x), int(y), HEART, {"X": (226, 52, 66), "H": (255, 176, 176)}, alpha, outline=(110, 18, 30))


def puff(fx: FX, cx: float, cy: float, r: float, alpha: int, dark: bool = False) -> None:
    lite, mid = ((150, 150, 156), (110, 110, 118)) if dark else ((236, 236, 232), (196, 196, 192))
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            if dx * dx + dy * dy <= r * r:
                c = lite if dx + dy < -r * 0.3 else mid
                fx.put(x, y, (c[0], c[1], c[2], alpha))


def bubble(fx: FX, x0: int, y0: int, dots: int) -> None:
    """Speech bubble 19x12 with a tail at the bottom-left (15 rows in total)."""
    w, h = 19, 12
    for y in range(h):
        for x in range(w):
            if (x in (0, w - 1)) and (y in (0, h - 1)):
                continue
            edge = x in (0, w - 1) or y in (0, h - 1) or ((x in (1, w - 2)) and (y in (1, h - 2)))
            fx.put(x0 + x, y0 + y, (30, 30, 34) if edge else (250, 250, 246))
    for k, (x, y) in enumerate(((4, h), (5, h), (3, h + 1), (4, h + 1), (2, h + 2))):
        fx.put(x0 + x, y0 + y, (30, 30, 34) if k != 1 else (250, 250, 246))
    for i in range(dots):
        for dx in (0, 1):
            for dy in (0, 1):
                fx.put(x0 + 4 + i * 4 + dx, y0 + 5 + dy, (70, 70, 80))


def sweat(fx: FX, x: float, y: float) -> None:
    _sprite(fx, int(x), int(y), [".A.", ".A.", "ABA", "BBB", ".B."], {"A": (190, 232, 255), "B": (96, 168, 240)}, 255,
            outline=(40, 80, 140))


def sparkle(fx: FX, x: float, y: float, alpha: int = 255, c: RGB = (200, 150, 255)) -> None:
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        cc = (255, 255, 255) if (dx, dy) == (0, 0) else c
        fx.put(x + dx, y + dy, (cc[0], cc[1], cc[2], alpha))


STAR = ["..Y..", ".YWY.", "YWWWY", ".YWY.", "..Y.."]


def star(fx: FX, x: float, y: float, alpha: int = 255) -> None:
    _sprite(fx, int(x) - 2, int(y) - 2, STAR, {"Y": (255, 210, 60), "W": (255, 250, 214)}, alpha, outline=(140, 96, 20))


def drop(fx: FX, x: float, y: float, alpha: int = 255, rgb: RGB = (120, 210, 96)) -> None:
    _sprite(fx, int(x) - 1, int(y) - 1, [".A.", "ABA", ".A."], {"A": rgb, "B": (226, 252, 210)}, alpha,
            outline=(40, 90, 36))


def feather(fx: FX, x: float, y: float, alpha: int = 255, flip: bool = False) -> None:
    rows = ["..WW", ".WWG", "WWG.", "G..."]
    if flip:
        rows = [r[::-1] for r in rows]
    _sprite(fx, int(x) - 2, int(y) - 2, rows, {"W": (250, 250, 246), "G": (188, 188, 182)}, alpha,
            outline=(110, 110, 104))


def portal(fx: FX, x: float, y: float, alpha: int = 255) -> None:
    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        c = (236, 170, 255) if (dx, dy) == (0, 0) else (150, 66, 214)
        fx.put(x + dx, y + dy, (c[0], c[1], c[2], alpha))


def spark(fx: FX, x: float, y: float, alpha: int = 255) -> None:
    fx.put(x, y, (255, 244, 200, alpha))
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        fx.put(x + dx, y + dy, (255, 168, 60, alpha // 2))


def speed(fx: FX, x: float, y: float, length: int, alpha: int = 200, trail_left: bool = True) -> None:
    for k in range(length):
        fx.put(x - k if trail_left else x + k, y, (236, 236, 236, int(alpha * (1 - k / length))))


def book(fx: FX, x0: int, y0: int, f: int) -> None:
    cover, cover_d, page, page_d, line = (122, 70, 38), (84, 46, 24), (242, 236, 218), (214, 206, 186), (150, 140, 128)
    for y in range(11):
        for x in range(22):
            if y >= 9:
                c = cover_d if y == 10 else cover
            elif x in (0, 21):
                c = cover
            elif x in (10, 11):
                c = page_d
            else:
                c = page if (y > 0 or x % 10 not in (1, 0)) else page_d
            fx.put(x0 + x, y0 + y, c)
    for y in (2, 4, 6):
        for x in list(range(2, 9)) + list(range(13, 20)):
            if (x * 3 + y + (f if x > 11 else 0)) % 7:
                fx.put(x0 + x, y0 + y, line)
    if f in (2, 3):
        lift = 4 if f == 2 else 2
        for x in range(12, 20 - (2 if f == 2 else 0)):
            fx.put(x0 + x - (x - 12) // 2 * (1 if f == 2 else 0), y0 - lift + (x - 12) // 3, page)
    for k in range(3):
        a = (f + k * 2) % 6
        sparkle(fx, x0 + 4 + k * 7, y0 - 3 - a * 2, max(0, 230 - a * 40))
