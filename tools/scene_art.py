"""Background landmark sprites drawn on the per-world scene layer (trees, igloo,
nether fungi, End city, chorus, crystals, exit portal). Original pixel art.

    from scene_art import atlas
    img, boxes = atlas()      # boxes: name -> [x, y, w, h]
"""

from __future__ import annotations

import math
import random

from PIL import Image


class Spr:
    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    def p(self, x, y, c) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.im.putpixel((int(x), int(y)), c)

    def rect(self, x, y, w, h, c) -> None:
        for yy in range(int(y), int(y + h)):
            for xx in range(int(x), int(x + w)):
                self.p(xx, yy, c)

    def blob(self, cx, cy, rx, ry, cols, seed) -> None:
        """Leafy canopy: lit top-left, darker bottom-right, ragged edge."""
        rng = random.Random(seed)
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if d > 1 + rng.uniform(-0.18, 0.05):
                    continue
                k = (x - cx) / rx * 0.5 + (y - cy) / ry * 0.6 + rng.uniform(-0.3, 0.3)
                c = cols[0] if k < -0.35 else cols[1] if k < 0.15 else cols[2]
                self.p(x, y, c)


def oak() -> Spr:
    s = Spr(22, 26)
    s.rect(10, 13, 3, 13, (110, 80, 50, 255))
    s.p(9, 25, (110, 80, 50, 255))
    s.p(13, 25, (110, 80, 50, 255))
    s.blob(11, 9, 10, 8, [(120, 190, 90, 255), (84, 150, 64, 255), (56, 110, 46, 255)], 1)
    return s


def birch() -> Spr:
    s = Spr(14, 28)
    for y in range(12, 28):
        s.rect(6, y, 2, 1, (60, 60, 60, 255) if y % 4 == 0 else (230, 230, 220, 255))
    s.blob(7, 8, 6, 8, [(170, 210, 110, 255), (130, 180, 80, 255), (96, 140, 60, 255)], 2)
    return s


def flowers() -> Spr:
    s = Spr(12, 6)
    for x, c in ((1, (230, 60, 60, 255)), (4, (250, 220, 60, 255)), (7, (120, 150, 255, 255)), (10, (240, 240, 240, 255))):
        s.rect(x, 3, 1, 3, (80, 150, 60, 255))
        s.rect(x - 1 if x > 0 else x, 1, 2, 2, c)
    return s


def cherry() -> Spr:
    s = Spr(28, 24)
    s.rect(13, 11, 3, 13, (70, 44, 52, 255))
    s.rect(10, 13, 3, 1, (70, 44, 52, 255))
    s.rect(16, 12, 4, 1, (70, 44, 52, 255))
    s.blob(14, 8, 13, 7, [(255, 210, 230, 255), (240, 160, 200, 255), (210, 120, 170, 255)], 3)
    for x, y in ((3, 15), (6, 16), (23, 15), (25, 17)):
        s.p(x, y, (240, 160, 200, 255))  # drooping petals
    return s


def spruce() -> Spr:
    s = Spr(18, 30)
    s.rect(8, 23, 2, 7, (90, 60, 40, 255))
    for i, (y, half) in enumerate(((3, 3), (8, 5), (13, 7), (18, 8))):
        for k in range(6):
            w = round(half * (k + 1) / 6)
            yy = y + k
            for x in range(9 - w, 9 + w):
                edge = k == 0 or x in (9 - w, 9 + w - 1)
                s.p(x, yy, (225, 240, 255, 255) if edge and k < 2 else (40, 90, 66, 255) if x < 9 else (30, 70, 52, 255))
    s.rect(8, 1, 2, 2, (225, 240, 255, 255))
    return s


def igloo() -> Spr:
    s = Spr(24, 12)
    for y in range(12):
        for x in range(24):
            if ((x - 11.5) / 11.5) ** 2 + ((y - 12) / 11) ** 2 <= 1:
                line = y % 4 == 0 or (x + (y // 4) * 3) % 6 == 0
                s.p(x, y, (190, 210, 235, 255) if line else (235, 245, 255, 255))
    s.rect(9, 6, 6, 6, (60, 70, 90, 255))
    return s


def fungus(crimson: bool) -> Spr:
    s = Spr(20, 24)
    stem = (120, 40, 60, 255) if crimson else (60, 150, 150, 255)
    s.rect(9, 10, 3, 14, stem)
    s.rect(8, 22, 5, 2, stem)
    cap = [(240, 80, 70, 255), (200, 40, 50, 255), (150, 24, 36, 255)] if crimson else \
          [(80, 230, 200, 255), (40, 180, 160, 255), (24, 130, 120, 255)]
    for y in range(0, 10):
        half = 9 - abs(y - 5)
        for x in range(10 - half, 10 + half):
            k = (x - 10) / 10 + (y - 4) / 10
            s.p(x, y, cap[0] if k < -0.2 else cap[1] if k < 0.25 else cap[2])
    for x, y in ((5, 4), (13, 3), (9, 7)):
        s.p(x, y, (255, 220, 120, 255))  # shroomlight specks
    return s


def chorus() -> Spr:
    """Blocky chorus tree: stacked 3x3 segments with pale flower blocks on the tips."""
    s = Spr(16, 24)
    st, lit, dk, fl = (160, 110, 180, 255), (195, 150, 210, 255), (120, 80, 140, 255), (235, 210, 248, 255)

    def seg(x, y):
        s.rect(x, y, 3, 3, st)
        s.rect(x, y, 3, 1, lit)
        s.p(x + 2, y + 2, dk)

    for y in (21, 18, 15, 12, 9, 6):
        seg(7, y)
    for x in (4, 1):
        seg(x, 12)
    for y in (9, 6):
        seg(1, y)
    for x in (10, 13):
        seg(x, 15)
    for y in (12, 9):
        seg(13, y)
    for x, y in ((1, 3), (7, 3), (13, 6)):
        s.rect(x, y, 3, 3, fl)
    return s


def endcity() -> Spr:
    s = Spr(18, 44)
    pur, purd, purl = (190, 140, 200, 255), (150, 100, 165, 255), (220, 180, 230, 255)
    for (x, y, w, h) in ((2, 22, 14, 22), (4, 8, 10, 14)):
        s.rect(x, y, w, h, pur)
        s.rect(x, y, w, 1, purl)
        s.rect(x + w - 1, y, 1, h, purd)
        for wy in range(y + 3, y + h - 2, 5):
            s.rect(x + 3, wy, 2, 2, (40, 20, 50, 255))
            s.rect(x + w - 5, wy, 2, 2, (40, 20, 50, 255))
    s.rect(0, 20, 18, 2, purd)
    s.rect(2, 6, 14, 2, purd)
    for x in (4, 9, 13):
        s.rect(x, 2, 1, 4, (240, 230, 250, 255))  # end rods
        s.p(x, 1, (255, 255, 255, 255))
    return s


def crystal() -> Spr:
    s = Spr(7, 7)
    for y in range(7):
        w = 3 - abs(y - 3)
        for x in range(3 - w, 4 + w):
            s.p(x, y, (255, 180, 240, 255) if (x + y) % 3 else (255, 240, 255, 255))
    return s


def portal() -> Spr:
    s = Spr(28, 9)
    bed = (120, 120, 126, 255)
    s.rect(0, 5, 28, 4, bed)
    s.rect(3, 3, 22, 2, bed)
    s.rect(6, 4, 16, 2, (30, 20, 50, 255))
    for x in range(7, 21, 3):
        s.p(x, 4, (160, 120, 255, 255))
    s.rect(13, 0, 2, 4, bed)
    return s


def kelp() -> Spr:
    """Kelp: wavy stalk with broad leaf blades alternating left/right, bulb on top."""
    s = Spr(10, 30)
    stalk, leaf, lit = (60, 120, 60, 255), (80, 150, 70, 255), (120, 190, 100, 255)
    for y in range(30):
        x = 4 + round(math.sin(y / 4) * 1.2)
        s.rect(x, y, 2, 1, stalk)
        if y % 4 == 1:
            side = -1 if (y // 4) % 2 else 1
            for k in range(1, 4):
                s.p(x + (1 + k if side > 0 else -k), y + (k > 1), leaf)
            s.p(x + (2 if side > 0 else -1), y, lit)
    s.rect(3, 0, 4, 2, lit)
    return s


def seagrass() -> Spr:
    """Seagrass: a dense low clump of blades in two greens."""
    s = Spr(14, 11)
    for x, h, c in ((0, 5, 0), (1, 8, 1), (2, 10, 0), (3, 7, 1), (5, 11, 0), (6, 9, 1), (7, 6, 0),
                    (8, 10, 1), (9, 8, 0), (10, 11, 1), (11, 7, 0), (12, 9, 1), (13, 5, 0)):
        col = (80, 160, 80, 255) if c else (110, 190, 100, 255)
        for y in range(11 - h, 11):
            s.p(x + (1 if y < 11 - h + 2 and x % 3 == 0 else 0), y, col)
    return s


def coral() -> Spr:
    s = Spr(16, 12)
    for x0, c in ((1, (240, 90, 120, 255)), (6, (250, 200, 70, 255)), (11, (120, 140, 250, 255))):
        s.rect(x0 + 1, 6, 2, 6, c)
        s.rect(x0, 3, 1, 4, c)
        s.rect(x0 + 3, 2, 1, 5, c)
        s.p(x0 + 1, 1, c)
    return s


def azalea() -> Spr:
    s = Spr(18, 14)
    s.blob(9, 7, 8, 6, [(130, 190, 80, 255), (96, 150, 60, 255), (70, 115, 46, 255)], 7)
    for x, y in ((4, 4), (9, 3), (13, 6), (6, 9), (12, 10)):
        s.rect(x, y, 2, 2, (240, 140, 210, 255))
    return s


def dripleaf() -> Spr:
    s = Spr(14, 16)
    s.rect(6, 5, 2, 11, (90, 150, 60, 255))
    s.rect(0, 3, 14, 2, (120, 190, 80, 255))
    s.rect(1, 2, 12, 1, (150, 210, 100, 255))
    return s


def vine() -> Spr:
    """Cave vine: thin stem with leaf pairs."""
    s = Spr(7, 24)
    for y in range(24):
        x = 3 + (1 if (y // 5) % 2 else 0)
        s.p(x, y, (60, 120, 55, 255))
        if y % 3 == 1:
            s.rect(x - 2, y, 2, 1, (100, 170, 80, 255))
            s.rect(x + 1, y + 1, 2, 1, (90, 160, 70, 255))
    return s


def berryvine() -> Spr:
    """Cave vine carrying glow berries: bright orange 3x3 clusters with a hot centre."""
    s = vine()
    for y in (4, 11, 18):
        s.rect(1, y, 3, 3, (240, 140, 40, 255))
        s.p(2, y + 1, (255, 230, 140, 255))
        s.rect(4, y + 3, 2, 2, (240, 140, 40, 255))
    return s


def cactus() -> Spr:
    s = Spr(12, 24)
    s.rect(4, 2, 4, 22, (80, 150, 60, 255))
    s.rect(4, 2, 1, 22, (110, 180, 80, 255))
    s.rect(0, 9, 4, 2, (80, 150, 60, 255))
    s.rect(0, 5, 2, 4, (80, 150, 60, 255))
    s.rect(8, 13, 3, 2, (80, 150, 60, 255))
    s.rect(10, 9, 2, 4, (80, 150, 60, 255))
    for y in range(4, 24, 4):
        s.p(7, y, (40, 80, 30, 255))
    return s


def deadbush() -> Spr:
    s = Spr(10, 8)
    bc = (150, 110, 60, 255)
    for x, y in ((5, 7), (5, 6), (4, 5), (3, 4), (2, 3), (6, 5), (7, 4), (8, 2), (4, 3), (6, 3), (6, 2)):
        s.p(x, y, bc)
    return s


def temple() -> Spr:
    s = Spr(34, 22)
    ss, sd = (226, 206, 150, 255), (196, 172, 116, 255)
    for k in range(8):
        s.rect(5 + k, 22 - (k + 1) * 2, 24 - 2 * k, 2, ss if k % 2 else sd)
    for x in (0, 28):
        s.rect(x, 6, 6, 16, ss)
        s.rect(x, 6, 6, 1, sd)
        s.rect(x + 1, 3, 4, 3, sd)
        s.rect(x + 2, 10, 2, 1, (210, 110, 50, 255))
        s.rect(x + 2, 13, 2, 1, (70, 110, 200, 255))
    s.rect(14, 15, 6, 7, (60, 44, 30, 255))
    return s


def redshroom() -> Spr:
    s = Spr(22, 24)
    s.rect(9, 10, 4, 14, (232, 226, 210, 255))
    for y in range(11):
        half = round(10 * math.sqrt(max(0.0, 1 - ((y - 10) / 10.5) ** 2)))
        for x in range(11 - half, 11 + half):
            s.p(x, y, (210, 50, 40, 255) if x < 14 else (176, 34, 30, 255))
    for x, y in ((6, 4), (12, 2), (15, 6), (9, 7), (3, 8)):
        s.rect(x, y, 2, 2, (245, 245, 240, 255))
    return s


def brownshroom() -> Spr:
    s = Spr(26, 14)
    s.rect(11, 5, 4, 9, (232, 226, 210, 255))
    s.rect(0, 2, 26, 4, (170, 120, 80, 255))
    s.rect(2, 1, 22, 1, (196, 146, 100, 255))
    s.rect(0, 5, 26, 1, (130, 90, 60, 255))
    return s


def sensor() -> Spr:
    s = Spr(8, 9)
    s.rect(0, 4, 8, 5, (20, 70, 80, 255))
    for x in (1, 3, 5, 7):
        s.rect(x, 1 + (x % 3), 1, 4 - (x % 3), (60, 230, 240, 255))
    return s


def shrieker() -> Spr:
    s = Spr(12, 10)
    s.rect(0, 5, 12, 5, (20, 70, 80, 255))
    s.rect(1, 1, 10, 4, (226, 220, 196, 255))
    s.rect(3, 2, 6, 2, (40, 40, 44, 255))
    return s


def citywall() -> Spr:
    s = Spr(40, 28)
    ds, dl = (70, 80, 96, 255), (100, 112, 130, 255)
    s.rect(0, 6, 40, 22, ds)
    s.rect(0, 6, 40, 1, dl)
    for x0 in (4, 17, 30):
        for y in range(12, 28):
            for x in range(x0, x0 + 7):
                if y > 15 or (x - x0 - 3) ** 2 + (y - 15) ** 2 <= 10:
                    s.p(x, y, (0, 0, 0, 0))
    for x in (2, 16, 29):
        s.rect(x, 2, 3, 4, ds)
    s.rect(18, 8, 4, 2, (60, 230, 240, 255))
    return s


OAK_LEAF = [(120, 190, 90, 255), (84, 150, 64, 255), (56, 110, 46, 255)]
PINK_LEAF = [(255, 210, 230, 255), (240, 160, 200, 255), (210, 120, 170, 255)]
TRUNK = (110, 80, 50, 255)


def oak_wide() -> Spr:
    """Low, wide oak with a two-lobed canopy."""
    s = Spr(30, 22)
    s.rect(14, 11, 3, 11, TRUNK)
    s.rect(10, 13, 4, 1, TRUNK)
    s.rect(17, 12, 4, 1, TRUNK)
    s.blob(9, 8, 8, 6, OAK_LEAF, 11)
    s.blob(20, 7, 9, 6, OAK_LEAF, 12)
    s.blob(15, 5, 7, 5, OAK_LEAF, 13)
    return s


def oak_tall() -> Spr:
    """Tall narrow oak."""
    s = Spr(18, 34)
    s.rect(8, 16, 3, 18, TRUNK)
    s.blob(9, 10, 8, 10, OAK_LEAF, 14)
    return s


def birch_tall() -> Spr:
    s = Spr(12, 36)
    for y in range(13, 36):
        s.rect(5, y, 2, 1, (60, 60, 60, 255) if y % 5 == 0 else (232, 232, 222, 255))
    s.blob(6, 8, 5, 8, [(176, 214, 116, 255), (138, 186, 86, 255), (100, 146, 64, 255)], 15)
    return s


def cherry_tall() -> Spr:
    s = Spr(22, 30)
    s.rect(10, 13, 3, 17, (70, 44, 52, 255))
    s.rect(7, 16, 3, 1, (70, 44, 52, 255))
    s.blob(11, 8, 10, 8, PINK_LEAF, 16)
    for x, y in ((2, 13), (19, 14), (4, 16)):
        s.p(x, y, (240, 160, 200, 255))
    return s


def cherry_lean() -> Spr:
    """Cherry tree leaning to one side with a drooping canopy."""
    s = Spr(32, 26)
    for y in range(9, 26):
        x = 9 + (26 - y) // 3
        s.rect(x, y, 3, 1, (70, 44, 52, 255))
    s.blob(19, 7, 12, 6, PINK_LEAF, 17)
    for x, y in ((8, 11), (10, 13), (28, 12), (30, 14), (25, 14)):
        s.p(x, y, (240, 160, 200, 255))
    return s


def spruce_v(W, H, tiers, snow=True) -> Spr:
    s = Spr(W, H)
    cx = W // 2
    s.rect(cx - 1, H - 7, 2, 7, (90, 60, 40, 255))
    for (y, half) in tiers:
        for k in range(6):
            w = round(half * (k + 1) / 6)
            for x in range(cx - w, cx + w):
                edge = k == 0 or x in (cx - w, cx + w - 1)
                s.p(x, y + k, (225, 240, 255, 255) if snow and edge and k < 2 else (40, 90, 66, 255) if x < cx else (30, 70, 52, 255))
    s.rect(cx - 1, max(0, tiers[0][0] - 2), 2, 2, (225, 240, 255, 255))
    return s


def huge_fungus(crimson, W, H, cap, stem_w, lean, seed, vines) -> Spr:
    """Huge crimson / warped fungus: thick stem, wide wart-block cap with a ragged rim,
    shroomlights, weeping vines (crimson) or twisting vines (warped)."""
    rng = random.Random(seed)
    s = Spr(W, H)
    cx = W // 2
    stem, stem_l = ((116, 38, 58, 255), (160, 70, 92, 255)) if crimson else ((36, 110, 112, 255), (70, 160, 156, 255))
    for y in range(cap - 2, H):
        t = (y - cap) / max(1, H - cap)
        x = round(cx - stem_w / 2 + lean * (1 - t))
        s.rect(x, y, stem_w, 1, stem)
        s.p(x, y, stem_l)
    caps = [(220, 60, 54, 255), (178, 34, 40, 255), (126, 22, 30, 255)] if crimson else \
           [(46, 196, 176, 255), (26, 150, 142, 255), (18, 108, 104, 255)]
    capx = cx + lean
    half = W / 2 - 0.5
    for x in range(W):
        dx = (x - capx) / half
        if abs(dx) > 1:
            continue
        top = round(cap * 0.35 * dx * dx)
        bot = cap - 1 + (rng.randint(0, 3) if abs(dx) > 0.35 else rng.randint(0, 1))
        for y in range(top, bot):
            k = dx * 0.45 + (y / cap) * 0.8 + rng.uniform(-0.25, 0.25)
            s.p(x, y, caps[0] if k < 0.25 else caps[1] if k < 0.75 else caps[2])
    for _ in range(2 + rng.randint(0, 2)):
        x = capx + rng.randint(-W // 3, W // 3 - 1)
        y = rng.randint(max(1, cap // 3), cap - 3)
        s.rect(x, y, 2, 2, (255, 196, 104, 255))
        s.p(x, y, (255, 242, 196, 255))
    for _ in range(vines):
        x = capx + rng.randint(-W // 2 + 2, W // 2 - 3)
        if crimson:
            for y in range(cap, min(H - 3, cap + rng.randint(4, 11))):
                s.p(x, y, (196, 40, 52, 255))
        else:
            for k in range(rng.randint(5, 12)):
                s.p(x + (1 if (k // 2) % 2 else 0), H - 1 - k, (40, 176, 156, 255))
    return s


def kelp_v(H, ph) -> Spr:
    s = Spr(10, H)
    stalk, leaf, lit = (60, 120, 60, 255), (80, 150, 70, 255), (120, 190, 100, 255)
    for y in range(H):
        x = 4 + round(math.sin(y / 4 + ph) * 1.2)
        s.rect(x, y, 2, 1, stalk)
        if y % 4 == 1:
            side = -1 if (y // 4) % 2 else 1
            for k in range(1, 4):
                s.p(x + (1 + k if side > 0 else -k), y + (k > 1), leaf)
    s.rect(3, 0, 4, 2, lit)
    return s


def coral_fan() -> Spr:
    """Fan coral + brain coral."""
    s = Spr(20, 12)
    fan = (180, 90, 220, 255)
    for y in range(9):
        w = 1 + (8 - y) // 2
        for x in range(5 - w, 5 + w + 1):
            if (x + y) % 3:
                s.p(x, y + 1, fan)
    s.rect(4, 9, 2, 3, fan)
    for y in range(6, 12):
        for x in range(9, 19):
            if ((x - 13.5) / 5) ** 2 + ((y - 11) / 5) ** 2 <= 1:
                s.p(x, y, (240, 120, 150, 255) if (x + y) % 2 else (210, 90, 120, 255))
    return s


def seagrass_tall() -> Spr:
    s = Spr(8, 22)
    for x, h, c in ((1, 22, (90, 170, 90, 255)), (3, 16, (110, 190, 100, 255)), (5, 20, (80, 160, 80, 255))):
        for y in range(22 - h, 22):
            s.p(x + (1 if (y // 6) % 2 else 0), y, c)
    return s


def cactus_one() -> Spr:
    s = Spr(10, 26)
    g, lit = (80, 150, 60, 255), (110, 180, 80, 255)
    s.rect(3, 0, 4, 26, g)
    s.rect(3, 0, 1, 26, lit)
    s.rect(7, 13, 2, 2, g)
    s.rect(8, 7, 2, 7, g)
    for y in range(3, 26, 4):
        s.p(6, y, (40, 80, 30, 255))
    return s


def cactus_plain() -> Spr:
    s = Spr(6, 30)
    s.rect(1, 0, 4, 30, (80, 150, 60, 255))
    s.rect(1, 0, 1, 30, (110, 180, 80, 255))
    for y in range(3, 30, 4):
        s.p(4, y, (40, 80, 30, 255))
    return s


def redshroom_tall() -> Spr:
    s = Spr(16, 28)
    s.rect(6, 8, 4, 20, (232, 226, 210, 255))
    for y in range(9):
        half = round(8 * math.sqrt(max(0.0, 1 - ((y - 8) / 8.5) ** 2)))
        for x in range(8 - half, 8 + half):
            s.p(x, y, (210, 50, 40, 255) if x < 10 else (176, 34, 30, 255))
    for x, y in ((4, 4), (9, 2), (11, 6), (6, 6)):
        s.rect(x, y, 2, 2, (245, 245, 240, 255))
    return s


def brownshroom_wide() -> Spr:
    s = Spr(34, 18)
    s.rect(15, 6, 4, 12, (232, 226, 210, 255))
    s.rect(0, 2, 34, 4, (170, 120, 80, 255))
    s.rect(2, 1, 30, 1, (196, 146, 100, 255))
    s.rect(0, 5, 34, 1, (130, 90, 60, 255))
    return s


def azalea_tree() -> Spr:
    s = Spr(22, 24)
    s.rect(10, 12, 2, 12, (110, 80, 50, 255))
    s.rect(7, 15, 3, 1, (110, 80, 50, 255))
    s.blob(11, 7, 10, 6, [(130, 190, 80, 255), (96, 150, 60, 255), (70, 115, 46, 255)], 18)
    for x, y in ((5, 4), (11, 2), (16, 6), (8, 8), (14, 9)):
        s.rect(x, y, 2, 2, (240, 140, 210, 255))
    return s


def dripstone() -> Spr:
    """Pointed dripstone hanging from a cave ceiling."""
    s = Spr(12, 16)
    for x0, h in ((0, 12), (4, 8), (7, 16), (10, 6)):
        for y in range(h):
            w = max(1, round(2.5 * (1 - y / h)))
            s.rect(x0 + (2 - w // 2) - 1, y, w, 1, (150, 120, 100, 255) if y % 3 else (120, 96, 80, 255))
    return s


PROPS = {"oak": oak, "birch": birch, "flowers": flowers, "cherry": cherry, "spruce": spruce, "igloo": igloo,
         "crimson": lambda: fungus(True), "warped": lambda: fungus(False), "chorus": chorus, "endcity": endcity,
         "crystal": crystal, "portal": portal,
         "kelp": kelp, "seagrass": seagrass, "coral": coral, "azalea": azalea, "dripleaf": dripleaf, "vine": vine,
         "berryvine": berryvine, "cactus": cactus, "deadbush": deadbush, "temple": temple, "redshroom": redshroom,
         "brownshroom": brownshroom, "sensor": sensor, "shrieker": shrieker, "citywall": citywall,
         "oak2": oak_wide, "oak3": oak_tall, "birch2": birch_tall, "cherry2": cherry_tall, "cherry3": cherry_lean,
         "spruce2": lambda: spruce_v(14, 38, [(3, 2), (8, 3), (13, 4), (18, 5), (23, 6), (28, 7)]),
         "spruce3": lambda: spruce_v(12, 22, [(3, 2), (7, 4), (11, 5), (15, 6)]),
         "crimson": lambda: huge_fungus(True, 30, 36, 14, 4, 0, 1, 4), "crimson2": lambda: huge_fungus(True, 24, 30, 11, 3, 2, 2, 3),
         "crimson3": lambda: huge_fungus(True, 26, 44, 13, 3, -2, 3, 5), "warped": lambda: huge_fungus(False, 30, 36, 14, 4, 0, 4, 4),
         "warped2": lambda: huge_fungus(False, 24, 30, 11, 3, -2, 5, 3), "warped3": lambda: huge_fungus(False, 26, 44, 13, 3, 2, 6, 5),
         "kelp2": lambda: kelp_v(22, 1.3), "kelp3": lambda: kelp_v(40, 2.6), "coral2": coral_fan, "seagrass2": seagrass_tall,
         "cactus2": cactus_one, "cactus3": cactus_plain, "redshroom2": redshroom_tall, "brownshroom2": brownshroom_wide,
         "azalea2": azalea_tree, "dripstone": dripstone}


def atlas():
    sprs = {k: f() for k, f in PROPS.items()}
    W = sum(s.w for s in sprs.values()) + len(sprs)
    H = max(s.h for s in sprs.values())
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    boxes, x = {}, 0
    for k, s in sprs.items():
        img.paste(s.im, (x, 0))
        boxes[k] = [x, 0, s.w, s.h]
        x += s.w + 1
    return img, boxes


if __name__ == "__main__":
    a, b = atlas()
    bg = Image.new("RGBA", a.size, (24, 26, 32, 255))
    bg.alpha_composite(a)
    bg.resize((a.width * 6, a.height * 6), Image.NEAREST).save(
        r"C:/Users/sad79/AppData/Local/hermes/cache/scratch/scene_props.png")
    print(b)
