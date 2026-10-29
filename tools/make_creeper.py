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


# --- style variants: same 9 animations, different head / face / proportions ---------
STYLES = {
    "creeper-blocky": dict(name="Creeper Blocky", desc="方正 Q 版：方頭方身、方眼、經典嘴，有光影",
                           head=(10, 4, 28, 24), round=1, bevel=0, body=(15, 27, 18, 14),
                           feet=((12, 39, 7, 6), (29, 39, 7, 6)), eyes="square", eye_x=(4, 18), eye_y=6,
                           eye_size=(6, 5), shine=1, mouth=("classic8", 10, 13), blush=False),
    "creeper-carved": dict(name="Creeper Carved", desc="稜角立體：直角方塊、亮頂面暗側面、雕刻感",
                           head=(9, 5, 30, 22), round=0, bevel=5, body=(14, 27, 20, 13),
                           feet=((11, 39, 8, 6), (29, 39, 8, 6)), eyes="square", eye_x=(4, 19), eye_y=8,
                           eye_size=(7, 4), shine=0, mouth=("classic8", 11, 13), blush=False, inset=True),
    "creeper-tall": dict(name="Creeper Classic", desc="接近原版比例：頭較小、身體較長、四腳外張",
                         head=(12, 4, 24, 20), round=1, bevel=2, body=(16, 23, 16, 18),
                         feet=((11, 40, 8, 5), (29, 40, 8, 5)), eyes="square", eye_x=(4, 15), eye_y=6,
                         eye_size=(5, 4), shine=0, mouth=("classic6", 9, 11), blush=False),
    "creeper-buddy": dict(name="Creeper Buddy", desc="圓潤 Q 版（上一版）：圓眼、亮點、腮紅",
                          head=(10, 4, 28, 24), round=3, bevel=0, body=(15, 27, 18, 14),
                          feet=((12, 39, 7, 6), (29, 39, 7, 6)), eyes="round", eye_x=(5, 18), eye_y=7,
                          eye_size=(5, 5), shine=3, mouth=("chibi", 11, 14), blush=True),
}
DEFAULT = "creeper-blocky"
STYLE = STYLES[DEFAULT]


def use(slug: str) -> None:
    global STYLE
    STYLE = STYLES[slug]


def block(cv: Canvas, x0: int, y0: int, w: int, h: int, round_: int = 1, shade: float = 0.0, bevel: int = 0) -> None:
    """Block with top-left light; `bevel` adds a lit top face and a dark right side."""
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
            if bevel:
                if y < bevel:
                    light += 0.24
                elif x >= w - bevel:
                    light -= 0.2
            cv.put(x0 + x, y0 + y, skin(x0 + x, y0 + y, light))


MOUTHS = {
    "chibi": ["..XX..", ".XXXX.", "XXXXXX", "XX..XX"],
    "classic8": ["..XXXX..", "..XXXX..", "XXXXXXXX", "XXXXXXXX", "XX....XX", "XX....XX"],
    "classic6": ["..XX..", ".XXXX.", ".XXXX.", ".X..X."],
}


def face(cv: Canvas, ox: int, oy: int, eyes: str) -> None:
    st = STYLE
    ew, eh = st["eye_size"]
    ey = oy + st["eye_y"]
    for exo in st["eye_x"]:
        ex = ox + exo
        if eyes == "open":
            for y in range(eh):
                for x in range(ew):
                    if st["eyes"] == "round" and x in (0, ew - 1) and y in (0, eh - 1):
                        continue
                    cv.put(ex + x, ey + y, FACE)
            for k, (sx, sy) in enumerate(((1, 1), (2, 1), (1, 2))):
                if k < st["shine"]:
                    cv.put(ex + sx, ey + sy, SHINE)
        elif eyes == "blink":
            for x in range(ew):
                cv.put(ex + x, ey + eh - 2, FACE)
        elif eyes == "happy":
            for x in range(ew):
                cv.put(ex + x, ey + eh - 1 - min(x, ew - 1 - x, 2), FACE)
        elif eyes == "x":
            n = min(ew, eh)
            for k in range(n):
                cv.put(ex + k, ey + k, FACE)
                cv.put(ex + n - 1 - k, ey + k, FACE)
        elif eyes == "down":
            for y in range(eh // 2, eh):
                for x in range(ew):
                    cv.put(ex + x, ey + y, FACE)
    kind, mx, my = st["mouth"]
    rows = MOUTHS[kind] if eyes != "x" else ["X" * len(MOUTHS[kind][0])]
    if eyes == "x":
        my += 2
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c == "X":
                cv.put(ox + mx + x, oy + my + y, FACE)
    if st.get("inset") and eyes == "open":
        lip = (176, 226, 140, 255)
        for exo in st["eye_x"]:
            for x in range(ew):
                cv.put(ox + exo + x, ey + eh, lip)
        for x, c in enumerate(rows[-1]):
            if c == "X":
                cv.put(ox + mx + x, oy + my + len(rows), lip)
    if st["blush"] and eyes != "x":
        for bx in (ox + 3, ox + 23):
            cv.put(bx, oy + 14, BLUSH)
            cv.put(bx + 1, oy + 14, BLUSH)


def creeper(cv: Canvas, dy: int = 0, dx: int = 0, face_dx: int = 0, eyes: str = "open",
            leg_l: int = 0, leg_r: int = 0, legs_follow: bool = False) -> None:
    st = STYLE
    ly = dy if legs_follow else 0
    small_round = min(1, st["round"])
    for (fx0, fy0, fw, fh), lo in zip(st["feet"], (leg_l, leg_r)):
        block(cv, fx0 + dx, fy0 + ly + lo, fw, fh, round_=small_round, shade=0.12, bevel=st["bevel"] // 2)
    bx, by, bw, bh = st["body"]
    block(cv, bx + dx, by + dy, bw, bh, round_=small_round, shade=0.05, bevel=st["bevel"] // 2)
    hx, hy, hw, hh = st["head"]
    block(cv, hx + dx, hy + dy, hw, hh, round_=st["round"], bevel=st["bevel"])
    face(cv, hx + dx + face_dx, hy + dy, eyes)


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
    x0, y0, w, h = 40, 0, 8, 7
    for y in range(h):
        for x in range(w):
            if x in (0, w - 1) and y in (0, h - 1):
                continue
            edge = x in (0, w - 1) or y in (0, h - 1)
            cv.put(x0 + x, y0 + y, (24, 24, 24, 255) if edge else (250, 250, 250, 255), fx=True)
    for i, (x, y) in enumerate(((3, h), (2, h + 1))):
        cv.put(x0 + x, y0 + y, (24, 24, 24, 255), fx=True)
    for i in range(dots):
        for yy in (0, 1):
            cv.put(x0 + 1 + i * 2, y0 + 2 + yy, (60, 60, 60, 255), fx=True)


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


def head_pixels(slug: str = DEFAULT) -> dict[tuple[int, int], tuple]:
    """Logical pixels of the idle pose (used for the CLI banner hero)."""
    prev = STYLE
    use(slug)
    cv = Canvas()
    creeper(cv)
    cv.outline()
    use(next(k for k, v in STYLES.items() if v is prev))
    return cv.px


def build_variant(slug: str) -> dict[str, list[Image.Image]]:
    use(slug)
    pet_dir = ROOT / "pets" / slug
    pet_dir.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (FRAME_W * COLS, FRAME_H * ROWS), (0, 0, 0, 0))
    frames = {s: [frame(s, f) for f in range(FRAMES)] for s in STATES}
    for r, st in enumerate(STATES):
        for c in range(COLS):
            sheet.paste(frames[st][c % FRAMES], (c * FRAME_W, r * FRAME_H))
    sheet.save(pet_dir / "spritesheet.png", optimize=True)
    (pet_dir / "pet.json").write_text(json.dumps({
        "id": slug,
        "displayName": STYLES[slug]["name"],
        "description": "A pixel creeper that hops, reads and (almost) explodes alongside Hermes.",
        "spritesheetPath": "spritesheet.png",
    }, indent=2) + "\n", encoding="utf-8")
    return frames


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    all_frames = {slug: build_variant(slug) for slug in STYLES}
    use(DEFAULT)

    # comparison: one row per variant, animated through the main states
    show = ["idle", "running-right", "waving", "jumping", "failed", "waiting", "review"]
    cw, ch = FRAME_W // 2, FRAME_H // 2
    label_w = 150
    gif = []
    for f in range(FRAMES):
        canvas = Image.new("RGBA", (label_w + cw * len(show), (ch + 6) * len(STYLES) + 20), (24, 26, 32, 255))
        d = ImageDraw.Draw(canvas)
        for i, st in enumerate(show):
            d.text((label_w + i * cw + 6, 4), st, fill=(150, 150, 150, 255))
        for r, slug in enumerate(STYLES):
            y0 = 20 + r * (ch + 6)
            d.text((8, y0 + ch // 2 - 6), slug, fill=(123, 211, 74, 255))
            for i, st in enumerate(show):
                canvas.alpha_composite(all_frames[slug][st][f].resize((cw, ch), Image.NEAREST), (label_w + i * cw, y0))
        gif.append(canvas.convert("RGB"))
    gif[0].save(DOCS / "creepers.png")
    strip = Image.new("RGB", (gif[0].width, gif[0].height * 2))
    strip.paste(gif[0], (0, 0))
    strip.paste(gif[3], (0, gif[0].height))
    pal = strip.quantize(colors=200, method=Image.Quantize.MEDIANCUT)
    q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in gif]
    q[0].save(DOCS / "creepers.gif", save_all=True, append_images=q[1:], duration=1100 // FRAMES, loop=0)
    print("wrote", ", ".join(f"pets/{k}" for k in STYLES), "+ docs/creepers.gif")


if __name__ == "__main__":
    main()
