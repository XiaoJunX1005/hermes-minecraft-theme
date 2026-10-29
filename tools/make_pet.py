"""Generate the animated Creeper Buddy pet (Codex/petdex 8x9 spritesheet).

Output: pets/creeper-buddy/spritesheet.png (1536x1872) + pet.json,
        docs/pet-preview.gif (every state side by side).

Run:  python tools/make_pet.py
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from pixels import CREEPER_GREENS, creeper_head, noise_texture

ROOT = Path(__file__).resolve().parent.parent
PET_DIR = ROOT / "pets" / "creeper-buddy"
DOCS = ROOT / "docs"

FRAME_W, FRAME_H = 192, 208
COLS, ROWS = 8, 9
PX = 6                      # one logical pixel = 6x6 real pixels
GRID_W, GRID_H = 32, 34     # 32*6 = 192, 34*6 = 204 (+4px top pad)
TOP_PAD = FRAME_H - GRID_H * PX
FRAMES = 6

# Codex row order (agent/pet/constants.py CODEX_STATE_ROWS).
STATES = ["idle", "running-right", "running-left", "waving", "jumping",
          "failed", "waiting", "running", "review"]

OUTLINE = (13, 31, 10, 255)


def hex_rgba(h: str, a: int = 255) -> tuple[int, int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def shade(c: tuple, k: float) -> tuple:
    return (int(c[0] * k), int(c[1] * k), int(c[2] * k), c[3])


def blend(c: tuple, other: tuple, t: float) -> tuple:
    return tuple(int(c[i] * (1 - t) + other[i] * t) for i in range(3)) + (c[3],)


HEAD_SEED, BODY_TEX, LEG_TEX = 7, noise_texture(10, 8, CREEPER_GREENS, 11, [2, 4, 6, 5, 3, 2]), \
    noise_texture(6, 5, CREEPER_GREENS, 21, [1, 3, 5, 5, 4, 3])

HEART = [".X.X.", "XXXXX", "XXXXX", ".XXX.", "..X.."]
BOOK = [
    "CCCCCCC",
    "CPPPPPC",
    "CPPPPPC",
    "CPPPPPC",
    "CPPPPPC",
    "CCCCCCC",
]


class Canvas:
    def __init__(self) -> None:
        self.px: dict[tuple[int, int], tuple] = {}
        self.fx: dict[tuple[int, int], tuple] = {}   # effects drawn after outline

    def put(self, x: int, y: int, c: tuple, fx: bool = False) -> None:
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            (self.fx if fx else self.px)[(x, y)] = c

    def blit(self, tex: list[list[str]], ox: int, oy: int, right_shade: int = 2, k: float = 1.0) -> None:
        h, w = len(tex), len(tex[0])
        for y in range(h):
            for x in range(w):
                c = hex_rgba(tex[y][x])
                if x >= w - right_shade:
                    c = shade(c, 0.78)
                if y == h - 1:
                    c = shade(c, 0.85)
                self.put(ox + x, oy + y, shade(c, k))

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
                    c = blend(c, (255, 255, 255, 255), flash)
                gx = GRID_W - 1 - x if flip else x
                d.rectangle([gx * PX, TOP_PAD + y * PX, gx * PX + PX - 1, TOP_PAD + y * PX + PX - 1], fill=c)
        return img


def shadow(cv: Canvas, lift: int) -> None:
    half = max(3, 7 - lift // 2)
    for x in range(16 - half, 16 + half):
        cv.put(x, 32, (0, 0, 0, 70), fx=True)
    for x in range(16 - half + 2, 16 + half - 2):
        cv.put(x, 33, (0, 0, 0, 40), fx=True)


def creeper(cv: Canvas, dy: int = 0, dx: int = 0, face_dx: int = 0,
            leg_l: int = 0, leg_r: int = 0, legs_follow: bool = False) -> None:
    ly = dy if legs_follow else 0
    cv.blit(LEG_TEX, 9 + dx, 26 + ly + leg_l, right_shade=1, k=0.92)
    cv.blit(LEG_TEX, 17 + dx, 26 + ly + leg_r, right_shade=1, k=0.92)
    cv.blit(BODY_TEX, 11 + dx, 18 + dy)
    cv.blit(creeper_head(16, face_dx, HEAD_SEED), 8 + dx, 2 + dy)


def heart(cv: Canvas, ox: int, oy: int, alpha: int = 255) -> None:
    for y, row in enumerate(HEART):
        for x, ch in enumerate(row):
            if ch == "X":
                c = (255, 138, 128, alpha) if (x, y) == (1, 1) else (226, 40, 40, alpha)
                cv.put(ox + x, oy + y, c, fx=True)


def puff(cv: Canvas, ox: int, oy: int, size: int, alpha: int) -> None:
    for y in range(size):
        for x in range(size):
            if (x, y) in ((0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)) and size > 2:
                continue
            g = 200 if (x + y) % 2 else 165
            cv.put(ox + x, oy + y, (g, g, g, alpha), fx=True)


def bubble(cv: Canvas, dots: int) -> None:
    x0, y0, w, h = 22, 0, 10, 6
    for y in range(h):
        for x in range(w):
            edge = x in (0, w - 1) or y in (0, h - 1)
            corner = (x in (0, w - 1)) and (y in (0, h - 1))
            if corner:
                continue
            cv.put(x0 + x, y0 + y, (20, 20, 20, 255) if edge else (250, 250, 250, 255), fx=True)
    cv.put(x0 + 2, y0 + h, (20, 20, 20, 255), fx=True)
    cv.put(x0 + 1, y0 + h + 1, (20, 20, 20, 255), fx=True)
    for i in range(dots):
        cv.put(x0 + 2 + i * 2, y0 + 3, (40, 40, 40, 255), fx=True)


def book(cv: Canvas, ox: int, oy: int, f: int) -> None:
    for y, row in enumerate(BOOK):
        for x, ch in enumerate(row):
            if ch == "C":
                cv.put(ox + x, oy + y, (107, 59, 31, 255), fx=True)
            elif ch == "P":
                c = (232, 226, 208, 255) if y != 2 else (150, 140, 130, 255)
                cv.put(ox + x, oy + y, c, fx=True)
    # enchantment glint wandering over the cover
    sx, sy = [(1, 1), (3, 2), (5, 3), (4, 4), (2, 3), (1, 2)][f]
    cv.put(ox + sx, oy + sy, (199, 125, 255, 255), fx=True)
    cv.put(ox + 3, oy - 2 - (f % 3), (199, 125, 255, 180 - 40 * (f % 3)), fx=True)


# --- per-state frame builders -------------------------------------------------------

LEG_CYCLE = [(-1, 0), (-2, 0), (0, 0), (0, -1), (0, -2), (0, 0)]
RUN_BOB = [-1, -1, 0, -1, -1, 0]


def frame(state: str, f: int) -> Image.Image:
    cv = Canvas()
    flash, flip = 0.0, False

    if state == "idle":
        dy = [0, 0, -1, -1, -1, 0][f]
        creeper(cv, dy=dy)
        shadow(cv, 0)

    elif state in ("running-right", "running-left", "running"):
        ll, lr = LEG_CYCLE[f]
        creeper(cv, dy=RUN_BOB[f], face_dx=0 if state == "running" else 1, leg_l=ll, leg_r=lr)
        shadow(cv, 0)
        if state != "running" and f in (2, 3, 5, 0):
            age = {2: 0, 3: 1, 5: 0, 0: 1}[f]
            puff(cv, 5 - age, 29 - age, 2 + age, 200 - age * 80)
        if state == "running":   # working hard: sweat drop
            cv.put(25, 6 + f % 3, (110, 190, 255, 255), fx=True)
            cv.put(25, 7 + f % 3, (60, 140, 230, 255), fx=True)
        flip = state == "running-left"

    elif state == "waving":
        dy = [0, -1, -2, -2, -1, 0][f]
        creeper(cv, dy=dy, legs_follow=True)
        shadow(cv, -dy)
        heart(cv, 25, 12 - f * 2, 255 - f * 30)
        if f >= 2:
            heart(cv, 2, 16 - (f - 2) * 2, 255 - (f - 2) * 45)

    elif state == "jumping":
        # The head already sits 2px from the frame top, so the hop is short
        # and sold by the crouch (+1), tucked legs and a shrinking shadow.
        dy = [1, -1, -2, -2, -1, 0][f]
        tuck = -1 if f in (2, 3) else 0
        creeper(cv, dy=dy, legs_follow=f != 0, leg_l=tuck, leg_r=tuck)
        shadow(cv, -dy * 3)

    elif state == "failed":
        dx = [-1, 1, -1, 1, -1, 1][f]
        creeper(cv, dx=dx)
        shadow(cv, 0)
        flash = 0.7 if f % 2 else 0.0
        if f >= 2:
            puff(cv, 3, 14 - (f - 2) * 3, 3, 210 - (f - 2) * 40)
            puff(cv, 26, 10 - (f - 2) * 3, 3, 210 - (f - 2) * 40)

    elif state == "waiting":
        dy = [0, 0, 0, -1, -1, -1][f]
        creeper(cv, dy=dy)
        shadow(cv, 0)
        cv.outline()
        bubble(cv, 1 + f // 2)
        return cv.render()

    elif state == "review":
        face = [-1, -1, 0, 1, 1, 0][f]
        creeper(cv, face_dx=face, dy=[0, 0, -1, -1, 0, 0][f])
        shadow(cv, 0)
        cv.outline()
        book(cv, 24, 19 + [0, -1, -1, 0, 1, 1][f], f)
        return cv.render()

    cv.outline()
    return cv.render(flash=flash, flip=flip)


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
        "id": "creeper-buddy",
        "displayName": "Creeper Buddy",
        "description": "A tiny pixel creeper that mines, hops and (almost) explodes alongside Hermes.",
        "spritesheetPath": "spritesheet.png",
    }, indent=2) + "\n", encoding="utf-8")

    # README preview: every state side by side, half size, on a grass strip.
    show = ["idle", "running-right", "waving", "jumping", "failed", "waiting", "review"]
    cell_w, cell_h = FRAME_W // 2, FRAME_H // 2
    gif_frames = []
    for f in range(FRAMES):
        canvas = Image.new("RGBA", (cell_w * len(show), cell_h + 22), (24, 26, 32, 255))
        d = ImageDraw.Draw(canvas)
        for i, s in enumerate(show):
            spr = frames[s][f].resize((cell_w, cell_h), Image.NEAREST)
            canvas.alpha_composite(spr, (i * cell_w, 0))
            d.text((i * cell_w + 6, cell_h + 5), s, fill=(200, 200, 200, 255))
        gif_frames.append(canvas.convert("RGB"))
    pal = gif_frames[0].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    gif_frames = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in gif_frames]
    gif_frames[0].save(DOCS / "pet-preview.gif", save_all=True, append_images=gif_frames[1:],
                       duration=1100 // FRAMES, loop=0, disposal=2)
    print("wrote", PET_DIR / "spritesheet.png", sheet.size)


if __name__ == "__main__":
    main()
