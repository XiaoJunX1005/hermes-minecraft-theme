"""Generate the animated Lantern Buddy pet (Codex/petdex 8x9 spritesheet).

An original character: a little copper lantern with a glowing face.

Output: pets/lantern-buddy/spritesheet.png (1536x1872) + pet.json,
        docs/pet-preview.gif (every state side by side).

Run:  python tools/make_pet.py
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SLUG = "lantern-buddy"
PET_DIR = ROOT / "pets" / SLUG
DOCS = ROOT / "docs"

FRAME_W, FRAME_H = 192, 208
COLS, ROWS = 8, 9
PX = 6
GRID_W, GRID_H = 32, 34
TOP_PAD = FRAME_H - GRID_H * PX
FRAMES = 6

# Codex row order (agent/pet/constants.py CODEX_STATE_ROWS).
STATES = ["idle", "running-right", "running-left", "waving", "jumping",
          "failed", "waiting", "running", "review"]

OUTLINE = (20, 16, 18, 255)
PATINA = (79, 195, 168, 255)
CAP = (74, 52, 40, 255)
FACE = (58, 37, 22, 255)
BLUSH = (232, 132, 110, 255)


def rgba(h: str, a: int = 255) -> tuple:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def glass(t: float, glow: float) -> tuple:
    """Glass colour: t = 0 centre .. 1 edge, glow = brightness 0..1."""
    hot, warm, edge = (255, 232, 168), (242, 179, 107), (205, 128, 64)
    a, b, k = (hot, warm, t / 0.6) if t < 0.6 else (warm, edge, (t - 0.6) / 0.4)
    c = [a[i] * (1 - k) + b[i] * k for i in range(3)]
    dim = 0.45 + 0.55 * glow
    return (int(c[0] * dim), int(c[1] * dim), int(c[2] * dim), 255)


class Canvas:
    def __init__(self) -> None:
        self.px: dict[tuple[int, int], tuple] = {}
        self.fx: dict[tuple[int, int], tuple] = {}

    def put(self, x: int, y: int, c: tuple, fx: bool = False) -> None:
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            (self.fx if fx else self.px)[(x, y)] = c

    def outline(self) -> None:
        filled = set(self.px)
        for (x, y) in list(filled):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if n not in filled and 0 <= n[0] < GRID_W and 0 <= n[1] < GRID_H:
                    self.px.setdefault(n, OUTLINE)

    def render(self, flip: bool = False) -> Image.Image:
        img = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for layer in (self.px, self.fx):
            for (x, y), c in layer.items():
                gx = GRID_W - 1 - x if flip else x
                d.rectangle([gx * PX, TOP_PAD + y * PX, gx * PX + PX - 1, TOP_PAD + y * PX + PX - 1], fill=c)
        return img


_PATINA_SPOTS = {(9, 8), (10, 8), (22, 21), (21, 22)}
_COPPER_BANDS = [(232, 168, 110, 255), (196, 124, 70, 255), (172, 104, 58, 255), (140, 82, 46, 255)]


def copper(x: int, roof: bool = False) -> tuple:
    """Smooth copper: bright highlight on the left edge, darker toward the right."""
    if x <= 10:
        return _COPPER_BANDS[0] if x == 10 or roof else _COPPER_BANDS[1]
    if x >= 21:
        return _COPPER_BANDS[3]
    return _COPPER_BANDS[1] if x < 16 else _COPPER_BANDS[2]


def lantern(cv: Canvas, dx: int = 0, dy: int = 0, eyes: str = "open", glow: float = 1.0,
            leg_l: int = 0, leg_r: int = 0, look: int = 0, legs_follow: bool = False) -> None:
    ly = dy if legs_follow else 0
    # legs
    for lx, lo in ((12, leg_l), (18, leg_r)):
        for x in (lx, lx + 1):
            for y in (26, 27):
                cv.put(x + dx, y + ly + lo, CAP)
    # ring handle (hollow loop)
    for x in range(14, 18):
        cv.put(x + dx, 0 + dy, CAP)
    for y in (1, 2):
        cv.put(13 + dx, y + dy, CAP)
        cv.put(18 + dx, y + dy, CAP)
    # peaked roof
    for y, (a, b) in ((3, (13, 18)), (4, (11, 20)), (5, (10, 21))):
        for x in range(a, b + 1):
            cv.put(x + dx, y + dy, copper(x, roof=True))
    for x in range(9, 23):
        cv.put(x + dx, 6 + dy, copper(x))
        cv.put(x + dx, 24 + dy, copper(x))
    for x in range(10, 22):
        cv.put(x + dx, 25 + dy, CAP)
    # frame + glass (two slim mullions make it read as a lantern cage)
    for y in range(7, 24):
        for x in range(9, 23):
            frame = x in (9, 10, 21, 22) or y in (7, 23)
            if frame:
                c = PATINA if (x, y) in _PATINA_SPOTS else copper(x)
            elif x in (12, 19) and y not in range(12, 20):
                c = copper(x)
            else:
                t = max(abs(x - 15.5) / 5.5, abs(y - 15) / 7.5)
                c = glass(min(1.0, t), glow)
            cv.put(x + dx, y + dy, c)
    # face
    ex = 13 + look + dx
    ey = 14 + dy
    if eyes == "open":
        for x0 in (ex, ex + 5):
            for xx in (0, 1):
                for yy in (0, 1):
                    cv.put(x0 + xx, ey + yy, FACE)
    elif eyes == "blink":
        for x0 in (ex, ex + 5):
            cv.put(x0, ey + 1, FACE)
            cv.put(x0 + 1, ey + 1, FACE)
    elif eyes == "happy":  # ^ ^
        for x0 in (ex, ex + 5):
            cv.put(x0, ey + 1, FACE)
            cv.put(x0 + 1, ey, FACE)
            cv.put(x0 + 2, ey + 1, FACE)
    elif eyes == "x":
        for x0 in (ex, ex + 5):
            for p in ((0, 0), (2, 0), (1, 1), (0, 2), (2, 2)):
                cv.put(x0 + p[0], ey + p[1] - 1, FACE)
    elif eyes == "down":
        for x0 in (ex, ex + 5):
            cv.put(x0, ey + 2, FACE)
            cv.put(x0 + 1, ey + 2, FACE)
            cv.put(x0, ey + 1, FACE)
            cv.put(x0 + 1, ey + 1, FACE)
    if eyes == "x":
        for x in (15, 16):
            cv.put(x + look + dx, 19 + dy, FACE)
    else:
        cv.put(15 + look + dx, 18 + dy, FACE)
        cv.put(16 + look + dx, 19 + dy, FACE)
        cv.put(17 + look + dx, 18 + dy, FACE)
        cv.put(13 + look + dx, 17 + dy, BLUSH)
        cv.put(19 + look + dx, 17 + dy, BLUSH)


def shadow(cv: Canvas, lift: int) -> None:
    half = max(3, 7 - lift)
    for x in range(16 - half, 16 + half):
        cv.put(x, 30, (0, 0, 0, 70), fx=True)
    for x in range(16 - half + 2, 16 + half - 2):
        cv.put(x, 31, (0, 0, 0, 40), fx=True)


def sparkle(cv: Canvas, x: int, y: int, c: tuple, big: bool = True) -> None:
    cv.put(x, y, c, fx=True)
    if big:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cv.put(x + dx, y + dy, c[:3] + (int(c[3] * 0.55),), fx=True)


def puff(cv: Canvas, ox: int, oy: int, size: int, alpha: int) -> None:
    for y in range(size):
        for x in range(size):
            if size > 2 and (x, y) in ((0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)):
                continue
            g = 150 if (x + y) % 2 else 120
            cv.put(ox + x, oy + y, (g, g, g + 6, alpha), fx=True)


def bubble(cv: Canvas, dots: int) -> None:
    x0, y0, w, h = 22, 0, 10, 6
    for y in range(h):
        for x in range(w):
            if x in (0, w - 1) and y in (0, h - 1):
                continue
            edge = x in (0, w - 1) or y in (0, h - 1)
            cv.put(x0 + x, y0 + y, (30, 32, 38, 255) if edge else (236, 230, 218, 255), fx=True)
    cv.put(x0 + 2, y0 + h, (30, 32, 38, 255), fx=True)
    for i in range(dots):
        cv.put(x0 + 2 + i * 2, y0 + 3, (79, 140, 125, 255), fx=True)


def scroll(cv: Canvas, ox: int, oy: int, f: int) -> None:
    paper, roll, ink = (236, 226, 200, 255), (176, 140, 96, 255), (120, 104, 92, 255)
    for x in range(7):
        cv.put(ox + x, oy, roll, fx=True)
        cv.put(ox + x, oy + 6, roll, fx=True)
    for y in range(1, 6):
        for x in range(1, 6):
            cv.put(ox + x, oy + y, paper, fx=True)
    for y in (2, 3, 4):
        for x in range(2, 5 if y == 4 else 6):
            if (x + f) % 4:
                cv.put(ox + x, oy + y, ink, fx=True)


LEG_CYCLE = [(-1, 0), (-2, 0), (0, 0), (0, -1), (0, -2), (0, 0)]
BOB = [-1, -1, 0, -1, -1, 0]
AMBER = (255, 214, 140, 255)
TEAL = (110, 220, 196, 255)


def frame(state: str, f: int) -> Image.Image:
    cv = Canvas()
    flip = False
    fx_after: list = []

    if state == "idle":
        dy = [0, 0, -1, -1, -1, 0][f]
        lantern(cv, dy=dy, eyes="blink" if f == 4 else "open", glow=0.85 + 0.15 * (f in (1, 2, 3)))
        shadow(cv, 0)
        fx_after.append(lambda: sparkle(cv, 24, 6 - f, AMBER[:3] + (230 - f * 35,), big=False))

    elif state in ("running-right", "running-left"):
        ll, lr = LEG_CYCLE[f]
        lantern(cv, dy=BOB[f], leg_l=ll, leg_r=lr, look=1)
        shadow(cv, 0)
        if f in (2, 3, 5, 0):
            age = {2: 0, 3: 1, 5: 0, 0: 1}[f]
            fx_after.append(lambda: puff(cv, 6 - age, 26 - age, 2 + age, 200 - age * 80))
        flip = state == "running-left"

    elif state == "running":   # busy: working hard, sparks fly from the handle
        ll, lr = LEG_CYCLE[f]
        lantern(cv, dy=BOB[f], leg_l=ll, leg_r=lr, glow=1.0)
        shadow(cv, 0)
        fx_after.append(lambda: [sparkle(cv, 12 - f, 3 - (f % 3), AMBER, big=False),
                                 sparkle(cv, 20 + f, 2 - (f % 2), AMBER, big=False),
                                 sparkle(cv, 16 + (f % 3), 0, TEAL, big=False)])

    elif state == "waving":
        dy = [0, -1, -2, -2, -1, 0][f]
        lantern(cv, dy=dy, eyes="happy", legs_follow=True)
        shadow(cv, -dy)
        fx_after.append(lambda: [sparkle(cv, 26, 14 - f * 2, AMBER[:3] + (255 - f * 30,)),
                                 sparkle(cv, 5, 18 - f * 2, TEAL[:3] + (255 - f * 30,)) if f >= 1 else None])

    elif state == "jumping":
        dy = [1, -1, -2, -2, -1, 0][f]
        tuck = -1 if f in (2, 3) else 0
        lantern(cv, dy=dy, eyes="happy" if f in (2, 3) else "open", legs_follow=f != 0, leg_l=tuck, leg_r=tuck)
        shadow(cv, -dy * 2)

    elif state == "failed":
        dx = [-1, 1, -1, 1, -1, 1][f]
        lantern(cv, dx=dx, eyes="x", glow=[0.2, 0.6, 0.1, 0.5, 0.15, 0.4][f])
        shadow(cv, 0)
        if f >= 1:
            fx_after.append(lambda: [puff(cv, 14, 0 - (f - 1) % 2, 3, 200 - (f - 1) * 30),
                                     puff(cv, 18 + f % 2, 1, 2, 160 - (f - 1) * 25)])

    elif state == "waiting":
        lantern(cv, dy=[0, 0, 0, -1, -1, -1][f], eyes="blink", glow=0.55)
        shadow(cv, 0)
        fx_after.append(lambda: bubble(cv, 1 + f // 2))

    elif state == "review":
        lantern(cv, eyes="down", look=[0, 0, 1, 1, 1, 0][f], dy=[0, 0, -1, -1, 0, 0][f])
        shadow(cv, 0)
        fx_after.append(lambda: scroll(cv, 23, 18 + [0, -1, -1, 0, 1, 1][f], f))

    cv.outline()
    for fn in fx_after:
        fn()
    return cv.render(flip=flip)


def idle_grid() -> dict[tuple[int, int], tuple]:
    """Logical pixels of the idle pose (for the CLI banner)."""
    cv = Canvas()
    lantern(cv)
    cv.outline()
    return cv.px


def main() -> None:
    PET_DIR.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (FRAME_W * COLS, FRAME_H * ROWS), (0, 0, 0, 0))
    frames = {s: [frame(s, f) for f in range(FRAMES)] for s in STATES}
    for r, s in enumerate(STATES):
        for c in range(COLS):
            sheet.paste(frames[s][c % FRAMES], (c * FRAME_W, r * FRAME_H))
    sheet.save(PET_DIR / "spritesheet.png", optimize=True)

    (PET_DIR / "pet.json").write_text(json.dumps({
        "id": SLUG,
        "displayName": "Lantern Buddy",
        "description": "A tiny copper lantern that hops, sparks and glows alongside Hermes.",
        "spritesheetPath": "spritesheet.png",
    }, indent=2) + "\n", encoding="utf-8")

    show = ["idle", "running-right", "running", "waving", "jumping", "failed", "waiting", "review"]
    cell_w, cell_h = FRAME_W // 2, FRAME_H // 2
    gif = []
    for f in range(FRAMES):
        canvas = Image.new("RGBA", (cell_w * len(show), cell_h + 22), (21, 23, 28, 255))
        d = ImageDraw.Draw(canvas)
        for i, s in enumerate(show):
            canvas.alpha_composite(frames[s][f].resize((cell_w, cell_h), Image.NEAREST), (i * cell_w, 0))
            d.text((i * cell_w + 6, cell_h + 5), s, fill=(200, 196, 188, 255))
        gif.append(canvas.convert("RGB"))
    strip = Image.new("RGB", (gif[0].width, gif[0].height * 3))
    for k, i in enumerate((0, 2, 4)):
        strip.paste(gif[i], (0, gif[0].height * k))
    pal = strip.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    gif = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in gif]
    gif[0].save(DOCS / "pet-preview.gif", save_all=True, append_images=gif[1:],
                duration=1100 // FRAMES, loop=0)
    print("wrote", PET_DIR / "spritesheet.png", sheet.size)


if __name__ == "__main__":
    main()
