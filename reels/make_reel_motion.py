#!/usr/bin/env python3
"""Filmic animated reel for SytronANPR: one continuous moving road scene, silent, 1080x1920, 30 fps.
Usage: make_reel_motion.py <company.yaml> <logo.png> <out.mp4> [t0 t1 step -> write PNG previews instead]
All feature text is copied from company.yaml. Plates are placeholders (XX 00 XX 0000)."""
import math, subprocess, sys
import yaml
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR = 1080, 1920, 30, 38.0
BG, BG2 = (20, 21, 26), (15, 16, 21)
BOX, BOXL = (42, 47, 55), (52, 58, 67)
AMBER, GREEN, BLUE, RED = (236, 198, 53), (98, 160, 127), (66, 125, 196), (189, 66, 64)
WHITE, GREY = (245, 246, 238), (154, 160, 170)
B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
M = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
_f = {}
def F(p, s):
    if (p, s) not in _f: _f[(p, s)] = ImageFont.truetype(p, s)
    return _f[(p, s)]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def ramp(t, a, b): return ease((t - a) / (b - a))
def lerp(a, b, k): return a + (b - a) * k
def mix(c1, c2, k): return tuple(int(lerp(a, b, k)) for a, b in zip(c1, c2))
def inout(t, a, b, c, d): return ramp(t, a, b) * (1 - ramp(t, c, d))

# ---------------------------------------------------------------- vehicles
FEED_W, FEED_H = 960, 720
LANE = {0: 560, 1: 680}
DIM = {"car": (300, 140), "bus": (520, 170), "truck": (480, 190), "bike": (170, 125), "auto": (190, 150)}
PLATE = {"car": (256, -68, 300, -46), "bus": (468, -64, 512, -42), "truck": (434, -70, 478, -48),
         "bike": (124, -64, 160, -48), "auto": (146, -62, 186, -44)}
LABEL = {"car": "CAR", "bus": "BUS", "truck": "TRUCK", "bike": "TWO-WHEELER", "auto": "AUTO"}

def lin(t0, sp, w): return [(t0, -w), (t0 + (FEED_W + w) / sp, FEED_W)]
VEH = {}
def add(name, kind, color, lane, keys): VEH[name] = dict(kind=kind, color=color, lane=lane, keys=keys)
add("hook", "car", (138, 147, 160), 0, lin(0.0, 200, 300))
add("A", "car", BLUE, 1, lin(3.2, 190, 300))
add("B", "car", (150, 150, 158), 1, lin(8.6, 190, 300))
add("C", "car", RED, 0, lin(9.5, 150, 300))
add("D", "auto", (138, 143, 78), 1, lin(10.8, 150, 190))
add("E", "bike", (176, 120, 70), 0, lin(11.8, 150, 170))
add("bus", "bus", (96, 120, 150), 0, lin(13.2, 150, 520))
add("truck", "truck", (120, 126, 110), 1, lin(12.33, 150, 480))
add("F", "car", (176, 170, 150), 1, lin(15.93, 150, 300))
add("G", "car", (96, 140, 130), 1, [(22.6, -300), (24.8, 250), (25.9, 250), (27.6, 1000)])
add("H", "car", (150, 110, 120), 1, [(25.8, -300), (27.6, 260), (40, 260)])

def vx(v, t):
    k = v["keys"]
    if t <= k[0][0]: return k[0][1]
    for (t1, x1), (t2, x2) in zip(k, k[1:]):
        if t <= t2: return lerp(x1, x2, (t - t1) / (t2 - t1))
    return k[-1][1]
def vbox(n, t):
    v = VEH[n]; x = vx(v, t); w, h = DIM[v["kind"]]; yb = LANE[v["lane"]]
    return (x, yb - h, x + w, yb)
def vplate(n, t):
    v = VEH[n]; x = vx(v, t); yb = LANE[v["lane"]]; a, b, c, d = PLATE[v["kind"]]
    return (x + a, yb + b, x + c, yb + d)
def inview(r, m=10): return r[0] > m and r[2] < FEED_W - m

def wheel(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(14, 15, 18))
    d.ellipse([cx - r * .45, cy - r * .45, cx + r * .45, cy + r * .45], fill=(120, 126, 136))

def draw_vehicle(d, v, t):
    x = vx(v, t); k = v["kind"]; yb = LANE[v["lane"]]; c = v["color"]; dk = mix(c, (0, 0, 0), .35)
    win = (150, 190, 215)
    if x < -DIM[k][0] - 5 or x > FEED_W + 5: return
    if k == "car":
        d.rounded_rectangle([x, yb - 95, x + 300, yb - 35], 16, fill=c)
        d.polygon([(x + 62, yb - 95), (x + 105, yb - 142), (x + 215, yb - 142), (x + 255, yb - 95)], fill=dk)
        d.polygon([(x + 78, yb - 98), (x + 112, yb - 134), (x + 160, yb - 134), (x + 160, yb - 98)], fill=win)
        d.polygon([(x + 168, yb - 98), (x + 168, yb - 134), (x + 210, yb - 134), (x + 240, yb - 98)], fill=win)
        wheel(d, x + 70, yb - 30, 30); wheel(d, x + 232, yb - 30, 30)
        d.rectangle([x + 290, yb - 86, x + 300, yb - 72], fill=(240, 220, 150))
    elif k == "bus":
        d.rounded_rectangle([x, yb - 170, x + 520, yb - 40], 18, fill=c)
        for i in range(7): d.rounded_rectangle([x + 24 + i * 62, yb - 150, x + 72 + i * 62, yb - 100], 6, fill=win)
        d.rounded_rectangle([x + 462, yb - 150, x + 506, yb - 66], 6, fill=dk)
        d.rectangle([x, yb - 70, x + 520, yb - 62], fill=dk)
        wheel(d, x + 100, yb - 36, 34); wheel(d, x + 400, yb - 36, 34)
    elif k == "truck":
        d.rectangle([x, yb - 190, x + 330, yb - 55], fill=dk)
        d.rectangle([x + 8, yb - 182, x + 322, yb - 63], fill=mix(c, (255, 255, 255), .06))
        d.rounded_rectangle([x + 340, yb - 140, x + 480, yb - 55], 14, fill=c)
        d.polygon([(x + 400, yb - 132), (x + 454, yb - 132), (x + 470, yb - 96), (x + 400, yb - 96)], fill=win)
        wheel(d, x + 70, yb - 34, 34); wheel(d, x + 250, yb - 34, 34); wheel(d, x + 410, yb - 34, 34)
    elif k == "bike":
        wheel(d, x + 34, yb - 34, 34); wheel(d, x + 138, yb - 34, 34)
        d.line([(x + 34, yb - 34), (x + 82, yb - 70), (x + 138, yb - 34)], fill=c, width=9)
        d.line([(x + 82, yb - 70), (x + 120, yb - 90), (x + 134, yb - 78)], fill=c, width=8)
        d.rounded_rectangle([x + 54, yb - 84, x + 112, yb - 66], 8, fill=dk)
        d.polygon([(x + 62, yb - 84), (x + 74, yb - 118), (x + 100, yb - 114), (x + 96, yb - 80)], fill=(110, 116, 126))
        d.ellipse([x + 78, yb - 138, x + 104, yb - 112], fill=(205, 170, 140))
    elif k == "auto":
        d.rounded_rectangle([x + 4, yb - 110, x + 190, yb - 48], 14, fill=c)
        d.polygon([(x + 4, yb - 110), (x + 20, yb - 152), (x + 140, yb - 152), (x + 140, yb - 110)], fill=dk)
        d.rectangle([x + 28, yb - 118, x + 134, yb - 100], fill=win)
        wheel(d, x + 40, yb - 30, 28); wheel(d, x + 156, yb - 30, 28)
    p = vplate(None, t) if False else None
    a, b, cc, dd = PLATE[k]
    d.rounded_rectangle([x + a, yb + b, x + cc, yb + dd], 3, fill=(230, 228, 214))

# ---------------------------------------------------------------- feed drawing
BUILD = [(0, 270, 150), (170, 220, 120), (310, 300, 170), (500, 250, 110), (640, 200, 160), (820, 280, 140), (990, 240, 130)]
def feed_base(t, night):
    img = Image.new("RGBA", (FEED_W, FEED_H), (27, 30, 37, 255)); d = ImageDraw.Draw(img)
    off = (t * 12) % 1130
    for rep in (-1, 0):
        for bx, bh, bw in BUILD:
            x0 = bx - off + rep * 1130 + 1130
            x0 = x0 % 1130 - 170
            d.rectangle([x0, 430 - bh, x0 + bw, 430], fill=(34, 38, 46))
            for wy in range(430 - bh + 22, 410, 36):
                for wx in range(int(x0) + 14, int(x0 + bw) - 14, 30):
                    d.rectangle([wx, wy, wx + 12, wy + 16], fill=(42, 47, 57))
    d.rectangle([0, 430, FEED_W, FEED_H], fill=(42, 47, 55))
    d.rectangle([0, 430, FEED_W, 442], fill=(60, 66, 76))
    dash = (t * 260) % 120
    for lx in range(-120, FEED_W + 120, 120):
        d.rectangle([lx + dash, 620 - 3, lx + dash + 60, 620 + 3], fill=(82, 88, 98))
    return img

def overlay(img, rgba_fn):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); rgba_fn(ImageDraw.Draw(layer))
    return Image.alpha_composite(img, layer)

def corners(d, r, col, wd=4, ln=26):
    x1, y1, x2, y2 = r
    for (x, y, sx, sy) in ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)):
        d.line([(x, y), (x + sx * ln, y)], fill=col, width=wd); d.line([(x, y), (x, y + sy * ln)], fill=col, width=wd)

def chip(d, xy, text, col, fnt=None, fill=(24, 26, 32, 235), pad=14, anchor="mm"):
    fnt = fnt or F(M, 26); tw = d.textlength(text, font=fnt); x, y = xy
    r = [x - tw / 2 - pad, y - 21, x + tw / 2 + pad, y + 21]
    d.rounded_rectangle(r, 10, fill=fill, outline=col, width=3)
    d.text((x, y), text, font=fnt, fill=WHITE, anchor="mm")

def read_box(img, n, t, t_lock, text="XX 00 XX 0000", col=AMBER, result=None):
    """Detection box around the plate of vehicle n, scan line, typed readout. Returns image."""
    p = vplate(n, t); bx = vbox(n, t)
    k = ramp(t, t_lock, t_lock + 0.35)
    if k <= 0 or not inview(bx, -60): return img
    pr = (p[0] - 10 - 24 * (1 - k), p[1] - 10 - 14 * (1 - k), p[2] + 10 + 24 * (1 - k), p[3] + 10 + 14 * (1 - k))
    n_ch = int(clamp((t - t_lock - 0.35) / 1.0) * len(text) + 0.001)
    done = (t - t_lock) > 1.45
    def f(d):
        corners(d, pr, col, 4, 12)
        d.rectangle(pr, outline=col + (150,), width=2)
        sy = lerp(bx[1], bx[3], (t * 1.3) % 1.0) if not done else None
        if sy is not None: d.line([(bx[0] + 8, sy), (bx[2] - 8, sy)], fill=AMBER + (170,), width=3)
        cx = clamp((p[0] + p[2]) / 2, 150, FEED_W - 150); cy = bx[1] - 52
        d.line([((p[0] + p[2]) / 2, pr[1]), ((p[0] + p[2]) / 2, cy + 22)], fill=col + (200,), width=2)
        chip(d, (cx, cy), (text[:n_ch] + ("_" if not done and int(t * 4) % 2 == 0 else "")).ljust(2), col if not done else GREEN,
             F(M, 28))
        if done: d.text((cx + d.textlength(text, font=F(M, 28)) / 2 + 34, cy), "✓", font=F(B, 30), fill=GREEN, anchor="mm")
    return overlay(img, f)

def mini_plate(d, x, y, double=False, s=1.0):
    w, h = (210, 62) if not double else (130, 96)
    d.rounded_rectangle([x, y, x + w * s, y + h * s], 8, fill=(232, 230, 216), outline=(120, 120, 110), width=2)
    if not double: d.text((x + w * s / 2, y + h * s / 2), "XX 00 XX 0000", font=F(M, int(24 * s)), fill=(30, 30, 34), anchor="mm")
    else:
        d.text((x + w * s / 2, y + 26 * s), "XX 00", font=F(M, int(26 * s)), fill=(30, 30, 34), anchor="mm")
        d.text((x + w * s / 2, y + 66 * s), "XX 0000", font=F(M, int(26 * s)), fill=(30, 30, 34), anchor="mm")

# ---------------------------------------------------------------- feed scenes
def render_feed(t, facts_unused=None):
    night = ramp(t, 7.6, 8.5) * (1 - ramp(t, 11.6, 12.4))
    img = feed_base(t, night)
    d = ImageDraw.Draw(img)
    # barrier post behind vehicles (scene 6)
    bar_k = inout(t, 24.2, 24.8, 29.2, 29.8)
    names = sorted(VEH, key=lambda n: VEH[n]["lane"])
    for n in names:
        if VEH[n]["lane"] == 0: draw_vehicle(d, VEH[n], t)
    for n in names:
        if VEH[n]["lane"] == 1: draw_vehicle(d, VEH[n], t)
    if night > 0:
        def nf(dd):
            dd.rectangle([0, 0, FEED_W, FEED_H], fill=(5, 7, 12, int(165 * night)))
            for n in ("B",):
                bx = vbox(n, t)
                if bx[2] > 0 and bx[0] < FEED_W:
                    fl = 0.5 + 0.5 * math.sin(t * 7)
                    hx, hy = bx[2] - 2, bx[3] - 78
                    dd.polygon([(hx, hy), (hx + 360, hy - 70 - 20 * fl), (hx + 360, hy + 90 + 20 * fl)],
                               fill=(236, 210, 140, int(night * (46 + 40 * fl))))
        img = overlay(img, nf)
        d = ImageDraw.Draw(img)
        rain = Image.new("RGBA", img.size, (0, 0, 0, 0)); rd = ImageDraw.Draw(rain)
        for i in range(70):
            rx = (i * 137 + t * 150) % (FEED_W + 100) - 50; ry = (i * 251 + t * 900) % FEED_H
            rd.line([(rx, ry), (rx - 8, ry + 26)], fill=(190, 200, 215, int(110 * night)), width=2)
        img = Image.alpha_composite(img, rain)
    # barrier (scene 6)
    if bar_k > 0:
        up = ramp(t, 25.4, 25.95) * (1 - ramp(t, 26.95, 27.45))
        def bf(dd):
            a = int(255 * bar_k)
            yb = LANE[1]
            dd.rounded_rectangle([700, yb - 150, 760, yb], 8, fill=BOXL + (a,), outline=GREY + (a,), width=2)
            dd.rectangle([716, yb - 140, 744, yb - 112], fill=(60, 66, 76, a))
            piv = (722, yb - 100)
            ang = math.radians(90 * up)
            L = 150
            ex, ey = piv[0] - L * math.cos(ang), piv[1] - L * math.sin(ang)
            nseg = 6
            for i in range(nseg):
                s0, s1 = i / nseg, (i + 1) / nseg
                p0 = (piv[0] + (ex - piv[0]) * s0, piv[1] + (ey - piv[1]) * s0)
                p1 = (piv[0] + (ex - piv[0]) * s1, piv[1] + (ey - piv[1]) * s1)
                dd.line([p0, p1], fill=((AMBER if i % 2 == 0 else (40, 42, 48)) + (a,)), width=14)
            ok = 1 - 0 if up > .5 else 0
            col = GREEN if (up > .1 and t < 27.5) else (RED if t > 28.0 else GREY)
            dd.ellipse([722 - 8, yb - 132 - 8, 722 + 8, yb - 132 + 8], fill=col + (a,))
        img = overlay(img, bf)
    # ----- scene overlays
    if 4.3 < t < 8.6:
        img = read_box(img, "A", t, 4.6)
        k = ramp(t, 5.4, 5.9)
        def f(dd):
            a = int(255 * k)
            dd.rounded_rectangle([560, 24, 940, 190], 14, fill=(24, 26, 32, int(225 * k)), outline=GREY + (a,), width=2)
            dd.text((580, 40), "PLATE FORMATS", font=F(M, 20), fill=AMBER + (a,))
            mini_plate(dd, 580, 78, False, 0.82); mini_plate(dd, 770, 70, True, 0.9)
            if k > .9:
                dd.text((900, 60), "✓", font=F(B, 26), fill=GREEN + (a,))
        if k > 0: img = overlay(img, f)
    if 8.9 < t < 12.4:
        img = read_box(img, "B", t, 9.6, col=AMBER)
        k = ramp(t, 8.4, 8.9) * (1 - ramp(t, 11.8, 12.3))
        def f(dd):
            for i, (lab, x) in enumerate((("NIGHT", 20), ("RAIN", 160), ("GLARE", 280))):
                chip(dd, (x + 52, 52), lab, AMBER, F(M, 22), fill=(24, 26, 32, int(220 * k)))
        if k > 0: img = overlay(img, f)
    if 12.6 < t < 16.4:
        shown = 0
        for i, (n, tl) in enumerate((("C", 12.8), ("D", 13.4), ("E", 14.0))):
            img = read_box(img, n, t, tl, col=AMBER if t < tl + 1.5 else GREEN, text="XX 00 XX 0000" if n != "E" else "XX 00 XX 0000")
            if inview(vbox(n, t), -40) and t > tl: shown += 1
        k = ramp(t, 12.7, 13.2) * (1 - ramp(t, 15.9, 16.3))
        def f(dd):
            dd.rounded_rectangle([700, 24, 940, 100], 14, fill=(24, 26, 32, int(225 * k)), outline=AMBER + (int(255 * k),), width=2)
            dd.text((720, 38), "PLATES IN VIEW", font=F(M, 18), fill=GREY + (int(255 * k),))
            dd.text((720, 60), str(shown), font=F(B, 34), fill=WHITE + (int(255 * k),))
        if k > 0: img = overlay(img, f)
    if 16.2 < t < 20.4:
        k = ramp(t, 16.3, 16.9) * (1 - ramp(t, 19.9, 20.4))
        def f(dd):
            for n in ("C", "D", "E", "bus", "truck"):
                b = vbox(n, t)
                if b[0] > 5 and b[2] < FEED_W - 5:
                    a = int(255 * k)
                    dd.rounded_rectangle([b[0] - 6, b[1] - 8, b[2] + 6, b[3] + 4], 12, outline=AMBER + (a,), width=3)
                    chip(dd, ((b[0] + b[2]) / 2, b[1] - 34), LABEL[VEH[n]["kind"]], AMBER, F(M, 24), fill=(24, 26, 32, int(235 * k)))
        img = overlay(img, f)
    if 20.0 < t < 24.2:
        img = read_box(img, "F", t, 20.0)
        p = vplate("F", t)
        e = ramp(t, 21.7, 22.6)
        def f(dd):
            k = ramp(t, 21.4, 21.9) * (1 - ramp(t, 23.8, 24.2)); a = int(255 * k)
            dd.rounded_rectangle([590, 24, 940, 200], 14, fill=(24, 26, 32, int(230 * k)), outline=GREY + (a,), width=2)
            dd.text((612, 40), "EMAIL ALERT", font=F(M, 20), fill=AMBER + (a,))
            mini_plate(dd, 612, 80, False, 0.9)
            ex = 612 + 205; ey = 98
            dd.rounded_rectangle([ex + 30, ey - 6, ex + 108, ey + 44], 6, fill=(220, 222, 214, a), outline=GREY + (a,), width=2)
            dd.line([(ex + 30, ey - 6), (ex + 69, ey + 22), (ex + 108, ey - 6)], fill=(120, 126, 136, a), width=3)
            if t > 22.7: dd.text((920, 140), "✓", font=F(B, 34), fill=GREEN + (int(255 * ramp(t, 22.7, 23.0)),), anchor="mm")
            dd.text((612, 160), "with the plate image", font=F(R, 20), fill=GREY + (a,))
        img = overlay(img, f)
    if 24.8 < t < 29.9:
        img = read_box(img, "G", t, 24.9, col=AMBER if t < 26.4 else GREEN, text="XX 00 XX 0000")
        img = read_box(img, "H", t, 27.7, col=AMBER, text="XX 00 XX 0000")
        def f(dd):
            if 25.5 < t < 28.6:
                k = ramp(t, 25.5, 25.9) * (1 - ramp(t, 28.0, 28.5)); a = int(255 * k)
                chip(dd, (330, 84), "WHITELISTED ✓", GREEN, F(M, 26), fill=(24, 26, 32, int(235 * k)), pad=18)
            if t > 28.3:
                k = ramp(t, 28.3, 28.8); a = int(255 * k)
                b = vbox("H", t)
                chip(dd, (clamp((b[0] + b[2]) / 2, 150, FEED_W - 150), b[1] - 112), "NOT LISTED  ✕", RED, F(M, 26),
                     fill=(24, 26, 32, int(235 * k)), pad=18)
        img = overlay(img, f)
    # ----- reports (scene 7): dim feed and rise three documents
    if t > 28.8:
        dim = ramp(t, 28.9, 29.5) * (1 - ramp(t, 32.5, 33.0))
        def f(dd):
            dd.rectangle([0, 0, FEED_W, FEED_H], fill=(15, 16, 21, int(215 * dim)))
            for i, (lab, t0) in enumerate((("PDF", 29.4), ("WORD", 29.75), ("CSV", 30.1))):
                k = ramp(t, t0, t0 + 0.55) * dim
                if k <= 0: continue
                x = 55 + i * 285; y = 150 + (1 - k) * 70; a = int(255 * k)
                dd.rounded_rectangle([x, y, x + 250, y + 360], 16, fill=BOXL + (a,), outline=AMBER + (a,) if i == 0 and t > 31 else GREY + (a,), width=2)
                dd.text((x + 125, y + 40), lab, font=F(M, 34), fill=AMBER + (a,), anchor="mm")
                dd.line([(x + 30, y + 74), (x + 220, y + 74)], fill=GREY + (a,), width=2)
                gk = ramp(t, t0 + 0.4, t0 + 1.4)
                for j, hgt in enumerate((60, 110, 80, 150, 120)):
                    hh = hgt * gk * (0.9 + 0.1 * math.sin(i + j))
                    dd.rectangle([x + 32 + j * 36, y + 330 - hh, x + 58 + j * 36, y + 330], fill=(98, 160, 127, a) if j == 3 else (GREY + (a,)))
                for r_ in range(3):
                    dd.rectangle([x + 30, y + 92 + r_ * 18, x + 220 - r_ * 36, y + 100 + r_ * 18], fill=(80, 86, 96, a))
            if t > 30.9:
                kk = ramp(t, 30.9, 31.4) * dim
                chip(dd, (480, 600), "Daily or weekly, by email", AMBER, F(M, 26), fill=(24, 26, 32, int(235 * kk)), pad=22)
        img = overlay(img, f)
    # HUD
    d = ImageDraw.Draw(img)
    rec = int(t * 2) % 2 == 0
    if t < 33:
        d.ellipse([890, 692 - 8, 906, 692 + 8], fill=(RED if rec else (80, 40, 40)) + (255,))
        d.text((24, 696), "CAM 01", font=F(M, 20), fill=GREY, anchor="lm")
        d.text((860, 696), "REC", font=F(M, 20), fill=GREY, anchor="rm")
    return img

# ---------------------------------------------------------------- full frame
STEPS = [("Real-time reading", 0), ("Day, night, rain, glare", 1), ("Many plates, one view", 2),
         ("Every vehicle type", 3), ("Instant alerts", 4), ("Gate control", 5), ("Reports", 6)]
STEP_T = [4, 8, 12, 16, 20, 24, 29, 33]
FEED_XY = (60, 540)
MASK = Image.new("L", (FEED_W, FEED_H), 0); ImageDraw.Draw(MASK).rounded_rectangle([0, 0, FEED_W - 1, FEED_H - 1], 28, fill=255)

def text_c(d, y, s, fnt, col, a=1.0, dy=0, x=W / 2):
    d.text((x, y + dy), s, font=fnt, fill=mix(BG, col, clamp(a)), anchor="mm")
def wrap(s, n):
    out, cur = [], ""
    for w in s.split():
        if len(cur) + len(w) + 1 > n and cur: out.append(cur); cur = w
        else: cur = (cur + " " + w).strip()
    return out + [cur]

def make_logo(path):
    lg = Image.open(path).convert("RGB"); lg = lg.resize((int(lg.width * 0.40), int(lg.height * 0.40)), Image.LANCZOS)
    from PIL import ImageFilter
    m = Image.new("L", lg.size, 0); ImageDraw.Draw(m).ellipse([14, 10, lg.width - 14, lg.height - 10], fill=255)
    return lg, m.filter(ImageFilter.GaussianBlur(14))

def frame(t, facts, logo):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    out = ramp(t, 33.0, 33.6)
    top = 1 - out
    # logo
    lg, lm = logo
    img.paste(lg, ((W - lg.width) // 2, int(40 - out * 0)), lm)
    prod = facts["products"][0]
    feats = prod["features"]
    # heading
    if t < 4.6:
        a1 = ramp(t, 0.3, 0.9); a2 = ramp(t, 0.9, 1.5); ao = 1 - ramp(t, 3.8, 4.4)
        text_c(d, 330, "Reads every Indian plate,", F(B, 56), WHITE, a1 * ao, (1 - a1) * 26)
        text_c(d, 408, "day and night.", F(B, 56), AMBER, a2 * ao, (1 - a2) * 26)
    if t >= 4.0 and t < 33.6:
        a = ramp(t, 4.0, 4.6) * top
        text_c(d, 330, prod["name"], F(B, 60), AMBER, a)
        text_c(d, 392, "Read every plate, track every vehicle, control every gate", F(R, 26), GREY, a)
    # feed
    fk = 1 - out
    if fk > 0.01:
        fd = render_feed(t).convert("RGB")
        if fk < 1: fd = Image.blend(Image.new("RGB", fd.size, BG), fd, fk)
        img.paste(fd, FEED_XY, MASK)
        d.rounded_rectangle([FEED_XY[0], FEED_XY[1], FEED_XY[0] + FEED_W, FEED_XY[1] + FEED_H], 28,
                            outline=mix(BG, (96, 102, 112), fk), width=2)
    # caption block
    for i in range(7):
        a, b = STEP_T[i], STEP_T[i + 1]
        if a - 0.0 <= t < b + 0.6:
            ain = ramp(t, a + 0.15, a + 0.7); aout = 1 - ramp(t, b - 0.3, b + 0.3) if i < 6 else 1 - ramp(t, 32.7, 33.4)
            al = ain * aout
            if al <= 0: continue
            dy = (1 - ain) * 34
            text_c(d, 1330, f"STEP {i + 1} OF 7", F(M, 28), AMBER, al, dy)
            text_c(d, 1388, STEPS[i][0], F(B, 56), WHITE, al, dy)
            for j, line in enumerate(wrap(feats[STEPS[i][1]], 30)):
                text_c(d, 1462 + j * 50, line, F(R, 40), GREY, al, dy)
    # step trail
    if t > 4.0 and t < 33.6:
        ta = ramp(t, 4.0, 4.6) * top
        cur = sum(1 for s in STEP_T[:7] if t >= s) - 1
        for i in range(7):
            cx = 180 + i * 120; cy = 1650
            act = i == cur; dn = i < cur
            col = AMBER if act else (GREEN if dn else (96, 102, 112))
            r = 26 if act else 22
            if i < 6:
                d.line([(cx + r + 6, cy), (cx + 120 - r - 6, cy)], fill=mix(BG, (GREEN if dn else (60, 66, 76)), ta), width=3)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=mix(BG, BOX if not act else (60, 52, 20), ta), outline=mix(BG, col, ta), width=3)
            d.text((cx, cy), str(i + 1), font=F(M, 24), fill=mix(BG, col if not (not act and not dn) else GREY, ta), anchor="mm")
    # outro
    if t > 33.0:
        o = ramp(t, 33.0, 33.6)
        lg2 = lg.resize((int(lg.width * 1.5), int(lg.height * 1.5)), Image.LANCZOS)
        m2 = lm.resize(lg2.size)
        img.paste(Image.blend(Image.new("RGB", lg2.size, BG), lg2, o), ((W - lg2.width) // 2, 420), m2)
        text_c(d, 990, facts["name"], F(B, 50), GREY, o)
        d.rounded_rectangle([470, 1040, 610, 1046], 3, fill=mix(BG, AMBER, o))
        for i, (line, col) in enumerate((("Read every plate,", WHITE), ("track every vehicle,", WHITE), ("control every gate.", AMBER))):
            ak = ramp(t, 34.0 + i * 0.7, 34.5 + i * 0.7)
            text_c(d, 1130 + i * 84, line, F(B, 62), col, ak, (1 - ak) * 28)
        ab = ramp(t, 36.2, 36.8)
        if ab > 0:
            site = facts.get("website", "www.sytronsoft.com")
            wd = d.textlength(site, font=F(B, 40)) + 100
            r = [W / 2 - wd / 2, 1480, W / 2 + wd / 2, 1566]
            d.rounded_rectangle(r, 43, fill=mix(BG, AMBER, ab))
            d.text((W / 2, 1523), site, font=F(B, 40), fill=mix(BG, (24, 20, 8), ab), anchor="mm")
            text_c(d, 1610, "Learn more", F(R, 30), GREY, ab)
    # fade in from black at the very start
    if t < 0.4:
        img = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), img, ramp(t, 0, 0.4))
    return img

def main():
    yml, logo_p, outp = sys.argv[1:4]
    facts = yaml.safe_load(open(yml)); logo = make_logo(logo_p)
    if len(sys.argv) > 4:
        for tt in sys.argv[4:]:
            frame(float(tt), facts, logo).save(f"prev_{float(tt):05.2f}.png")
        return
    n = int(DUR * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-t", str(DUR), "-i", "anullsrc=r=44100:cl=stereo",
           "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
           "-movflags", "+faststart", outp]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        pr.stdin.write(frame(i / FPS, facts, logo).tobytes())
    pr.stdin.close(); pr.wait()
    print(f"reel: {outp} ({DUR:.0f} s, {n} frames)")

if __name__ == "__main__":
    main()
