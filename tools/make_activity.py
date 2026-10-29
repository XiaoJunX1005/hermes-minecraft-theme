"""Activity icons (16x16, 8 frames) + the minecraft-activity desktop plugin.

Each icon stands for something Hermes is actually doing (thinking, reading a
file, running a command, searching the web, ...). The plugin listens to the
desktop app's gateway events and picks the matching icon.

    python tools/make_activity.py
      -> desktop-plugins/minecraft-activity/plugin.js   (atlas embedded)
      -> docs/activity.gif                              (README preview)
"""

from __future__ import annotations

import base64
import io
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from make_icons import F, S, G, bee, furnace, tnt

ROOT = Path(__file__).resolve().parent.parent

# order = atlas rows; label = text shown next to the icon
KINDS = [
    ("think", "思考中"), ("write", "撰寫回覆"), ("shell", "執行指令"), ("web", "搜尋網路"),
    ("browse", "瀏覽網頁"), ("read", "讀取檔案"), ("search", "搜尋檔案"), ("edit", "修改檔案"),
    ("vision", "查看畫面"), ("memory", "整理記憶"), ("agent", "派出幫手"), ("wait", "等你回應"),
    ("error", "出錯了"), ("done", "完成"), ("tool", "使用工具"),
]
EN = {"think": "thinking", "write": "writing", "shell": "terminal", "web": "web search", "browse": "browse",
      "read": "read file", "search": "search files", "edit": "edit file", "vision": "vision",
      "memory": "memory", "agent": "subagent", "wait": "waiting", "error": "error", "done": "done", "tool": "other tool"}

INK = (40, 30, 30, 255)


def think(f: int) -> Image.Image:
    """Enchanting: an open book floating over a table, purple glyphs rising."""
    g = G()
    dy = [0, -1, -1, 0, 0, 1, 1, 0][f]
    g.rect(1, 12, 14, 3, (46, 30, 44, 255))
    g.rect(1, 12, 14, 1, (178, 44, 56, 255))
    g.rect(3, 6 + dy, 5, 4, (236, 226, 200, 255))
    g.rect(8, 6 + dy, 5, 4, (246, 238, 214, 255))
    g.rect(2, 10 + dy, 12, 1, (110, 62, 34, 255))
    for x in (4, 5, 6):
        g.p(x, 7 + dy, (150, 130, 120, 255))
    for x in (9, 10, 11):
        g.p(x, 8 + dy, (150, 130, 120, 255))
    for k, x in enumerate((2, 8, 13)):
        y = 5 - (f + k * 3) % 6
        if y >= 0:
            g.p(x, y, (200, 130, 255, 255))
            g.p(x, y + 1, (140, 80, 220, 200))
    g.outline()
    return g.im


def write(f: int) -> Image.Image:
    """A big feather quill writing a line on a scroll."""
    g = G()
    g.rect(0, 10, 12, 5, (242, 234, 210, 255))
    g.rect(0, 10, 12, 1, (200, 180, 140, 255))
    n = min(9, 2 + f)
    g.rect(1, 12, n, 1, (90, 70, 60, 255))
    tx = 1 + n
    g.p(tx, 12, INK)
    # feather: shaft from the nib up and to the right, vanes on both sides
    for k in range(1, 10):
        x, y = tx + k // 2 + (1 if k > 1 else 0), 12 - k
        if not (0 <= x < 16 and y >= 0):
            break
        g.p(x, y, (120, 110, 100, 255))
        if k > 2:
            g.p(x - 1, y, (250, 250, 250, 255))
            g.p(x + 1, y, (214, 224, 240, 255))
            if k > 4:
                g.p(x - 2, y, (236, 240, 250, 255))
    g.outline()
    return g.im


def web(f: int) -> Image.Image:
    """Compass with a spinning needle."""
    g = G()
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - 7.5, y - 7.5)
            if d < 7.6:
                g.p(x, y, (70, 70, 78, 255) if d > 6.6 else (130, 130, 140, 255) if d > 5.6 else (222, 218, 206, 255))
    a = f * math.pi / 4 + 0.3
    for t in range(-5, 6):
        x, y = round(7.5 + math.cos(a) * t * 0.9 - 0.5), round(7.5 + math.sin(a) * t * 0.9 - 0.5)
        g.p(x, y, (214, 40, 40, 255) if t > 0 else (60, 60, 72, 255))
    g.rect(7, 7, 2, 2, (40, 40, 48, 255))
    return g.im


PATH = [(3, 11), (4, 10), (5, 10), (6, 9), (8, 8), (9, 7), (10, 6), (11, 5)]


def browse(f: int) -> Image.Image:
    """Treasure map: a dotted route drawn step by step to a blinking X."""
    g = G()
    g.rect(1, 2, 14, 12, (226, 206, 160, 255))
    for x in range(1, 15):
        g.p(x, 2, (150, 120, 80, 255))
        g.p(x, 13, (150, 120, 80, 255))
    g.rect(2, 3, 4, 3, (118, 170, 92, 255))
    g.rect(10, 9, 4, 3, (118, 170, 92, 255))
    g.rect(7, 10, 3, 2, (90, 150, 210, 255))
    for (x, y) in PATH[: f + 1]:
        g.p(x, y, (140, 70, 40, 255))
    if f % 2:
        for d in (-1, 0, 1):
            g.p(12 + d, 4 + d, (214, 40, 40, 255))
            g.p(12 + d, 4 - d, (214, 40, 40, 255))
    g.outline()
    return g.im


def read(f: int) -> Image.Image:
    """Open book with a page flipping right to left."""
    g = G()
    g.rect(1, 5, 7, 8, (236, 226, 200, 255))
    g.rect(8, 5, 7, 8, (244, 236, 214, 255))
    g.rect(1, 13, 14, 1, (110, 62, 34, 255))
    for y in (7, 9, 11):
        g.rect(2, y, 5, 1, (160, 144, 130, 255))
        g.rect(9, y, 5, 1, (160, 144, 130, 255))
    w = abs(7 - 2 * f) if f < 4 else 2 * (f - 4) + 1
    x0 = 8 if f < 4 else 8 - w
    g.rect(x0, 4, max(1, w), 8, (255, 252, 236, 255))
    g.rect(7, 4, 2, 9, (120, 74, 44, 255))
    g.outline()
    return g.im


def search(f: int) -> Image.Image:
    """Torch with a pulsing ring of light."""
    g = G()
    r = 4 + f % 4
    for k in range(8):
        a = k * math.pi / 4
        g.p(round(7.5 + math.cos(a) * r), round(6 + math.sin(a) * r), (255, 226, 130, 200 - (f % 4) * 40))
    g.rect(7, 8, 2, 7, (124, 86, 52, 255))
    flame = [(255, 210, 80, 255), (255, 150, 40, 255), (255, 240, 170, 255)]
    g.rect(7, 5, 2, 3, flame[f % 3])
    g.p(7 + f % 2, 4, flame[(f + 1) % 3])
    g.outline()
    return g.im


def edit(f: int) -> Image.Image:
    """Anvil struck by a hammer, sparks on impact."""
    g = G()
    g.rect(4, 13, 8, 2, (56, 56, 62, 255))
    g.rect(6, 10, 4, 3, (72, 72, 80, 255))
    g.rect(2, 7, 12, 3, (92, 92, 100, 255))
    g.rect(2, 7, 12, 1, (140, 140, 150, 255))
    g.rect(0, 8, 2, 1, (92, 92, 100, 255))
    hy = [0, 1, 2, 3, 4, 2, 1, 0][f]
    g.rect(9, hy, 4, 2, (160, 160, 172, 255))
    g.rect(12, hy + 2, 1, 3, (124, 86, 52, 255))
    if f in (4, 5):
        rng = random.Random(f)
        for _ in range(6):
            g.p(rng.randrange(6, 15), rng.randrange(2, 7), rng.choice([(255, 220, 90, 255), (255, 150, 40, 255)]))
    g.outline()
    return g.im


def vision(f: int) -> Image.Image:
    """Spyglass with a glint travelling across the lens."""
    g = G()
    for k in range(11):
        x, y = 2 + k, 13 - k
        col = (190, 140, 56, 255) if k % 4 else (120, 84, 40, 255)
        g.p(x, y, col)
        g.p(x + 1, y, col)
        g.p(x, y - 1, (220, 176, 90, 255) if k % 4 else (120, 84, 40, 255))
    g.rect(12, 1, 3, 3, (170, 220, 255, 255))
    gx, gy = [(12, 1), (13, 1), (14, 1), (14, 2), (14, 3), (13, 3), (12, 3), (12, 2)][f]
    g.p(gx, gy, (255, 255, 255, 255))
    g.outline()
    return g.im


def memory(f: int) -> Image.Image:
    """Chest whose lid opens onto a golden glow."""
    g = G()
    lift = [0, 0, 1, 2, 3, 3, 2, 1][f]
    g.rect(2, 8, 12, 7, (150, 100, 50, 255))
    g.rect(2, 11, 12, 1, (110, 72, 36, 255))
    g.rect(2, 5 - lift, 12, 3, (170, 116, 60, 255))
    g.rect(2, 5 - lift, 12, 1, (196, 140, 76, 255))
    if lift:
        g.rect(3, 8 - lift, 10, lift, (255, 214, 96, 255))
    g.rect(7, 7, 2, 3, (210, 210, 220, 255))
    g.outline()
    return g.im


def wait(f: int) -> Image.Image:
    """Hourglass: sand runs down, flips at the end."""
    g = G()
    wood = (150, 100, 50, 255)
    g.rect(3, 1, 10, 2, wood)
    g.rect(3, 13, 10, 2, wood)
    glass = (210, 236, 255, 150)
    for y in range(3, 13):
        half = abs(y - 7.5)
        w = max(1, int(half * 0.8) + 1)
        g.rect(8 - w, y, 2 * w, 1, glass)
    sand = (232, 196, 96, 255)
    top = 4 - f // 2           # rows of sand left in the top bulb
    for k in range(max(0, top)):
        y = 6 - k
        w = max(1, int(abs(y - 7.5) * 0.8) + 1)
        g.rect(8 - w, y, 2 * w, 1, sand)
    for k in range(min(4, f // 2 + 1)):
        y = 12 - k
        w = max(1, int(abs(y - 7.5) * 0.8) + 1)
        g.rect(8 - w, y, 2 * w, 1, sand)
    if f % 2 == 0 and top > 0:
        g.p(7, 8, sand)
        g.p(7, 9 + (f // 2) % 2, sand)
    g.outline()
    return g.im


def tool(f: int) -> Image.Image:
    """Pickaxe swinging at a stone block, chips flying on impact."""
    g = G()
    stone = [(150, 150, 156, 255), (126, 126, 132, 255), (104, 104, 110, 255)]
    rng = random.Random(7)
    for y in range(9, 16):
        for x in range(7, 16):
            g.p(x, y, rng.choice(stone))
    swing = [0, 1, 2, 3, 3, 2, 1, 0][f]
    hx, hy = 3 + swing, 2 + swing
    for k in range(7):  # handle from grip (bottom-left) to head
        g.p(hx - 3 + k // 2, hy + 6 - k, (124, 86, 52, 255))
    head = (120, 230, 230, 255)
    for k in range(-3, 4):
        g.p(hx + k, hy - 1 + abs(k) // 2, head)
    g.p(hx - 3, hy + 1, (60, 150, 150, 255))
    g.p(hx + 3, hy + 1, (60, 150, 150, 255))
    if f in (3, 4):
        for (x, y) in ((8, 7), (10, 6), (12, 7), (9, 5)):
            g.p(x, y, (180, 180, 186, 255))
    g.outline()
    return g.im


def done(f: int) -> Image.Image:
    """Pulsing experience orb."""
    g = G()
    rr = [3, 4, 5, 5.5, 5, 4, 3.5, 3][f]
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - 7.5, y - 7.5)
            if d < rr:
                g.p(x, y, (240, 255, 150, 255) if d < rr * 0.4 else (160, 236, 64, 255) if d < rr * 0.75 else (90, 170, 30, 255))
    a = f * math.pi / 4
    for k in range(2):
        g.p(round(7.5 + 7 * math.cos(a + k * math.pi) - 0.5), round(7.5 + 7 * math.sin(a + k * math.pi) - 0.5),
            (230, 255, 160, 255))
    return g.im


DRAW = {"think": think, "write": write, "shell": furnace, "web": web, "browse": browse, "read": read,
        "search": search, "edit": edit, "vision": vision, "memory": memory, "agent": bee, "wait": wait,
        "error": lambda f: tnt(f % 4), "done": done, "tool": tool}



# ---- workbench stations (16x16, 8 frames) ------------------------------------------
BENCH_ROWS = ["lectern-idle", "lectern-think", "lectern-read", "lectern-write",
              "forge-idle", "forge-edit", "forge-shell", "forge-tool",
              "map-idle", "map-web", "map-browse", "map-search", "map-vision",
              "store-idle", "store-memory", "store-wait", "store-agent",
              "fx-done", "fx-error"]
WOOD, WOOD_D, WOOD_L = (150, 100, 50, 255), (110, 72, 36, 255), (186, 132, 72, 255)
PAGE, PAGE2, LINE = (236, 226, 200, 255), (246, 238, 214, 255), (150, 130, 120, 255)


def lectern(mode: str, f: int) -> Image.Image:
    """Lectern with an open book: think (glyphs), read (page flip), write (quill)."""
    g = G()
    g.rect(3, 14, 10, 2, WOOD_D)
    g.rect(7, 9, 2, 5, WOOD)
    g.rect(2, 7, 12, 2, WOOD_L)
    g.rect(2, 8, 12, 1, WOOD)
    g.rect(3, 4, 5, 3, PAGE)
    g.rect(8, 4, 5, 3, PAGE2)
    g.rect(7, 4, 1, 3, (120, 74, 44, 255))
    for x in (4, 5, 6, 9, 10, 11):
        g.p(x, 5, LINE)
    if mode == "think":
        for k, x in enumerate((3, 8, 12)):
            y = 3 - (f + k * 3) % 5
            if y >= 0:
                g.p(x, y, (200, 130, 255, 255))
    elif mode == "read":
        x = 12 - f
        if 3 <= x <= 12:
            g.rect(x, 3, 1, 4, (255, 252, 236, 255))
    elif mode == "write":
        n = f % 4 + 1
        g.rect(8, 6, n, 1, (60, 40, 30, 255))
        for k in range(1, 5):
            g.p(8 + n + k // 2, 6 - k, (250, 250, 250, 255))
    g.outline()
    return g.im


def forge(mode: str, f: int) -> Image.Image:
    """Anvil (left) + furnace (right): edit hammers, shell fires the furnace, tool does a bit of both."""
    g = G()
    g.rect(1, 13, 6, 2, (56, 56, 62, 255))
    g.rect(2, 11, 4, 2, (72, 72, 80, 255))
    g.rect(0, 9, 8, 2, (100, 100, 108, 255))
    g.rect(0, 9, 8, 1, (150, 150, 160, 255))
    g.rect(9, 6, 7, 9, (120, 120, 126, 255))
    g.rect(9, 6, 7, 1, (150, 150, 156, 255))
    g.rect(10, 10, 5, 4, (30, 22, 18, 255))
    flame = [(255, 210, 80, 255), (255, 150, 40, 255), (240, 90, 30, 255)]
    if mode == "shell":
        rng = random.Random(f)
        for x in range(10, 15):
            for k in range(rng.randint(1, 4)):
                g.p(x, 13 - k, flame[min(2, k)])
        if mode == "shell":
            g.p(12 + f % 2, 4 - f % 3, (170, 170, 176, 220))
    else:
        g.p(12, 13, (160, 60, 30, 255))
    if mode == "edit":
        hy = [0, 1, 2, 3, 3, 2, 1, 0][f]
        g.rect(1, 2 + hy, 4, 2, (172, 172, 184, 255))
        g.rect(4, 4 + hy, 1, 3, WOOD)
        if f in (3, 4):
            rng = random.Random(f + 9)
            for _ in range(5):
                g.p(rng.randrange(0, 9), rng.randrange(4, 9), rng.choice(flame[:2]))
    elif mode == "tool":
        sw = [0, 1, 2, 2, 1, 0, 0, 0][f]
        for k in range(5):
            g.p(1 + k + sw, 7 - k, WOOD)
        for k in range(-2, 3):
            g.p(5 + sw + k, 1 + abs(k) // 2 + sw // 2, (120, 230, 230, 255))
        if f in (2, 3):
            for x, y in ((2, 7), (6, 6), (4, 5)):
                g.p(x, y, (200, 200, 206, 255))
    g.outline()
    return g.im


def maptable(mode: str, f: int) -> Image.Image:
    """Cartography table with a map and a compass (web spins it, browse draws a route,
    search sweeps a light over the map, vision swaps the compass for a spyglass)."""
    g = G()
    g.rect(1, 9, 14, 2, WOOD_L)
    g.rect(1, 10, 14, 1, WOOD)
    g.rect(2, 11, 2, 5, WOOD_D)
    g.rect(12, 11, 2, 5, WOOD_D)
    g.rect(1, 6, 9, 3, (226, 206, 160, 255))
    if mode == "idle":                                   # rolled up when nobody is using it
        g.rect(1, 6, 9, 3, (0, 0, 0, 0))
        g.rect(2, 7, 7, 2, (226, 206, 160, 255))
        g.rect(2, 7, 7, 1, (200, 180, 136, 255))
    g.p(2, 7, (118, 170, 92, 255))
    g.p(3, 7, (118, 170, 92, 255))
    g.p(7, 6, (90, 150, 210, 255))
    if mode == "vision":
        for k in range(5):
            g.p(10 + k, 8 - k, (190, 140, 56, 255))
        g.rect(14, 3, 2, 2, (170, 220, 255, 255))
        if f % 4 < 2:
            g.p(15, 3, (255, 255, 255, 255))
    else:
        for y in range(4, 9):
            for x in range(10, 15):
                d = math.hypot(x - 12, y - 6)
                if d < 2.6:
                    g.p(x, y, (90, 90, 98, 255) if d > 1.7 else (222, 218, 206, 255))
        a = f * math.pi / 4 if mode == "web" else -math.pi / 2
        for t in (1, 2):
            g.p(round(12 + math.cos(a) * t * 0.9), round(6 + math.sin(a) * t * 0.9), (214, 40, 40, 255))
        g.p(round(12 - math.cos(a)), round(6 - math.sin(a)), (60, 60, 72, 255))
        g.p(12, 6, (40, 40, 48, 255))
        if mode == "web" and f % 2 == 0:
            g.p(12, 2, (150, 220, 255, 255))
            g.p(9, 4, (150, 220, 255, 200))
    if mode == "browse":
        for k in range(min(f + 1, 7)):
            g.p(2 + k, 8 - (k // 3), (140, 70, 40, 255))
        if f % 2:
            g.p(8, 6, (214, 40, 40, 255))
    elif mode == "search":
        g.rect(0, 2, 1, 4, WOOD)                       # torch beside the map
        g.p(0, 1, (255, 200, 70, 255))
        g.p(0, 0, (255, 240, 170, 255) if f % 2 else (255, 150, 40, 255))
        x = 1 + f
        if x <= 9:
            g.rect(x, 6, 2 if x < 9 else 1, 3, (255, 236, 150, 255))
    g.outline()
    return g.im


def storage(mode: str, f: int) -> Image.Image:
    """Chest (left) + bell (right): memory opens the chest, wait rings the bell, agent sends a bee."""
    g = G()
    lift = [0, 0, 1, 2, 3, 3, 2, 1][f] if mode == "memory" else 0
    g.rect(0, 10, 8, 6, (150, 100, 50, 255))
    g.rect(0, 12, 8, 1, WOOD_D)
    if lift:
        g.rect(1, 10 - lift, 6, lift, (255, 214, 96, 255))
    g.rect(0, 8 - lift, 8, 2, (170, 116, 60, 255))
    g.rect(0, 8 - lift, 8, 1, (196, 140, 76, 255))
    g.rect(3, 9 - lift, 2, 2, (210, 210, 220, 255))
    g.rect(9, 1, 7, 1, WOOD_D)
    g.rect(15, 1, 1, 15, WOOD_D)
    dx = [0, 1, 0, -1][f % 4] if mode == "wait" else 0
    g.p(12, 2, (90, 90, 90, 255))
    g.rect(11 + dx, 3, 3, 3, (236, 190, 60, 255))
    g.rect(10 + dx, 6, 5, 1, (200, 150, 40, 255))
    g.p(11 + dx, 3, (255, 230, 140, 255))
    if mode == "wait" and f % 2 == 0:
        g.p(9, 4, (255, 240, 180, 255))
        g.p(9, 6, (255, 240, 180, 255))
    if mode == "agent":
        # chunky bee (5x4) flying a loop in the open area above the chest
        bx, by = [(1, 1), (3, 0), (5, 1), (5, 3), (3, 4), (1, 3), (0, 2), (0, 1)][f]
        for x in range(5):
            for y in range(1, 4):
                g.p(bx + x, by + y, (54, 36, 22, 255) if x in (1, 3) else (246, 200, 50, 255))
        g.p(bx + 4, by + 1, (20, 20, 24, 255))
        wing = (230, 244, 255, 255)
        if f % 2 == 0:
            g.rect(bx + 1, by - 1, 3, 2, wing)
        else:
            g.rect(bx + 1, by, 3, 1, wing)
    g.outline()
    return g.im


def fx(mode: str, f: int) -> Image.Image:
    """Overlay drawn over the current station: done = XP orbs rising, error = smoke."""
    g = G()
    if mode == "done":
        for k, x in enumerate((3, 8, 12)):
            y = 13 - (f * 2 + k * 5) % 13
            g.rect(x, y, 2, 2, (160, 236, 64, 255))
            g.p(x, y, (240, 255, 150, 255))
    else:
        for k, x in enumerate((4, 9)):
            y = 10 - (f + k * 3) % 8
            g.rect(x, y, 3, 2, (120, 120, 126, 210))
            g.p(x + 1, y - 1, (150, 150, 156, 190))
        if f % 4 == 0:
            g.p(7, 12, (230, 70, 50, 255))
    return g.im


BENCH_DRAW = {"lectern": lectern, "forge": forge, "map": maptable, "store": storage, "fx": fx}


def bench_atlas() -> Image.Image:
    img = Image.new("RGBA", (S * F, S * len(BENCH_ROWS)), (0, 0, 0, 0))
    for r, name in enumerate(BENCH_ROWS):
        station, mode = name.split("-", 1)
        for c in range(F):
            img.paste(BENCH_DRAW[station](mode, c), (c * S, r * S))
    return img


def atlas() -> Image.Image:
    img = Image.new("RGBA", (S * F, S * len(KINDS)), (0, 0, 0, 0))
    for r, (kind, _) in enumerate(KINDS):
        for c in range(F):
            img.paste(DRAW[kind](c), (c * S, r * S))
    return img


def data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.quantize(colors=128, method=Image.Quantize.FASTOCTREE).save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def preview(a: Image.Image) -> None:
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\msjh.ttc", 14)
        label = dict(KINDS)
    except OSError:
        font, label = ImageFont.load_default(), EN
    cols, z, cw, ch = 5, 4, 130, 96
    rows = math.ceil(len(KINDS) / cols)
    frames = []
    for f in range(F):
        c = Image.new("RGBA", (cols * cw, rows * ch), (24, 26, 32, 255))
        d = ImageDraw.Draw(c)
        for i, (kind, _) in enumerate(KINDS):
            x0, y0 = (i % cols) * cw, (i // cols) * ch
            cell = a.crop((f * S, i * S, (f + 1) * S, (i + 1) * S)).resize((S * z, S * z), Image.NEAREST)
            c.alpha_composite(cell, (x0 + (cw - S * z) // 2, y0 + 6))
            text = label[kind]
            tw = d.textlength(text, font=font)
            d.text((x0 + (cw - tw) / 2, y0 + S * z + 10), text, fill=(220, 220, 220, 255), font=font)
        frames.append(c.convert("RGB"))
    strip = Image.new("RGB", (frames[0].width, frames[0].height * 2))
    strip.paste(frames[0], (0, 0))
    strip.paste(frames[4], (0, frames[0].height))
    pal = strip.quantize(colors=200, method=Image.Quantize.MEDIANCUT)
    q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in frames]
    q[0].save(ROOT / "docs" / "activity.gif", save_all=True, append_images=q[1:], duration=130, loop=0)


def main() -> None:
    a = atlas()
    preview(a)
    src = (ROOT / "src" / "activity-plugin.js").read_text(encoding="utf-8")
    kinds = json.dumps([{"kind": k, "label": label} for k, label in KINDS], ensure_ascii=False)
    b = bench_atlas()
    big = Image.new("RGBA", b.size, (24, 26, 32, 255))
    big.alpha_composite(b)
    big.resize((b.width * 5, b.height * 5), Image.NEAREST).save(ROOT / "docs" / "_bench-atlas.png")
    out = (src.replace("__ATLAS__", data_uri(a)).replace("__KINDS__", kinds)
              .replace("__BENCH__", data_uri(b)).replace("__BENCH_ROWS__", json.dumps(BENCH_ROWS))
              .replace("__GENERATED__", "GENERATED by tools/make_activity.py from src/activity-plugin.js — edit that file."))
    dest = ROOT / "desktop-plugins" / "minecraft-activity" / "plugin.js"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out, encoding="utf-8", newline="\n")
    print("wrote", dest, f"({dest.stat().st_size // 1024} KiB)", "+ docs/activity.gif")


if __name__ == "__main__":
    main()
