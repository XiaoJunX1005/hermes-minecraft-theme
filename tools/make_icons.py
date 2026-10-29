"""16x16 animated "thinking" icons — blocks and mobs — packed into one atlas.

Rows = icons, columns = frames (8). Blocks are drawn as crisp isometric item
cubes (like an inventory slot); mobs are flat side/front sprites with outlines.

    from make_icons import ICONS, atlas
    img = atlas()          # 128 x (16 * len(ICONS)) RGBA
"""

from __future__ import annotations

import random

from PIL import Image

from pixels import DIRT, GRASS_TOP, grass_block_front, noise_texture

S, F = 16, 8
ICONS = ["grass", "diamond", "furnace", "tnt", "mining", "slime", "bee", "chicken"]
LABELS = {"grass": "草方塊", "diamond": "鑽石礦", "furnace": "熔爐", "tnt": "TNT", "mining": "挖掘中",
          "slime": "史萊姆", "bee": "蜜蜂", "chicken": "雞"}
STONE = ["#8f8f8f", "#828282", "#767676", "#6a6a6a"]
COBBLE = ["#9a9a9a", "#7e7e7e", "#6a6a6a", "#555555", "#474747"]


def rgba(c, a: int = 255) -> tuple:
    if isinstance(c, tuple):
        return c if len(c) == 4 else c + (a,)
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)


class G:
    def __init__(self) -> None:
        self.im = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    def p(self, x: int, y: int, c) -> None:
        if 0 <= x < S and 0 <= y < S:
            self.im.putpixel((x, y), rgba(c))

    def rect(self, x0: int, y0: int, w: int, h: int, c) -> None:
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                self.p(x, y, c)

    def outline(self, col=(18, 18, 22, 255)) -> None:
        src = self.im.copy()
        for y in range(S):
            for x in range(S):
                if src.getpixel((x, y))[3]:
                    continue
                if any(0 <= x + dx < S and 0 <= y + dy < S and src.getpixel((x + dx, y + dy))[3] > 120
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    self.im.putpixel((x, y), col)


# --- isometric item cube ---------------------------------------------------------------

def iso(top, left, right, scroll: int = 0, shade=(1.08, 0.78, 0.55)) -> G:
    """Inventory-style cube. Textures are 16x16 grids of hex/rgba; `scroll` slides the
    textures sideways so a uniform block reads as turning."""
    g = G()
    for py in range(S):
        for px in range(S):
            x, y = px + 0.5, py + 0.5
            u = ((x - 8) / 8 + y / 4) / 2
            v = (y / 4 - (x - 8) / 8) / 2
            hit = None
            if 0 <= u < 1 and 0 <= v < 1:
                hit = (top, int(u * 16), int(v * 16), shade[0])
            else:
                a = x / 8
                b = (y - 4 - 4 * a) / 8
                if 0 <= a < 1 and 0 <= b < 1:
                    hit = (left, int(a * 16), int(b * 16), shade[1])
                else:
                    a = (x - 8) / 8
                    b = (y - 8 + 4 * a) / 8
                    if 0 <= a < 1 and 0 <= b < 1:
                        hit = (right, int(a * 16), int(b * 16), shade[2])
            if not hit:
                continue
            tex, tu, tv, k = hit
            if tex is not top:
                tu = (tu + scroll) % 16
            else:
                tu, tv = (tu + scroll) % 16, (tv + scroll) % 16
            r, gg, b, a = rgba(tex[tv][tu])
            g.p(px, py, (min(255, int(r * k)), min(255, int(gg * k)), min(255, int(b * k)), a))
    return g


def _specks(tex, spots, cols):
    tex = [row[:] for row in tex]
    for (x, y) in spots:
        for (dx, dy), c in zip(((0, 0), (1, 0), (0, 1), (1, 1)), cols):
            if 0 <= x + dx < 16 and 0 <= y + dy < 16:
                tex[y + dy][x + dx] = c
    return tex


def grass(f: int) -> Image.Image:
    top = noise_texture(16, 16, GRASS_TOP, 21)
    side = grass_block_front(16, 16, 3)
    return iso(top, side, side, scroll=f * 2).im


def diamond(f: int) -> Image.Image:
    stone = noise_texture(16, 16, STONE, 5, [1, 3, 3, 2])
    tex = [row[:] for row in stone]
    for (x0, y0) in ((2, 2), (10, 3), (4, 10), (11, 11)):
        for dy in range(3):
            for dx in range(3):
                tex[y0 + dy][x0 + dx] = ["#bdfbf3", "#7ef2f0", "#2cb8c4"][min(2, dx + dy - 1 if dx + dy else 0)]
    g = iso(tex, tex, tex)
    sparks = [(4, 3), (11, 6), (3, 9), (12, 11), (8, 2), (6, 12), (10, 9), (2, 6)]
    sx, sy = sparks[f]
    g.p(sx, sy, (255, 255, 255, 255))
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        g.p(sx + dx, sy + dy, (200, 255, 250, 200))
    return g.im


def furnace(f: int) -> Image.Image:
    stone = noise_texture(16, 16, STONE, 9, [1, 3, 3, 2])
    front = [row[:] for row in stone]
    flame = [["#ffd25a", "#ff9a2a", "#e85a1a"], ["#ffe680", "#ffb030", "#f06a1c"], ["#ffc240", "#ff8420", "#d84a14"]]
    for y in range(1, 4):
        for x in range(2, 14):
            front[y][x] = "#3a3a3a"
    for y in range(6, 15):
        for x in range(2, 14):
            front[y][x] = "#141414" if x in (2, 13) or y == 6 else "#2a1608"
    rng = random.Random(f)
    for x in range(3, 13):
        h = rng.randint(3, 7)
        for k in range(h):
            front[14 - k][x] = flame[f % 3][min(2, k * 3 // max(1, h))]
    return iso(noise_texture(16, 16, STONE, 11, [1, 3, 3, 2]), front, stone).im


def _tnt_side():
    t = [["#d33b2a" if (x // 2) % 2 else "#b82c1f" for x in range(16)] for _ in range(16)]
    for y in range(5, 11):
        for x in range(16):
            t[y][x] = "#f0ece4"
    glyphs = ["XXX.X.X.XXX", ".X..XXX..X.", ".X..XXX..X.", ".X..X.X..X."]
    for y, row in enumerate(glyphs):
        for x, c in enumerate(row):
            if c == "X":
                t[6 + y][2 + x] = "#1c1c1c"
    return t


def tnt(f: int) -> Image.Image:
    top = [["#c9352a" if (x + y) % 3 else "#a82a1f" for x in range(16)] for y in range(16)]
    for y in range(6, 10):
        for x in range(6, 10):
            top[y][x] = "#6a6a6a"
    side = _tnt_side()
    g = iso(top, side, side)
    if f >= 4 and f % 2 == 0:  # white priming flash
        for y in range(S):
            for x in range(S):
                r, gg, b, a = g.im.getpixel((x, y))
                if a:
                    g.im.putpixel((x, y), (min(255, r + 110), min(255, gg + 110), min(255, b + 110), a))
    spark = [(8, 1), (9, 0), (7, 0), (8, 0)][f % 4]
    g.p(*spark, (255, 230, 120, 255))
    return g.im


CRACKS = [(7, 6), (8, 7), (8, 8), (7, 9), (9, 9), (6, 10), (10, 8), (11, 7), (5, 7), (4, 8), (9, 11),
          (10, 12), (6, 12), (5, 13), (11, 10), (12, 11), (3, 6), (12, 5), (8, 4), (7, 13)]


def mining(f: int) -> Image.Image:
    cob = noise_texture(16, 16, ["#b4b4b4", "#a6a6a6", "#9a9a9a", "#8c8c8c"], 13, [1, 3, 3, 1])
    if f >= 6:  # block broke: show debris only
        g = G()
        rng = random.Random(f)
        for _ in range(6):
            x, y = rng.randrange(2, 12), rng.randrange(5 + (f - 6) * 3, 13)
            g.rect(x, y, 2, 2, rng.choice(COBBLE[:3]))
            g.p(x, y + 1, COBBLE[4])
        g.outline()
        return g.im
    g = iso(cob, cob, cob)
    for (x, y) in CRACKS[: (f + 1) * 3]:
        g.p(x, y, (16, 16, 18, 255))
        g.p(x + 1, y + 1, (60, 60, 64, 255))
    return g.im


def slime(f: int) -> Image.Image:
    g = G()
    hs = [11, 10, 9, 10, 12, 12, 11, 11][f]
    lift = [0, 0, 0, 0, -1, -3, -2, -1][f]
    w = 22 - hs
    x0, y0 = (S - w) // 2, 15 - hs + lift
    g.rect(x0, y0, w, hs, (120, 196, 96, 205))
    g.rect(x0 + 2, y0 + 2, w - 4, hs - 4, (84, 156, 66, 255))
    g.rect(x0, y0, w, 1, (168, 228, 140, 230))
    ey = y0 + max(2, hs // 3)
    for ex in (x0 + 2, x0 + w - 4):
        g.rect(ex, ey, 2, 2, (24, 40, 20, 255))
    g.p(x0 + w // 2, ey + 3, (24, 40, 20, 255))
    g.outline((32, 70, 26, 255))
    return g.im


def bee(f: int) -> Image.Image:
    g = G()
    dy = [0, -1, -1, 0, 0, -1, -1, 0][f]
    for y in range(6, 13):
        for x in range(3, 13):
            c = (238, 196, 62, 255)
            if x in (6, 7, 10):
                c = (54, 36, 22, 255)
            g.p(x, y + dy, c)
    g.p(2, 9 + dy, (90, 90, 96, 255))
    g.p(1, 9 + dy, (90, 90, 96, 255))
    g.rect(11, 7 + dy, 2, 2, (20, 20, 24, 255))
    g.p(13, 5 + dy, (54, 36, 22, 255))
    g.p(14, 4 + dy, (54, 36, 22, 255))
    wing = (214, 236, 255, 210)
    if f % 2 == 0:
        g.rect(6, 2 + dy, 3, 4, wing)
        g.rect(9, 3 + dy, 2, 3, wing)
    else:
        g.rect(5, 5 + dy, 6, 1, wing)
    g.outline()
    return g.im


def chicken(f: int) -> Image.Image:
    g = G()
    peck = f in (2, 3, 6)
    hx, hy = (1, 2) if peck else (0, 0)
    for x in (6, 9):
        g.rect(x, 12, 1, 3, (230, 180, 60, 255))
    g.rect(3, 6, 9, 6, (240, 240, 236, 255))
    g.rect(5, 8, 4, 3, (200, 200, 196, 255))
    g.rect(2, 5, 2, 3, (236, 236, 232, 255))
    g.rect(9 + hx, 2 + hy, 4, 5, (246, 246, 242, 255))
    g.p(11 + hx, 3 + hy, (20, 20, 24, 255))
    g.rect(13 + hx, 4 + hy, 1, 2, (238, 156, 40, 255))
    g.rect(12 + hx, 6 + hy, 1, 2, (214, 40, 40, 255))
    g.rect(10 + hx, 1 + hy, 2, 1, (214, 40, 40, 255))
    g.outline()
    return g.im


DRAW = {"grass": grass, "diamond": diamond, "furnace": furnace, "tnt": tnt, "mining": mining,
        "slime": slime, "bee": bee, "chicken": chicken}


def atlas() -> Image.Image:
    img = Image.new("RGBA", (S * F, S * len(ICONS)), (0, 0, 0, 0))
    for r, name in enumerate(ICONS):
        for c in range(F):
            img.paste(DRAW[name](c), (c * S, r * S))
    return img


if __name__ == "__main__":
    a = atlas()
    big = Image.new("RGBA", a.size, (24, 26, 32, 255))
    big.alpha_composite(a)
    big.resize((a.width * 6, a.height * 6), Image.NEAREST).save("../docs/thinking-atlas.png")
    print("ok", a.size)
