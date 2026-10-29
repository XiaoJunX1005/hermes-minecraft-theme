"""Generate the animated Creeper Buddy pet (Codex/petdex 8x9 spritesheet).

A chibi, high-density redraw (48x52 logical pixels, 4px each) with smooth
value-noise shading — deliberately NOT the game's 8x8 face / 16x16 texture.

Output: pets/creeper-buddy/spritesheet.png (1536x1872) + pet.json,
        docs/pet-preview.gif (every state side by side).

Run:  python tools/make_creeper.py
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from pixels import fbm

ROOT = Path(__file__).resolve().parent.parent
SLUG = "creeper-buddy"
PET_DIR = ROOT / "pets" / SLUG
DOCS = ROOT / "docs"

FRAME_W, FRAME_H = 192, 208
COLS, ROWS = 8, 9
PX = 4
GRID_W, GRID_H = 48, 52
FRAMES = 6
STATES = ["idle", "running-right", "running-left", "waving", "jumping",
          "failed", "waiting", "running", "review"]

OUTLINE = (16, 30, 14, 255)
FACE = (24, 40, 22, 255)
SHINE = (236, 255, 226, 255)
BLUSH = (236, 150, 140, 255)
GREENS = [(52, 112, 44), (66, 134, 52), (82, 156, 62), (98, 176, 72), (120, 196, 88), (150, 214, 112)]

_NOISE = fbm(GRID_W, GRID_H, 77)


def skin(x: int, y: int, light: float) -> tuple:
    # mostly form shading from one top-left light, with a gentle creeper mottle on top
    t = min(0.999, max(0.0, 0.32 + (_NOISE[y % GRID_H][x % GRID_W] - 0.5) * 0.32 + light * 1.4))
    r, g, b = GREENS[int(t * len(GREENS))]
    return (r, g, b, 255)


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

    def render(self, flash: float = 0.0, flip: bool = False) -> Image.Image:
        img = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for layer in (self.px, self.fx):
            for (x, y), c in layer.items():
                if flash and layer is self.px and c != OUTLINE:
                    c = tuple(int(c[i] * (1 - flash) + 255 * flash) for i in range(3)) + (c[3],)
                gx = GRID_W - 1 - x if flip else x
                d.rectangle([gx * PX, y * PX, gx * PX + PX - 1, y * PX + PX - 1], fill=c)
        return img


def block(cv: Canvas, x0: int, y0: int, w: int, h: int, round_: int = 1, shade: float = 0.0) -> None:
    """Rounded-corner block with top-left light and bottom-right shade."""
    for y in range(h):
        for x in range(w):
            cx = min(x, w - 1 - x)
            cy = min(y, h - 1 - y)
            if cx + cy < round_:
                continue
            light = 0.18 * (1 - x / w) + 0.14 * (1 - y / h) - 0.22 * (y / h) ** 2 - shade
            if x == 0 or y == 0:
                light += 0.12
            if x == w - 1 or y == h - 1:
                light -= 0.14
            cv.put(x0 + x, y0 + y, skin(x0 + x, y0 + y, light))


def face(cv: Canvas, ox: int, oy: int, eyes: str) -> None:
    """Face in head-local coords (head is 28x24 at ox, oy)."""
    for ex in (ox + 5, ox + 18):
        if eyes == "open":
            for y in range(5):
                for x in range(5):
                    if (x in (0, 4)) and (y in (0, 4)):
                        continue
                    cv.put(ex + x, oy + 7 + y, FACE)
            cv.put(ex + 1, oy + 8, SHINE)
            cv.put(ex + 2, oy + 8, SHINE)
            cv.put(ex + 1, oy + 9, SHINE)
        elif eyes == "blink":
            for x in range(5):
                cv.put(ex + x, oy + 10, FACE)
        elif eyes == "happy":
            for x, y in ((0, 11), (1, 10), (2, 9), (3, 10), (4, 11)):
                cv.put(ex + x, oy + y, FACE)
        elif eyes == "x":
            for i in range(5):
                cv.put(ex + i, oy + 7 + i, FACE)
                cv.put(ex + 4 - i, oy + 7 + i, FACE)
        elif eyes == "down":
            for y in range(3):
                for x in range(5):
                    if not ((x in (0, 4)) and y == 2):
                        cv.put(ex + x, oy + 9 + y, FACE)
    # small, rounded mouth (chibi version of the classic shape)
    mouth = ["..XX..", ".XXXX.", "XXXXXX", "XX..XX"] if eyes != "x" else ["XXXXXX"]
    for y, row in enumerate(mouth):
        for x, c in enumerate(row):
            if c == "X":
                cv.put(ox + 11 + x, oy + 14 + y, FACE)
    if eyes not in ("x",):
        for bx in (ox + 3, ox + 23):
            cv.put(bx, oy + 14, BLUSH)
            cv.put(bx + 1, oy + 14, BLUSH)


def creeper(cv: Canvas, dy: int = 0, dx: int = 0, face_dx: int = 0, eyes: str = "open",
            leg_l: int = 0, leg_r: int = 0, legs_follow: bool = False) -> None:
    ly = dy if legs_follow else 0
    for fx0, lo in ((12, leg_l), (29, leg_r)):
        block(cv, fx0 + dx, 39 + ly + lo, 7, 6, round_=1, shade=0.12)
    block(cv, 15 + dx, 27 + dy, 18, 14, round_=1, shade=0.05)
    block(cv, 10 + dx, 4 + dy, 28, 24, round_=3)
    face(cv, 10 + dx + face_dx, 4 + dy, eyes)


def shadow(cv: Canvas, lift: int) -> None:
    half = max(6, 14 - lift)
    for x in range(24 - half, 24 + half):
        cv.put(x, 47, (0, 0, 0, 70), fx=True)
    for x in range(24 - half + 3, 24 + half - 3):
        cv.put(x, 48, (0, 0, 0, 40), fx=True)


HEART = [".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]


def heart(cv: Canvas, ox: int, oy: int, alpha: int = 255) -> None:
    for y, row in enumerate(HEART):
        for x, ch in enumerate(row):
            if ch == "X":
                c = (255, 160, 150, alpha) if (x, y) in ((1, 1), (2, 1)) else (226, 52, 60, alpha)
                cv.put(ox + x, oy + y, c, fx=True)


def puff(cv: Canvas, ox: int, oy: int, size: int, alpha: int) -> None:
    for y in range(size):
        for x in range(size):
            if (x - size / 2 + 0.5) ** 2 + (y - size / 2 + 0.5) ** 2 > (size / 2) ** 2:
                continue
            g = 205 if (x + y) % 3 else 170
            cv.put(ox + x, oy + y, (g, g, g, alpha), fx=True)


def bubble(cv: Canvas, dots: int) -> None:
    x0, y0, w, h = 34, 0, 14, 8
    for y in range(h):
        for x in range(w):
            if x in (0, w - 1) and y in (0, h - 1):
                continue
            edge = x in (0, w - 1) or y in (0, h - 1)
            cv.put(x0 + x, y0 + y, (24, 24, 24, 255) if edge else (250, 250, 250, 255), fx=True)
    for i, (x, y) in enumerate(((3, h), (2, h + 1))):
        cv.put(x0 + x, y0 + y, (24, 24, 24, 255), fx=True)
    for i in range(dots):
        for xx in (0, 1):
            for yy in (0, 1):
                cv.put(x0 + 3 + i * 3 + xx, y0 + 4 + yy, (60, 60, 60, 255), fx=True)


def book(cv: Canvas, ox: int, oy: int, f: int) -> None:
    cover, page, line = (110, 62, 34, 255), (238, 232, 214, 255), (150, 140, 130, 255)
    for y in range(9):
        for x in range(11):
            edge = x in (0, 10) or y in (0, 8)
            cv.put(ox + x, oy + y, cover if edge or x == 5 else page, fx=True)
    for y in (2, 4, 6):
        for x in (2, 3, 4, 6, 7, 8):
            if (x + y + f) % 5:
                cv.put(ox + x, oy + y, line, fx=True)
    sx, sy = [(2, 1), (4, 2), (7, 3), (8, 5), (6, 6), (3, 5)][f]
    cv.put(ox + sx, oy + sy, (205, 140, 255, 255), fx=True)
    for k in range(2):
        cv.put(ox + 5 + k * 3 - f % 2, oy - 3 - (f + k) % 3, (205, 140, 255, 200 - 50 * ((f + k) % 3)), fx=True)


LEG_CYCLE = [(-1, 0), (-2, 0), (0, 0), (0, -1), (0, -2), (0, 0)]
BOB = [-1, -1, 0, -1, -1, 0]


def frame(state: str, f: int) -> Image.Image:
    cv = Canvas()
    flash, flip, after = 0.0, False, []

    if state == "idle":
        creeper(cv, dy=[0, 0, -1, -1, -1, 0][f], eyes="blink" if f == 4 else "open")
        shadow(cv, 0)
    elif state in ("running-right", "running-left"):
        ll, lr = LEG_CYCLE[f]
        creeper(cv, dy=BOB[f], face_dx=2, leg_l=ll, leg_r=lr)
        shadow(cv, 0)
        if f in (2, 3, 5, 0):
            age = {2: 0, 3: 1, 5: 0, 0: 1}[f]
            after.append(lambda: puff(cv, 5 - age * 2, 41 - age * 2, 4 + age * 2, 210 - age * 90))
        flip = state == "running-left"
    elif state == "running":
        ll, lr = LEG_CYCLE[f]
        creeper(cv, dy=BOB[f], leg_l=ll, leg_r=lr)
        shadow(cv, 0)
        def sweat():
            y0 = 6 + f % 3
            for (x, y), c in (((41, y0), (190, 230, 255, 255)), ((40, y0 + 1), (120, 190, 250, 255)),
                              ((41, y0 + 1), (150, 210, 255, 255)), ((42, y0 + 1), (90, 160, 240, 255)),
                              ((40, y0 + 2), (80, 150, 235, 255)), ((41, y0 + 2), (70, 135, 220, 255)),
                              ((42, y0 + 2), (60, 120, 210, 255)), ((41, y0 + 3), (50, 105, 190, 255))):
                cv.put(x, y, c, fx=True)
        after.append(sweat)
    elif state == "waving":
        dy = [0, -1, -2, -2, -1, 0][f]
        creeper(cv, dy=dy, eyes="happy", legs_follow=True)
        shadow(cv, -dy * 2)
        after.append(lambda: heart(cv, 39, 18 - f * 3, 255 - f * 30))
        if f >= 2:
            after.append(lambda: heart(cv, 2, 22 - (f - 2) * 3, 255 - (f - 2) * 45))
    elif state == "jumping":
        dy = [2, -1, -3, -3, -1, 0][f]
        tuck = -2 if f in (2, 3) else 0
        creeper(cv, dy=dy, eyes="happy" if f in (2, 3) else "open", legs_follow=f != 0, leg_l=tuck, leg_r=tuck)
        shadow(cv, -dy * 3)
    elif state == "failed":
        creeper(cv, dx=[-1, 1, -1, 1, -1, 1][f], eyes="x")
        shadow(cv, 0)
        flash = [0.0, 0.25, 0.45, 0.25, 0.5, 0.2][f]
        if f >= 2:
            after.append(lambda: [puff(cv, 2, 18 - (f - 2) * 4, 6, 220 - (f - 2) * 45),
                                  puff(cv, 39, 12 - (f - 2) * 4, 6, 220 - (f - 2) * 45)])
    elif state == "waiting":
        creeper(cv, dy=[0, 0, 0, -1, -1, -1][f], eyes="blink")
        shadow(cv, 0)
        after.append(lambda: bubble(cv, 1 + f // 2))
    elif state == "review":
        creeper(cv, face_dx=[-1, -1, 0, 1, 1, 0][f], dy=[0, 0, -1, -1, 0, 0][f], eyes="down")
        shadow(cv, 0)
        after.append(lambda: book(cv, 36, 30 + [0, -1, -1, 0, 1, 1][f], f))

    cv.outline()
    for fn in after:
        fn()
    return cv.render(flash=flash, flip=flip)


def head_pixels() -> dict[tuple[int, int], tuple]:
    """Logical pixels of the idle pose (used for the CLI banner hero)."""
    cv = Canvas()
    creeper(cv)
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
        "displayName": "Creeper Buddy",
        "description": "A chibi pixel creeper that hops, reads and (almost) explodes alongside Hermes.",
        "spritesheetPath": "spritesheet.png",
    }, indent=2) + "\n", encoding="utf-8")

    show = ["idle", "running-right", "running", "waving", "jumping", "failed", "waiting", "review"]
    cw, ch = FRAME_W // 2, FRAME_H // 2
    gif = []
    for f in range(FRAMES):
        canvas = Image.new("RGBA", (cw * len(show), ch + 22), (24, 26, 32, 255))
        d = ImageDraw.Draw(canvas)
        for i, s in enumerate(show):
            canvas.alpha_composite(frames[s][f].resize((cw, ch), Image.NEAREST), (i * cw, 0))
            d.text((i * cw + 6, ch + 5), s, fill=(200, 200, 200, 255))
        gif.append(canvas.convert("RGB"))
    strip = Image.new("RGB", (gif[0].width, gif[0].height * 3))
    for k, i in enumerate((0, 2, 4)):
        strip.paste(gif[i], (0, gif[0].height * k))
    pal = strip.quantize(colors=160, method=Image.Quantize.MEDIANCUT)
    gif = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in gif]
    gif[0].save(DOCS / "pet-preview.gif", save_all=True, append_images=gif[1:], duration=1100 // FRAMES, loop=0)
    print("wrote", PET_DIR / "spritesheet.png", sheet.size)


if __name__ == "__main__":
    main()
