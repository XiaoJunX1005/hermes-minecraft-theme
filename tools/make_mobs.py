"""More pets from existing Minecraft mobs, sharing Creeper Buddy's nine-state
animation machinery (make_creeper.frame) but with their own bodies.

Output: pets/mc-<mob>/spritesheet.png + pet.json, docs/mobs.gif comparison.

Run:  python tools/make_mobs.py
"""

from __future__ import annotations

import json
import random

from PIL import Image, ImageDraw

import make_creeper as mc

TICK = 0  # current frame index (for wing flaps / particles)


def part(cv, pal, x0, y0, w, h, round_=1, shade=0.0, bevel=0):
    """Shaded block in `pal` (6 rgb tuples, dark -> light)."""
    prev = mc.GREENS
    mc.GREENS = pal
    mc.block(cv, x0, y0, w, h, round_=round_, shade=shade, bevel=bevel)
    mc.GREENS = prev


def rect(cv, x0, y0, w, h, c, fx=False):
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            cv.put(x, y, c, fx=fx)


def eye(cv, x, y, w, h, eyes, col, white=None):
    """One eye box; `white` draws the Minecraft-style white eye with a dark pupil."""
    if eyes == "open":
        if white:
            rect(cv, x, y, w, h, white)
            rect(cv, x + w - 2, y + h - 2, 2, 2, col)
        else:
            rect(cv, x, y, w, h, col)
    elif eyes == "blink":
        rect(cv, x, y + h - 1, w, 1, col)
    elif eyes == "happy":
        for k in range(w):
            cv.put(x + k, y + h - 1 - min(k, w - 1 - k, 1), col)
    elif eyes == "x":
        n = min(w, h)
        for k in range(n):
            cv.put(x + k, y + k, col)
            cv.put(x + n - 1 - k, y + k, col)
    elif eyes == "down":
        rect(cv, x, y + h // 2, w, h - h // 2, col)


# --- palettes ------------------------------------------------------------------------------
PINK = [(186, 100, 108), (204, 120, 126), (220, 140, 144), (232, 158, 158), (242, 176, 174), (250, 198, 194)]
SNOUT = [(214, 132, 138), (226, 150, 152), (236, 166, 166), (244, 182, 180), (250, 196, 192), (254, 212, 206)]
WHITE = [(188, 188, 184), (206, 206, 200), (222, 222, 216), (234, 234, 228), (244, 244, 238), (252, 252, 248)]
SLIME = [(70, 136, 58), (84, 154, 68), (100, 172, 80), (116, 188, 94), (134, 204, 110), (156, 220, 130)]
YELLOW = [(200, 142, 36), (218, 162, 46), (232, 180, 56), (242, 196, 68), (250, 212, 90), (255, 226, 118)]
VOID = [(14, 12, 18), (20, 18, 26), (26, 24, 32), (32, 30, 40), (40, 38, 50), (50, 48, 62)]
DARK = (40, 24, 28, 255)


def pig(cv, dy=0, dx=0, face_dx=0, eyes="open", leg_l=0, leg_r=0, legs_follow=False):
    ly = dy if legs_follow else 0
    for (fx0, lo) in ((12, leg_l), (29, leg_r)):
        part(cv, PINK, fx0 + dx, 39 + ly + lo, 7, 6, shade=0.15)
    part(cv, PINK, 13 + dx, 26 + dy, 22, 14, shade=0.06)
    hx, hy = 10 + dx, 5 + dy
    part(cv, PINK, hx, hy, 28, 22)
    fx = hx + face_dx
    for ex in (fx + 4, fx + 19):
        eye(cv, ex, hy + 6, 5, 4, eyes, DARK, white=(246, 242, 238, 255))
    part(cv, SNOUT, fx + 8, hy + 12, 12, 7, round_=1)
    rect(cv, fx + 10, hy + 14, 2, 3, (150, 74, 84, 255))
    rect(cv, fx + 16, hy + 14, 2, 3, (150, 74, 84, 255))
    if eyes == "x":
        rect(cv, fx + 11, hy + 20, 6, 1, DARK)


def chicken(cv, dy=0, dx=0, face_dx=0, eyes="open", leg_l=0, leg_r=0, legs_follow=False):
    ly = dy if legs_follow else 0
    leg = (232, 176, 56, 255)
    for (lx, lo) in ((18, leg_l), (28, leg_r)):
        rect(cv, lx + dx, 38 + ly + lo, 2, 6, leg)
        rect(cv, lx - 1 + dx, 44 + ly + lo, 4, 1, leg)
    part(cv, WHITE, 12 + dx, 22 + dy, 24, 17, round_=2, shade=0.04)
    part(cv, WHITE, 10 + dx, 25 + dy, 4, 10, round_=1, shade=0.25)   # wings
    part(cv, WHITE, 34 + dx, 25 + dy, 4, 10, round_=1, shade=0.25)
    hx, hy = 15 + dx, 7 + dy
    part(cv, WHITE, hx, hy, 18, 16, round_=1)
    fx = hx + face_dx
    rect(cv, fx + 5, hy - 3, 8, 3, (214, 44, 44, 255))                 # comb
    for ex in (fx + 3, fx + 13):
        eye(cv, ex, hy + 4, 2, 3, eyes, (20, 20, 24, 255))
    rect(cv, fx + 6, hy + 8, 6, 3, (238, 156, 40, 255))                # beak
    rect(cv, fx + 7, hy + 11, 4, 3, (214, 44, 44, 255))                # wattle


def slime(cv, dy=0, dx=0, face_dx=0, eyes="open", leg_l=0, leg_r=0, legs_follow=False):
    k = -(leg_l + leg_r)            # 0..2: squash while "walking"
    w, h = 26 + 2 * k, 26 - 2 * k
    x0, y0 = 24 - w // 2 + dx, 45 - h + dy
    rng = random.Random(3)
    for y in range(h):
        for x in range(w):
            r, g, b = SLIME[min(5, 2 + (y < 2) * 2 + (x < 2) - (x >= w - 2) - (y >= h - 2) + rng.choice((0, 0, 1)))]
            cv.put(x0 + x, y0 + y, (r, g, b, 200))
    part(cv, SLIME[:3] + SLIME[:3], x0 + 6, y0 + 6, w - 12, h - 12, round_=0)
    fx = x0 + face_dx
    for ex in (fx + 4, fx + w - 9):
        eye(cv, ex, y0 + 7, 5, 5, eyes, (24, 44, 22, 255))
    if eyes != "x":
        rect(cv, fx + w // 2 + 2, y0 + h - 9, 3, 2, (24, 44, 22, 255))


def bee(cv, dy=0, dx=0, face_dx=0, eyes="open", leg_l=0, leg_r=0, legs_follow=False):
    dy += [-3, -4, -4, -3, -2, -2][TICK % 6]     # hovering
    x0, y0 = 10 + dx, 14 + dy
    wing = (226, 240, 255, 130)
    flap = -2 if TICK % 2 == 0 else 1
    for wx in (x0 - 7, x0 + 28):          # flat translucent wings on the body's sides
        rect(cv, wx, y0 + 6 + flap, 7, 4, wing, fx=True)
        rect(cv, wx + 1, y0 + 5 + flap, 5, 1, wing, fx=True)
    for (lx, lo) in ((x0 + 6, leg_l), (x0 + 19, leg_r)):
        rect(cv, lx, y0 + 21 + lo, 2, 4, (60, 40, 26, 255))
    part(cv, YELLOW, x0, y0, 28, 22, round_=1)
    for sy in (y0 + 14, y0 + 18):
        rect(cv, x0 + 1, sy, 26, 2, (60, 40, 26, 255))
    fx = x0 + face_dx
    rect(cv, fx + 8, y0 - 4, 2, 4, (60, 40, 26, 255))                  # antennae
    rect(cv, fx + 18, y0 - 4, 2, 4, (60, 40, 26, 255))
    for ex in (fx + 3, fx + 18):
        eye(cv, ex, y0 + 4, 7, 7, eyes, (24, 22, 30, 255))
        if eyes == "open":
            cv.put(ex + 1, y0 + 5, (200, 220, 255, 255))
    rect(cv, fx + 12, y0 + 10, 4, 1, (120, 70, 30, 255))


def enderman(cv, dy=0, dx=0, face_dx=0, eyes="open", leg_l=0, leg_r=0, legs_follow=False):
    ly = dy if legs_follow else 0
    for (lx, lo) in ((18, leg_l), (26, leg_r)):
        part(cv, VOID, lx + dx, 34 + ly + lo, 4, 12, round_=0, shade=0.1)
    part(cv, VOID, 13 + dx, 19 + dy, 3, 21, round_=0, shade=0.1)        # arms
    part(cv, VOID, 32 + dx, 19 + dy, 3, 21, round_=0, shade=0.1)
    part(cv, VOID, 17 + dx, 18 + dy, 14, 17, round_=0)
    hx, hy = 13 + dx, 3 + dy
    part(cv, VOID, hx, hy, 22, 16, round_=0, bevel=2)
    purple, glow = (200, 80, 255, 255), (238, 170, 255, 255)
    fx = hx + face_dx
    for ex in (fx + 2, fx + 13):
        if eyes == "x":
            eye(cv, ex + 2, hy + 7, 4, 4, "x", purple)
            continue
        eye(cv, ex, hy + 9, 7, 2, eyes, purple)
        if eyes == "open":
            rect(cv, ex + 2, hy + 9, 3, 1, glow)
    rng = random.Random(TICK)
    for _ in range(3):                                                  # ender particles
        x, y = rng.randrange(6, 42), rng.randrange(4, 44)
        cv.put(x, y, (180, 70, 240, 200), fx=True)
        cv.put(x + 1, y, (120, 40, 180, 160), fx=True)


MOBS = {
    "mc-pig": dict(name="Pig", zh="豬", draw=pig, pal=PINK, outline=(96, 44, 52, 255)),
    "mc-chicken": dict(name="Chicken", zh="雞", draw=chicken, pal=WHITE, outline=(64, 64, 70, 255)),
    "mc-slime": dict(name="Slime", zh="史萊姆", draw=slime, pal=SLIME, outline=(30, 70, 26, 255)),
    "mc-bee": dict(name="Bee", zh="蜜蜂", draw=bee, pal=YELLOW, outline=(64, 42, 18, 255)),
    "mc-enderman": dict(name="Enderman", zh="終界使者", draw=enderman, pal=VOID, outline=(112, 64, 150, 255)),
}


def build(slug: str) -> dict[str, list[Image.Image]]:
    global TICK
    spec = MOBS[slug]
    mc.creeper = spec["draw"]
    mc.GREENS = spec["pal"]
    mc.OUTLINE = spec["outline"]
    frames = {}
    for st in mc.STATES:
        frames[st] = []
        for f in range(mc.FRAMES):
            TICK = f
            frames[st].append(mc.frame(st, f))
    d = mc.ROOT / "pets" / slug
    d.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (mc.FRAME_W * mc.COLS, mc.FRAME_H * mc.ROWS), (0, 0, 0, 0))
    for r, st in enumerate(mc.STATES):
        for c in range(mc.COLS):
            sheet.paste(frames[st][c % mc.FRAMES], (c * mc.FRAME_W, r * mc.FRAME_H))
    sheet.save(d / "spritesheet.png", optimize=True)
    (d / "pet.json").write_text(json.dumps({
        "id": slug, "displayName": f"{spec['name']} Buddy",
        "description": f"A pixel {spec['name'].lower()} that hops, reads and reacts alongside Hermes.",
        "spritesheetPath": "spritesheet.png"}, indent=2) + "\n", encoding="utf-8")
    return frames


def main() -> None:
    allf = {slug: build(slug) for slug in MOBS}
    show = ["idle", "running-right", "waving", "jumping", "failed", "waiting", "review"]
    cw, ch, label_w = mc.FRAME_W // 2, mc.FRAME_H // 2, 130
    gif = []
    for f in range(mc.FRAMES):
        c = Image.new("RGBA", (label_w + cw * len(show), (ch + 6) * len(MOBS) + 20), (24, 26, 32, 255))
        d = ImageDraw.Draw(c)
        for i, st in enumerate(show):
            d.text((label_w + i * cw + 6, 4), st, fill=(150, 150, 150, 255))
        for r, slug in enumerate(MOBS):
            y0 = 20 + r * (ch + 6)
            d.text((8, y0 + ch // 2 - 6), slug, fill=(123, 211, 74, 255))
            for i, st in enumerate(show):
                c.alpha_composite(allf[slug][st][f].resize((cw, ch), Image.NEAREST), (label_w + i * cw, y0))
        gif.append(c.convert("RGB"))
    gif[0].save(mc.DOCS / "mobs.png")
    strip = Image.new("RGB", (gif[0].width, gif[0].height * 2))
    strip.paste(gif[0], (0, 0))
    strip.paste(gif[3], (0, gif[0].height))
    pal = strip.quantize(colors=220, method=Image.Quantize.MEDIANCUT)
    q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in gif]
    q[0].save(mc.DOCS / "mobs.gif", save_all=True, append_images=q[1:], duration=1100 // mc.FRAMES, loop=0)
    print("wrote", ", ".join(f"pets/{s}" for s in MOBS), "+ docs/mobs.gif")


if __name__ == "__main__":
    main()
