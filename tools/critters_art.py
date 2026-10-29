"""Roaming mob sprites: side view (facing right) + front view for the turn animation.
16x16 per frame, 8 frames per row. All art original, drawn procedurally."""

from __future__ import annotations

import math

from PIL import Image

from make_icons import F, S, G

BOB = [0, -1, -1, 0, 0, 1, 1, 0]


def c_allay(f: int) -> Image.Image:
    g = G()
    dy = BOB[f]
    wing = (200, 236, 255, 210)
    if f % 2 == 0:
        g.rect(2, 3 + dy, 4, 5, wing)
    else:
        g.rect(1, 7 + dy, 5, 2, wing)
    g.rect(6, 3 + dy, 6, 5, (120, 196, 240, 255))
    g.rect(6, 3 + dy, 6, 1, (170, 224, 255, 255))
    g.p(9, 5 + dy, (20, 40, 80, 255))
    g.p(11, 5 + dy, (20, 40, 80, 255))
    g.rect(7, 8 + dy, 4, 4, (90, 170, 230, 255))
    g.rect(8, 12 + dy, 2, 2, (70, 150, 215, 255))
    g.p(12, 9 + dy, (90, 170, 230, 255))
    g.outline()
    return g.im


def c_phantom(f: int) -> Image.Image:
    g = G()
    flap = [0, 1, 2, 1, 0, -1, -2, -1][f]
    body, dark = (70, 90, 140, 255), (50, 64, 108, 255)
    tip = 6 - (3 + flap)
    g.rect(6, tip, 5, 7 - tip, dark)
    g.rect(3, 7, 10, 3, body)
    g.rect(3, 9, 10, 1, (110, 130, 180, 255))
    g.rect(13, 7, 2, 2, body)
    g.p(14, 7, (130, 255, 140, 255))
    g.rect(1, 8, 2, 1, body)
    g.p(0, 9, body)
    g.outline()
    return g.im




DARK = (54, 36, 22, 255)
WING = (225, 240, 255, 215)


def tri(g, pts, col):
    (x0, y0), (x1, y1), (x2, y2) = pts
    for y in range(min(y0, y1, y2), max(y0, y1, y2) + 1):
        for x in range(min(x0, x1, x2), max(x0, x1, x2) + 1):
            d1 = (x - x1) * (y0 - y1) - (x0 - x1) * (y - y1)
            d2 = (x - x2) * (y1 - y2) - (x1 - x2) * (y - y2)
            d3 = (x - x0) * (y2 - y0) - (x2 - x0) * (y - y0)
            if not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0)):
                g.p(x, y, col)


def bee_side(f, angry=False, pollen=False):
    g = G()
    body = (232, 150, 40, 255) if angry else (246, 200, 50, 255)
    for y in range(6, 12):
        for x in range(3, 13):
            g.p(x, y, DARK if x in (5, 6, 9) else body)
    g.rect(11, 7, 2, 2, (200, 30, 30, 255) if angry else (20, 20, 24, 255))
    g.p(2, 9, (90, 90, 96, 255))
    g.p(12, 5, DARK)
    g.p(13, 4, DARK)
    if pollen:
        for x in (4, 8, 10):
            g.p(x, 11, (255, 236, 130, 255))
    if f % 2 == 0:
        g.rect(5, 2, 3, 4, WING)
        g.rect(8, 3, 2, 3, WING)
    else:
        g.rect(4, 5, 7, 1, WING)
    g.outline()
    return g.im


def bee_front(f, angry=False, pollen=False):
    g = G()
    body = (232, 150, 40, 255) if angry else (246, 200, 50, 255)
    g.rect(4, 5, 8, 7, body)
    g.rect(4, 10, 8, 1, DARK)
    eye = (200, 30, 30, 255) if angry else (20, 20, 24, 255)
    g.rect(5, 7, 2, 2, eye)
    g.rect(9, 7, 2, 2, eye)
    for x, y in ((6, 4), (5, 3), (9, 4), (10, 3)):
        g.p(x, y, DARK)
    if pollen:
        for x in (5, 8, 10):
            g.p(x, 11, (255, 236, 130, 255))
    if f % 2 == 0:
        g.rect(1, 3, 3, 4, WING)
        g.rect(12, 3, 3, 4, WING)
    else:
        g.rect(1, 6, 3, 2, WING)
        g.rect(12, 6, 3, 2, WING)
    g.outline()
    return g.im


PARROTS = {
    "red": ((214, 44, 44, 255), (60, 100, 220, 255), (250, 220, 70, 255)),
    "blue": ((56, 96, 226, 255), (250, 210, 60, 255), (220, 230, 250, 255)),
    "green": ((76, 182, 64, 255), (250, 210, 60, 255), (250, 230, 90, 255)),
    "cyan": ((52, 196, 210, 255), (250, 210, 60, 255), (240, 240, 230, 255)),
    "gray": ((150, 150, 156, 255), (110, 110, 118, 255), (245, 245, 245, 255)),
}


def parrot_side(f, c):
    body, wing, face = PARROTS[c]
    g = G()
    g.rect(2, 10, 3, 3, body)
    g.p(1, 12, body)
    g.rect(4, 6, 6, 6, body)
    g.rect(8, 3, 4, 4, face)
    g.rect(12, 4, 2, 2, (60, 60, 64, 255))
    g.p(12, 6, (60, 60, 64, 255))
    g.p(10, 4, (20, 20, 24, 255))
    wy = [2, 4, 8, 4, 2, 4, 8, 4][f]
    g.rect(4, wy, 5, 3, wing)
    g.rect(6, 12, 1, 2, (90, 90, 90, 255))
    g.rect(8, 12, 1, 2, (90, 90, 90, 255))
    g.outline()
    return g.im


def parrot_front(f, c):
    body, wing, face = PARROTS[c]
    g = G()
    g.rect(6, 6, 4, 7, body)
    g.rect(5, 2, 6, 5, face)
    g.p(6, 4, (20, 20, 24, 255))
    g.p(9, 4, (20, 20, 24, 255))
    g.rect(7, 5, 2, 2, (60, 60, 64, 255))
    wy = [3, 5, 8, 5, 3, 5, 8, 5][f]
    g.rect(1, wy, 5, 2, wing)
    g.rect(10, wy, 5, 2, wing)
    g.outline()
    return g.im


def allay_front(f):
    g = G()
    dy = BOB[f]
    wing = (200, 236, 255, 200)
    if f % 2 == 0:
        g.rect(1, 3 + dy, 4, 5, wing)
        g.rect(11, 3 + dy, 4, 5, wing)
    else:
        g.rect(1, 7 + dy, 4, 2, wing)
        g.rect(11, 7 + dy, 4, 2, wing)
    g.rect(5, 2 + dy, 6, 5, (120, 196, 240, 255))
    g.rect(5, 2 + dy, 6, 1, (170, 224, 255, 255))
    g.p(6, 4 + dy, (20, 40, 80, 255))
    g.p(9, 4 + dy, (20, 40, 80, 255))
    g.rect(6, 7 + dy, 4, 4, (90, 170, 230, 255))
    g.rect(7, 11 + dy, 2, 2, (70, 150, 215, 255))
    g.outline()
    return g.im


def phantom_front(f):
    g = G()
    flap = [0, 1, 2, 1, 0, -1, -2, -1][f]
    body, dark = (70, 90, 140, 255), (50, 64, 108, 255)
    for k in range(7):
        y = 7 - round(flap * k / 6)
        g.rect(k, y, 1, 2, dark)
        g.rect(15 - k, y, 1, 2, dark)
    g.rect(6, 5, 4, 5, body)
    g.p(6, 6, (130, 255, 140, 255))
    g.p(9, 6, (130, 255, 140, 255))
    g.rect(7, 10, 2, 3, dark)
    g.outline()
    return g.im


DRAGON, DRAGON_W, EYE_P = (34, 30, 40, 255), (64, 54, 80, 255), (210, 100, 255, 255)


def dragon_side(f):
    g = G()
    wy = [2, 3, 5, 7, 9, 7, 5, 3][f]
    tri(g, ((4, 8), (7, wy), (10, 8)), DRAGON_W)
    g.rect(3, 8, 8, 3, DRAGON)
    g.rect(0, 10, 3, 1, DRAGON)
    g.p(0, 11, DRAGON)
    g.rect(11, 6, 2, 3, DRAGON)
    g.rect(12, 5, 4, 3, DRAGON)
    g.p(14, 6, EYE_P)
    g.p(13, 4, DRAGON)
    g.rect(5, 11, 1, 2, DRAGON)
    g.rect(9, 11, 1, 2, DRAGON)
    g.outline((120, 80, 150, 255))
    return g.im


def dragon_front(f):
    g = G()
    wy = [2, 3, 5, 7, 9, 7, 5, 3][f]
    tri(g, ((6, 8), (0, wy), (5, 10)), DRAGON_W)
    tri(g, ((9, 8), (15, wy), (10, 10)), DRAGON_W)
    g.rect(6, 6, 4, 6, DRAGON)
    g.rect(6, 2, 4, 4, DRAGON)
    g.p(6, 3, EYE_P)
    g.p(9, 3, EYE_P)
    g.rect(7, 12, 2, 3, DRAGON)
    g.outline((120, 80, 150, 255))
    return g.im


def bat_front(f):
    """Bat seen from the front: each wing is a membrane spread between three finger bones,
    so the trailing edge is notched and never forms one straight horizontal line."""
    g = G()
    body, wing, bone = (110, 80, 58, 255), (78, 56, 42, 255), (124, 92, 66, 255)
    flap = [-40, -20, 5, 30, 5, -20, -40, -40][f]
    for side in (-1, 1):
        sx, sy = (6, 7) if side < 0 else (9, 7)
        tips = []
        for da, ln in ((-28, 7.0), (0, 7.5), (28, 5.5)):
            a = math.radians(flap + da)
            tips.append((round(sx + side * math.cos(a) * ln), round(sy + math.sin(a) * ln)))
        tri(g, ((sx, sy), tips[0], tips[1]), wing)
        tri(g, ((sx, sy), tips[1], tips[2]), wing)
        for tx, ty in tips:
            n = max(abs(tx - sx), abs(ty - sy))
            for k in range(n + 1):
                g.p(round(sx + (tx - sx) * k / n), round(sy + (ty - sy) * k / n), bone)
    g.rect(6, 5, 4, 6, body)
    g.p(6, 4, body)
    g.p(9, 4, body)
    g.p(7, 7, (240, 220, 80, 255))
    g.p(8, 7, (240, 220, 80, 255))
    g.outline()
    return g.im


def ghast_front(f):
    g = G()
    for y in range(0, 11):
        for x in range(2, 14):
            v = 255 if y < 2 else 236 if y < 9 else 214
            g.p(x, y, (v, v, v, 255))
    g.rect(4, 4, 2, 1, (110, 110, 116, 255))
    g.rect(10, 4, 2, 1, (110, 110, 116, 255))
    g.rect(7, 7, 2, 2, (80, 80, 86, 255))
    for k, x in enumerate((3, 5, 7, 9, 11, 13)):
        for r in range(4 + (k % 2)):
            dx = round(math.sin((f / 8) * 2 * math.pi + r * 0.7) * (r / 3))
            g.p(x + dx, 11 + r, (226, 226, 226, 255))
    g.outline((120, 120, 126, 255))
    return g.im


def blaze_front(f):
    g = G()
    rods = []
    for ring, (cy, rx, sign) in enumerate(((4, 6.0, 1), (10, 6.5, -1))):
        for k in range(4):
            ang = sign * (f / 8) * (math.pi / 2) + k * math.pi / 2 + ring * math.pi / 4
            rods.append((math.sin(ang), round(7 + math.cos(ang) * rx), cy))
    rods.sort()

    def rod(x, y, d):
        k = 0.55 if d < 0 else 1.0
        g.rect(x, y, 2, 5, (int(225 * k), int(140 * k), int(30 * k), 255))
        g.rect(x, y, 2, 1, (int(255 * k), int(225 * k), int(120 * k), 255))

    for d, x, y in rods:
        if d < 0:
            rod(x, y, d)
    g.rect(4, 2, 8, 7, (255, 206, 70, 255))
    g.rect(4, 2, 8, 1, (255, 238, 150, 255))
    g.rect(5, 4, 2, 2, (70, 34, 10, 255))
    g.rect(9, 4, 2, 2, (70, 34, 10, 255))
    g.rect(6, 7, 4, 1, (170, 80, 20, 255))
    for d, x, y in rods:
        if d >= 0:
            rod(x, y, d)
    g.outline()
    return g.im


def shulker_front(f):
    """Frame = how far the lid is open (0 closed .. 7 open)."""
    g = G()
    lift = round(f * 3 / 7)
    pur, purd, purl = (170, 110, 185, 255), (130, 80, 150, 255), (205, 160, 215, 255)
    g.rect(2, 9, 12, 6, pur)
    g.rect(2, 9, 12, 1, purl)
    g.rect(2, 14, 12, 1, purd)
    if lift:
        g.rect(4, 9 - lift, 8, lift, (236, 226, 170, 255))
        if lift >= 2:
            g.p(6, 9 - lift, (30, 30, 40, 255))
            g.p(9, 9 - lift, (30, 30, 40, 255))
    g.rect(2, 3 - lift, 12, 6, pur)
    g.rect(2, 3 - lift, 12, 1, purl)
    g.rect(2, 8 - lift, 12, 1, purd)
    g.outline((90, 50, 110, 255))
    return g.im


def fish_side(f, body, belly, fin, L=11, H=5, stripes=()):
    g = G()
    wag = [0, 1, 1, 0, 0, -1, -1, 0][f]
    x0 = 3
    for x in range(L):
        t = x / (L - 1)
        hh = max(2, round(H * (1 - abs(t - 0.6) * 1.1)))
        top = 8 - hh // 2
        for y in range(hh):
            g.p(x0 + x, top + y, belly if y >= hh - max(1, hh // 3) else body)
    for sx in stripes:
        for y in range(4, 13):
            if g.im.getpixel((x0 + sx, y))[3]:
                g.p(x0 + sx, y, (245, 245, 245, 255))
    for k in range(1, 4):
        g.p(x0 - k, 8 - k + wag, fin)
        g.p(x0 - k, 8 + k - 1 + wag, fin)
    g.p(x0 - 1, 8 + wag, fin)
    g.rect(x0 + L // 2 - 1, 8 - H // 2 - 1, 3, 1, fin)
    g.p(x0 + L - 3, 7, (20, 20, 24, 255))
    g.outline()
    return g.im


def axolotl_side(f, body, gill):
    g = G()
    wag = [0, 1, 0, -1, 0, 1, 0, -1][f]
    g.rect(0, 9 + wag, 3, 2, body)
    g.rect(3, 8, 9, 4, body)
    g.rect(11, 7, 4, 4, body)
    g.p(13, 8, (20, 20, 24, 255))
    for x, y in ((11, 6), (12, 5), (14, 6), (15, 5), (10, 7)):
        g.p(x, y, gill)
    up = f % 4 < 2
    g.rect(4, 12, 1, 2 if up else 1, body)
    g.rect(9, 12, 1, 1 if up else 2, body)
    g.outline()
    return g.im


def rabbit_side(f, fur):
    g = G()
    g.rect(4, 8, 8, 5, fur)
    g.rect(10, 5, 5, 5, fur)
    g.rect(11, 1, 1, 4, fur)
    g.rect(13, 1, 1, 4, fur)
    g.p(13, 7, (20, 20, 24, 255))
    g.p(14, 8, (230, 150, 150, 255))
    g.rect(2, 9, 2, 2, (245, 245, 245, 255))
    leg = [0, 1, 1, 0, 0, 1, 1, 0][f]
    g.rect(5, 13, 3, 1 + leg, fur)
    g.rect(10, 13, 2, 2 - leg, fur)
    g.outline()
    return g.im


def camel_side(f):
    g = G()
    tan, dk = (214, 172, 112, 255), (176, 138, 86, 255)
    step = f % 4 < 2
    for i, x in enumerate((4, 6, 10, 12)):
        g.rect(x, 11, 1, 4 if (i % 2 == 0) == step else 3, dk)
    g.rect(3, 7, 10, 4, tan)
    g.rect(5, 5, 2, 2, tan)
    g.rect(9, 5, 2, 2, tan)
    g.rect(12, 4, 2, 4, tan)
    g.rect(13, 2, 3, 2, tan)
    g.p(14, 2, (20, 20, 24, 255))
    g.p(2, 8, dk)
    g.outline()
    return g.im


def mooshroom_side(f, body, spot, mush):
    g = G()
    step = f % 4 < 2
    for i, x in enumerate((4, 6, 10, 12)):
        g.rect(x, 12, 1, 3 if (i % 2 == 0) == step else 2, (60, 50, 50, 255))
    g.rect(3, 7, 10, 5, body)
    for x, y in ((5, 8), (8, 10), (10, 8)):
        g.rect(x, y, 2, 1, spot)
    g.rect(12, 6, 4, 4, body)
    g.rect(14, 8, 2, 2, (230, 200, 190, 255))
    g.p(13, 7, (20, 20, 24, 255))
    for x in (5, 9):
        g.p(x, 6, (230, 225, 210, 255))
        g.rect(x - 1, 5, 3, 1, mush)
    g.outline()
    return g.im


def squid_front(f, glow=False):
    g = G()
    body = (40, 160, 160, 255) if glow else (44, 62, 120, 255)
    g.rect(5, 1, 6, 8, body)
    g.rect(5, 1, 6, 1, (90, 220, 210, 255) if glow else (80, 100, 160, 255))
    g.p(6, 5, (230, 230, 240, 255))
    g.p(9, 5, (230, 230, 240, 255))
    for k, x in enumerate((5, 6, 7, 8, 9, 10)):
        n = 4 + (f + k) % 3
        for r in range(n):
            g.p(x + round(math.sin(f / 8 * 6.28 + k) * r / 4), 9 + r, body)
    if glow and f % 4 < 2:
        for x, y in ((7, 3), (9, 7), (6, 7)):
            g.p(x, y, (190, 255, 240, 255))
    g.outline()
    return g.im


def warden_front(f):
    g = G()
    g.rect(4, 4, 8, 10, (20, 42, 52, 255))
    g.rect(4, 1, 8, 4, (24, 54, 64, 255))
    g.p(3, 0, (60, 200, 210, 255))
    g.p(12, 0, (60, 200, 210, 255))
    glow = (40, 230, 240, 255) if f % 8 < 4 else (24, 150, 160, 255)
    g.rect(6, 7, 4, 3, glow)
    for y in (11, 12):
        g.p(5, y, (40, 90, 100, 255))
        g.p(10, y, (40, 90, 100, 255))
    step = f % 4 < 2
    g.rect(5, 14, 2, 2 if step else 1, (20, 42, 52, 255))
    g.rect(9, 14, 2, 1 if step else 2, (20, 42, 52, 255))
    g.outline((50, 110, 120, 255))
    return g.im


def warden_side(f):
    """Warden walking (facing right): heavy, slow stride, chest glows."""
    g = G()
    body, head, dk = (20, 42, 52, 255), (24, 54, 64, 255), (14, 30, 38, 255)
    step = f % 4 < 2
    g.rect(5, 13, 2, 3 if step else 2, dk)
    g.rect(9, 13, 2, 2 if step else 3, dk)
    g.rect(5, 4, 7, 9, body)
    g.rect(6, 0, 6, 4, head)
    g.p(5, 0, (60, 200, 210, 255))
    g.p(4, 1, (60, 200, 210, 255))
    glow = (40, 230, 240, 255) if f % 8 < 4 else (24, 150, 160, 255)
    g.rect(9, 6, 2, 3, glow)
    arm = 1 if step else -1
    g.rect(7 + arm, 6, 2, 6, dk)
    g.outline((50, 110, 120, 255))
    return g.im


def fish_front(f, body, belly, fin, L=11, H=5, stripes=()):
    """Fish seen head-on: oval body, eyes on the sides, little side fins paddling."""
    g = G()
    for y in range(5, 13):
        for x in range(16):
            if ((x - 7.5) / 3.6) ** 2 + ((y - 8.5) / 3.4) ** 2 <= 1:
                g.p(x, y, belly if y >= 10 else body)
    for sx in stripes[:1]:
        for y in range(5, 13):
            if g.im.getpixel((7, y))[3]:
                g.p(7, y, (245, 245, 245, 255))
                g.p(8, y, (245, 245, 245, 255))
    g.rect(7, 3, 2, 2, fin)
    fy = 9 + [0, 1, 1, 0, 0, -1, -1, 0][f]
    g.rect(1, fy, 3, 1, fin)
    g.rect(12, fy, 3, 1, fin)
    g.p(5, 8, (20, 20, 24, 255))
    g.p(10, 8, (20, 20, 24, 255))
    g.rect(7, 10, 2, 1, (90, 40, 40, 255))
    g.outline()
    return g.im


FISH = {
    "cod": ((176, 150, 110, 255), (214, 196, 160, 255), (140, 110, 80, 255), 11, 5, ()),
    "salmon": ((200, 80, 72, 255), (230, 150, 130, 255), (150, 60, 60, 255), 13, 6, ()),
    "tropical-orange": ((240, 120, 30, 255), (250, 160, 80, 255), (240, 240, 240, 255), 9, 6, (3, 7)),
    "tropical-yellow": ((240, 210, 50, 255), (250, 230, 120, 255), (60, 90, 200, 255), 9, 6, ()),
    "tropical-blue": ((60, 110, 220, 255), (110, 160, 240, 255), (250, 210, 60, 255), 9, 6, (5,)),
}

SPRITES = {
    "bee": (lambda f: bee_side(f), lambda f: bee_front(f)),
    "bee-angry": (lambda f: bee_side(f, angry=True), lambda f: bee_front(f, angry=True)),
    "bee-pollen": (lambda f: bee_side(f, pollen=True), lambda f: bee_front(f, pollen=True)),
    **{f"parrot-{c}": ((lambda f, c=c: parrot_side(f, c)), (lambda f, c=c: parrot_front(f, c))) for c in PARROTS},
    "allay": (c_allay, allay_front),
    "phantom": (c_phantom, phantom_front),
    "dragon": (dragon_side, dragon_front),
    "bat": (None, bat_front),
    "ghast": (None, ghast_front),
    "blaze": (None, blaze_front),
    "shulker": (None, shulker_front),
    **{k: ((lambda f, a=a: fish_side(f, *a)), (lambda f, a=a: fish_front(f, *a))) for k, a in FISH.items()},
    "squid": (None, lambda f: squid_front(f)),
    "glowsquid": (None, lambda f: squid_front(f, True)),
    "axolotl-pink": (lambda f: axolotl_side(f, (240, 160, 190, 255), (220, 90, 140, 255)), None),
    "axolotl-blue": (lambda f: axolotl_side(f, (110, 140, 230, 255), (60, 80, 190, 255)), None),
    "rabbit-brown": (lambda f: rabbit_side(f, (140, 100, 70, 255)), None),
    "rabbit-gold": (lambda f: rabbit_side(f, (220, 190, 110, 255)), None),
    "camel": (camel_side, None),
    "mooshroom-red": (lambda f: mooshroom_side(f, (200, 50, 40, 255), (240, 240, 235, 255), (210, 40, 40, 255)), None),
    "mooshroom-brown": (lambda f: mooshroom_side(f, (150, 100, 60, 255), (220, 200, 170, 255), (150, 110, 70, 255)), None),
    "warden": (warden_side, warden_front),
}
ROWS = [f"{v}:{view}" for v, (side, front) in SPRITES.items()
        for view, fn in (("side", side), ("front", front)) if fn]


def atlas() -> Image.Image:
    img = Image.new("RGBA", (S * F, S * len(ROWS)), (0, 0, 0, 0))
    for r, row in enumerate(ROWS):
        v, view = row.split(":")
        fn = SPRITES[v][0 if view == "side" else 1]
        for c in range(F):
            img.paste(fn(c), (c * S, r * S))
    return img
