#!/usr/bin/env python3
"""Explainer reel v5 for SytronANPR: story-telling flow (no numbered steps), scene length follows the voice-over so there are no pauses, flite voice-over, 1080x1920, 30 fps.
Usage: make_reel_motion_v4.py <company.yaml> <logo.png> <out.mp4> [t ... -> write PNG previews instead]
Needs the flite command (voice slt). Feature wording comes from company.yaml. Plates are placeholders (XX 00 XX 0000)."""
import math, os, subprocess, sys, tempfile, wave
from multiprocessing import Pool
import yaml
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR, K = 1080, 1920, 30, 80.0, 2
BGT, BGB = (234, 244, 238), (212, 232, 220)
INK, GREY, LINE = (24, 46, 40), (92, 116, 106), (184, 208, 196)
CARD, CARD2 = (247, 251, 248), (226, 240, 232)
ACC, ACC2, ACCL = (30, 134, 98), (24, 112, 122), (190, 226, 208)
AMB, RED, BLUE, NAVY = (214, 160, 52), (190, 72, 66), (66, 118, 178), (8, 22, 48)
BGC = (226, 240, 232)
FB = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FR = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"
FM = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
_f = {}
def F(p, s):
    if (p, s, K) not in _f: _f[(p, s, K)] = ImageFont.truetype(p, int(s * K))
    return _f[(p, s, K)]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def ramp(t, a, b): return ease((t - a) / (b - a))
def lerp(a, b, k): return a + (b - a) * k
def mix(c1, c2, k): return tuple(int(lerp(a, b, k)) for a, b in zip(c1, c2))
def fc(c, p): return mix(BGC, c, clamp(p))

ORDER = ["intro", "how", "types", "plates", "multi", "light", "alert", "gate", "reports", "outro"]
NARRATION = {   # every claim comes from company.yaml. "Sigh tron A N P R" is the spoken form of SytronANPR
    "intro": "Sigh tron A N P R. Read every plate, track every vehicle, control every gate.",
    "how": "A camera watches the road. Sigh tron A N P R reads each plate in real time, and everything else follows from there.",
    "types": "It identifies every vehicle in view. Car, bus, truck, two-wheeler and auto.",
    "plates": "It reads single and double-line Indian plates in real time, as each vehicle passes.",
    "multi": "It reads multiple plates in one camera view, all at the same time.",
    "light": "It keeps reading all day and all night. In rain, and in glare.",
    "alert": "When a plate is read, an instant email alert arrives, with the plate image.",
    "gate": "The barrier opens only for whitelisted plates. Every other vehicle stays out.",
    "reports": "Get PDF, Word and CSV reports, daily or weekly, by email.",
    "outro": "Sigh tron A N P R. Read every plate. Control every gate. Visit sytronsoft dot com.",
}
MINLEN, PAD = 5.6, 0.3
SCENES, DUR, VOICE_AT = [], 0.0, {}
TRAIL = []

class Cv:
    """Drawing helper: all coordinates are in 1080x1920 space, drawn at K-times scale."""
    def __init__(s):
        s.im = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0)); s.d = ImageDraw.Draw(s.im)
    def rr(s, b, r, fill=None, out=None, w=2):
        s.d.rounded_rectangle([v * K for v in b], radius=r * K, fill=fill, outline=out, width=int(w * K) if out else 0)
    def el(s, b, fill=None, out=None, w=2):
        s.d.ellipse([v * K for v in b], fill=fill, outline=out, width=int(w * K) if out else 0)
    def ln(s, pts, fill, w=3):
        s.d.line([(x * K, y * K) for x, y in pts], fill=fill, width=int(w * K), joint="curve")
    def pg(s, pts, fill): s.d.polygon([(x * K, y * K) for x, y in pts], fill=fill)
    def tx(s, x, y, t, size, fill, font=FB, anchor="la"):
        s.d.text((x * K, y * K), t, font=F(font, size), fill=fill, anchor=anchor)
    def tw(s, t, size, font=FB): return s.d.textlength(t, font=F(font, size)) / K
    def wrap(s, x, y, t, size, fill, maxw, font=FR, lh=1.35, anchor="l"):
        words, line, rows = t.split(), "", []
        for w_ in words:
            if s.tw((line + " " + w_).strip(), size, font) > maxw and line: rows.append(line); line = w_
            else: line = (line + " " + w_).strip()
        rows.append(line)
        for i, r in enumerate(rows): s.tx(x, y + i * size * lh, r, size, fill, font, anchor + "a")
        return y + len(rows) * size * lh
    def dash(s, p1, p2, fill, w=4, on=14, off=12, ph=0.0):
        (x1, y1), (x2, y2) = p1, p2; L = math.hypot(x2 - x1, y2 - y1); ux, uy = (x2 - x1) / L, (y2 - y1) / L
        a = -ph % (on + off) - (on + off)
        while a < L:
            s0, s1 = max(a, 0), min(a + on, L)
            if s1 > s0: s.ln([(x1 + ux * s0, y1 + uy * s0), (x1 + ux * s1, y1 + uy * s1)], fill, w)
            a += on + off

# ---------------------------------------------------------------- pictures
def plate(c, cx, cy, w, h, text="XX 00 XX 0000", dbl=False, col=(250, 250, 244)):
    c.rr([cx - w / 2 + 3, cy - h / 2 + 5, cx + w / 2 + 3, cy + h / 2 + 5], h * .14, fill=(196, 214, 204))
    c.rr([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], h * .14, fill=col, out=(40, 52, 48), w=max(3, h * .045))
    c.rr([cx - w / 2 + 6, cy - h / 2 + 6, cx - w / 2 + h * .26, cy + h / 2 - 6], h * .08, fill=BLUE)
    if dbl:
        a, b = text.split(" ", 1) if " " in text else (text, "")
        parts = ["XX 00", "XX 0000"]
        for i, p_ in enumerate(parts):
            c.tx(cx + h * .1, cy + (-h * .22 if i == 0 else h * .24), p_, h * .36, (28, 34, 32), FM, "mm")
    else:
        c.tx(cx + h * .1, cy, text, h * .46, (28, 34, 32), FM, "mm")

def wheel(c, x, y, r):
    c.el([x - r, y - r, x + r, y + r], fill=(30, 36, 34)); c.el([x - r * .5, y - r * .5, x + r * .5, y + r * .5], fill=(150, 162, 156))

def vehicle(c, kind, x, yb, col, s=1.0, show_plate=True):
    """Flat side view. x = left edge, yb = ground line. Sizes ~ car 300x120 at s=1."""
    dk = mix(col, (0, 0, 0), .3); win = (176, 208, 224)
    if kind == "car":
        c.rr([x, yb - 62 * s, x + 300 * s, yb - 18 * s], 16 * s, fill=col)
        c.pg([(x + 62 * s, yb - 62 * s), (x + 100 * s, yb - 112 * s), (x + 214 * s, yb - 112 * s), (x + 252 * s, yb - 62 * s)], col)
        c.pg([(x + 78 * s, yb - 66 * s), (x + 108 * s, yb - 104 * s), (x + 150 * s, yb - 104 * s), (x + 150 * s, yb - 66 * s)], win)
        c.pg([(x + 158 * s, yb - 66 * s), (x + 158 * s, yb - 104 * s), (x + 208 * s, yb - 104 * s), (x + 236 * s, yb - 66 * s)], win)
        wheel(c, x + 70 * s, yb - 20 * s, 26 * s); wheel(c, x + 232 * s, yb - 20 * s, 26 * s); pw, ph, px, py = 56, 24, 270, 52
    elif kind == "bus":
        c.rr([x, yb - 150 * s, x + 470 * s, yb - 18 * s], 20 * s, fill=col)
        for i in range(6): c.rr([x + (20 + i * 70) * s, yb - 130 * s, x + (76 + i * 70) * s, yb - 84 * s], 6 * s, fill=win)
        c.rr([x + 430 * s, yb - 130 * s, x + 462 * s, yb - 60 * s], 6 * s, fill=win)
        wheel(c, x + 90 * s, yb - 20 * s, 28 * s); wheel(c, x + 380 * s, yb - 20 * s, 28 * s); pw, ph, px, py = 56, 24, 420, 50
    elif kind == "truck":
        c.rr([x, yb - 150 * s, x + 320 * s, yb - 24 * s], 8 * s, fill=mix(col, (255, 255, 255), .25))
        c.rr([x + 330 * s, yb - 100 * s, x + 450 * s, yb - 24 * s], 14 * s, fill=col)
        c.pg([(x + 350 * s, yb - 96 * s), (x + 410 * s, yb - 96 * s), (x + 440 * s, yb - 64 * s), (x + 350 * s, yb - 64 * s)], win)
        wheel(c, x + 70 * s, yb - 22 * s, 26 * s); wheel(c, x + 250 * s, yb - 22 * s, 26 * s); wheel(c, x + 390 * s, yb - 22 * s, 26 * s)
        pw, ph, px, py = 52, 22, 396, 48
    elif kind == "bike":
        wheel(c, x + 36 * s, yb - 34 * s, 34 * s); wheel(c, x + 150 * s, yb - 34 * s, 34 * s)
        c.ln([(x + 36 * s, yb - 34 * s), (x + 90 * s, yb - 70 * s), (x + 150 * s, yb - 34 * s)], col, 8 * s)
        c.rr([x + 70 * s, yb - 96 * s, x + 126 * s, yb - 66 * s], 10 * s, fill=col)
        c.el([x + 94 * s, yb - 150 * s, x + 122 * s, yb - 122 * s], fill=dk); c.rr([x + 90 * s, yb - 122 * s, x + 122 * s, yb - 82 * s], 8 * s, fill=dk)
        c.ln([(x + 150 * s, yb - 34 * s), (x + 138 * s, yb - 100 * s), (x + 118 * s, yb - 104 * s)], dk, 6 * s)
        pw, ph, px, py = 40, 18, 64, 36
    else:  # auto rickshaw
        c.rr([x, yb - 86 * s, x + 190 * s, yb - 24 * s], 14 * s, fill=col)
        c.pg([(x + 10 * s, yb - 86 * s), (x + 30 * s, yb - 130 * s), (x + 150 * s, yb - 130 * s), (x + 190 * s, yb - 86 * s)], dk)
        c.pg([(x + 120 * s, yb - 90 * s), (x + 150 * s, yb - 122 * s), (x + 176 * s, yb - 90 * s)], win)
        wheel(c, x + 44 * s, yb - 22 * s, 22 * s); wheel(c, x + 158 * s, yb - 22 * s, 22 * s); pw, ph, px, py = 44, 20, 126, 40
    if show_plate:
        c.rr([x + (px - pw / 2) * s, yb - py * s - ph * s / 2, x + (px + pw / 2) * s, yb - py * s + ph * s / 2], 3 * s, fill=(250, 250, 244), out=(40, 52, 48), w=1.5)
    return (x + (px - pw / 2) * s, yb - py * s - ph * s / 2, x + (px + pw / 2) * s, yb - py * s + ph * s / 2)

def brackets(c, b, col, pad=8, ln=22, w=5):
    x0, y0, x1, y1 = b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad
    for (x, y, dx, dy) in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
        c.ln([(x, y + dy * ln), (x, y), (x + dx * ln, y)], col, w)

def icon_camera(c, cx, cy, s=1.0, t=0):
    c.rr([cx - 70 * s, cy - 40 * s, cx + 54 * s, cy + 40 * s], 14 * s, fill=INK)
    c.pg([(cx + 54 * s, cy - 14 * s), (cx + 84 * s, cy - 30 * s), (cx + 84 * s, cy + 30 * s), (cx + 54 * s, cy + 14 * s)], INK)
    c.el([cx - 40 * s, cy - 24 * s, cx + 8 * s, cy + 24 * s], fill=(70, 96, 110)); c.el([cx - 28 * s, cy - 12 * s, cx - 4 * s, cy + 12 * s], fill=(150, 196, 214))
    c.el([cx + 24 * s, cy - 30 * s, cx + 36 * s, cy - 18 * s], fill=fc(RED, .55 + .45 * math.sin(t * 6) ** 2))

def icon_mail(c, cx, cy, s=1.0, col=ACC):
    c.rr([cx - 60 * s, cy - 40 * s, cx + 60 * s, cy + 40 * s], 10 * s, fill=CARD, out=col, w=4)
    c.ln([(cx - 60 * s, cy - 36 * s), (cx, cy + 6 * s), (cx + 60 * s, cy - 36 * s)], col, 4)

def icon_doc(c, cx, cy, label, col, s=1.0, bars=True):
    c.rr([cx - 56 * s, cy - 72 * s, cx + 56 * s, cy + 72 * s], 10 * s, fill=CARD, out=col, w=4)
    c.rr([cx - 56 * s, cy - 72 * s, cx + 56 * s, cy - 36 * s], 10 * s, fill=col)
    c.tx(cx, cy - 54 * s, label, 22 * s, (255, 255, 255), FB, "mm")
    if bars:
        for i, h_ in enumerate([30, 52, 38, 62]): c.rr([cx - 40 * s + i * 22 * s, cy + 56 * s - h_ * s, cx - 28 * s + i * 22 * s, cy + 56 * s], 3, fill=mix(col, BGC, .35))

def icon_barrier(c, cx, gy, ang, s=1.0):
    c.rr([cx - 26 * s, gy - 120 * s, cx + 26 * s, gy], 8 * s, fill=INK)
    px, py = cx, gy - 100 * s; L = 340 * s; a = math.radians(ang)
    ex, ey = px - L * math.cos(a), py - L * math.sin(a)
    c.ln([(px, py), (ex, ey)], (232, 232, 224), 16 * s)
    for i in range(1, 6):
        u0, u1 = (i * 2 - 1) / 11, (i * 2) / 11
        c.ln([(px + (ex - px) * u0, py + (ey - py) * u0), (px + (ex - px) * u1, py + (ey - py) * u1)], RED, 16 * s)
    c.el([px - 12 * s, py - 12 * s, px + 12 * s, py + 12 * s], fill=AMB)

def tick(c, cx, cy, r, col, p=1.0):
    c.el([cx - r, cy - r, cx + r, cy + r], fill=col)
    pts = [(cx - r * .45, cy + r * .02), (cx - r * .1, cy + r * .38), (cx + r * .5, cy - r * .32)]
    if p < .5: pts = [pts[0], (lerp(pts[0][0], pts[1][0], p * 2), lerp(pts[0][1], pts[1][1], p * 2))]
    else: pts = [pts[0], pts[1], (lerp(pts[1][0], pts[2][0], (p - .5) * 2), lerp(pts[1][1], pts[2][1], (p - .5) * 2))]
    c.ln(pts, (255, 255, 255), r * .22)

def cross(c, cx, cy, r, col):
    c.el([cx - r, cy - r, cx + r, cy + r], fill=col)
    c.ln([(cx - r * .38, cy - r * .38), (cx + r * .38, cy + r * .38)], (255, 255, 255), r * .22)
    c.ln([(cx + r * .38, cy - r * .38), (cx - r * .38, cy + r * .38)], (255, 255, 255), r * .22)

def chip(c, cx, y, text, p, col=ACC, size=30):
    if p <= 0: return
    w = c.tw(text, size, FB) + 76; yo = (1 - ease(p)) * 18
    c.rr([cx - w / 2, y + yo, cx + w / 2, y + 62 + yo], 31, fill=fc(CARD, p), out=fc(col, p), w=3)
    c.el([cx - w / 2 + 20, y + 25 + yo, cx - w / 2 + 38, y + 43 + yo], fill=fc(col, p))
    c.tx(cx - w / 2 + 52, y + 31 + yo, text, size, fc(INK, p), FB, "lm")

def card(c, b, r=28, fill=CARD, out=LINE):
    c.rr([b[0] + 4, b[1] + 8, b[2] + 4, b[3] + 8], r, fill=(200, 220, 208)); c.rr(b, r, fill=fill, out=out, w=2)

# ---------------------------------------------------------------- common layout
def header(c, title, sub, lt, step=None):  # step labels are no longer shown
    p = ramp(lt, .2, .9)
    c.tx(70, 168 - (1 - p) * 20, title, 66, fc(INK, p), FB)
    c.wrap(70, 262, sub, 33, fc(GREY, ramp(lt, .5, 1.2)), 940, FR)

def trail(c, active, lt, done_all=False):
    n = len(TRAIL); x0, x1, y = 120, 960, 1742
    for i, name in enumerate(TRAIL):
        x = x0 + (x1 - x0) * i / (n - 1)
        if i < n - 1:
            xn = x0 + (x1 - x0) * (i + 1) / (n - 1); c.ln([(x + 26, y), (xn - 26, y)], ACCL if (i < active or done_all) else LINE, 4)
        on = (i == active - 1) if active else False; dn = (0 < i + 1 < active) or done_all
        col = ACC if (on or dn) else (170, 196, 184)
        r = 24 + (4 * math.sin(lt * 5) if on else 0)
        c.el([x - r, y - r, x + r, y + r], fill=col if (on or dn) else CARD, out=col, w=3)
        c.tx(x, y, str(i + 1), 24, (255, 255, 255) if (on or dn) else GREY, FB, "mm")
        c.tx(x, y + 50, name, 20, INK if on else GREY, FB if on else FR, "mm")

def bar(c, t):
    c.rr([70, 1858, 1010, 1866], 4, fill=(200, 220, 208)); c.rr([70, 1858, 70 + 940 * t / DUR, 1866], 4, fill=ACC)

def badge(c, logo, cx, y, w, h):
    c.rr([cx - w / 2, y, cx + w / 2, y + h], h * .22, fill=NAVY)
    lg = logo.resize((int(h * .86 * K), int(h * .86 * 470 / 580 * K * 580 / 470 * 0.95)), Image.LANCZOS)
    lg = logo.resize((int(h * .92 * K * 580 / 470), int(h * .92 * K)), Image.LANCZOS)
    c.im.alpha_composite(lg.convert("RGBA"), (int((cx - lg.width / K / 2) * K), int((y + h * .04) * K)))

# ---------------------------------------------------------------- scenes
def s_intro(c, lt, facts, logo, g):
    p = ramp(lt, 0, .8)
    badge(c, logo, 540, 380 - (1 - p) * 30, 520, 420 * 0.0 + 410)
    c.tx(540, 880, "SytronANPR", 112, fc(INK, ramp(lt, .5, 1.3)), FB, "mm")
    for i, (t_, col) in enumerate([("Read every plate,", INK), ("track every vehicle,", ACC2), ("control every gate.", ACC)]):
        pp = ramp(lt, 1.2 + i * .9, 1.9 + i * .9); c.tx(540, 1010 + i * 72 - (1 - pp) * 16, t_, 50, fc(col, pp), FB, "mm")
    # car driving through scanned lane
    gy = 1530
    c.rr([0, gy, 1080, gy + 10], 5, fill=LINE)
    x = -320 + (lt / 6.0) * 1500
    pb = vehicle(c, "car", x, gy, (84, 128, 150), 1.0)
    if 120 < pb[0] < 900: brackets(c, pb, ACC, 10, 16, 4)

def s_how(c, lt, facts, logo, g):
    header(c, "From camera to action", "A camera sees the vehicle. SytronANPR reads the plate in real time, and everything else follows.", lt)
    # camera
    p1 = ramp(lt, .8, 1.5); card(c, [250, 430, 830, 640]); c.tx(540, 612, "Camera", 28, fc(INK, p1), FB, "mm")
    icon_camera(c, 440, 520, .9, lt); vehicle(c, "car", 530, 560, (84, 128, 150), .32, True)
    # arrow 1
    for i in range(3):
        y = 650 + ((lt * 120 + i * 60) % 180) * 0.0 + ((lt * 90 + i * 60) % 180)
    c.dash((540, 650), (540, 790), ACC, 5, ph=lt * 60)
    # engine
    p2 = ramp(lt, 1.8, 2.6); card(c, [180, 800, 900, 1090])
    c.tx(540, 842, "SytronANPR", 34, fc(INK, p2), FB, "mm")
    scan = (lt * .5) % 1.0
    plate(c, 540, 960, 420, 96)
    sx = 330 + 420 * scan; c.rr([sx - 6, 910, sx + 6, 1010], 4, fill=fc(ACC, .8))
    rd = clamp((lt - 3.2) / 1.6)
    c.tx(540, 1048, "XX 00 XX 0000"[:int(13 * rd)] or " ", 30, ACC, FM, "mm")
    # fan out
    ends = [(260, "Email alert"), (540, "Gate control"), (820, "Reports")]
    for i, (x, lab) in enumerate(ends):
        c.dash((540, 1090), (x, 1210), ACC, 4, ph=lt * 60) if lt > 4.2 + i * .3 else None
        pp = ramp(lt, 4.6 + i * .5, 5.4 + i * .5)
        if pp > 0:
            card(c, [x - 125, 1215, x + 125, 1470]); c.tx(x, 1440, lab, 26, fc(INK, pp), FB, "mm")
            if i == 0: icon_mail(c, x, 1330, .8)
            elif i == 1: icon_barrier(c, x - 20, 1385, 40 if lt > 6.5 else 0, .5)
            else: icon_doc(c, x, 1328, "PDF", ACC2, .6)
    chip(c, 540, 1540, "Real-time reading", ramp(lt, 6.4, 7.0))

def s_plates(c, lt, facts, logo, g):
    header(c, "Single and double-line", facts["products"][0]["features"][0] + ".", lt, 1)
    # single-line
    card(c, [90, 420, 990, 800]); c.tx(130, 450, "SINGLE-LINE", 24, ACC, FB)
    plate(c, 540, 600, 640, 150, dbl=False)
    sc = ramp(lt, .8, 2.6); sx = 220 + 640 * sc
    if .8 < lt < 2.8: c.rr([sx - 5, 515, sx + 5, 685], 4, fill=ACC)
    if lt > 1.2: brackets(c, (220, 525, 860, 675), ACC, 8, 28, 6)
    c.tx(540, 745, "XX 00 XX 0000"[:int(13 * clamp((lt - 2.4) / 1.2))] or " ", 40, ACC, FM, "mm")
    if lt > 3.6: tick(c, 910, 745, 24, ACC, ramp(lt, 3.6, 4.2))
    # double-line
    card(c, [90, 860, 990, 1340]); c.tx(130, 890, "DOUBLE-LINE", 24, ACC2, FB)
    plate(c, 540, 1080, 430, 220, dbl=True)
    sc = ramp(lt, 3.8, 5.6); sy = 970 + 220 * sc
    if 3.8 < lt < 5.8: c.rr([320, sy - 5, 760, sy + 5], 4, fill=ACC2)
    if lt > 4.2: brackets(c, (325, 970, 755, 1190), ACC2, 8, 28, 6)
    c.tx(540, 1275, "XX 00 XX 0000"[:int(13 * clamp((lt - 5.4) / 1.2))] or " ", 40, ACC2, FM, "mm")
    if lt > 6.6: tick(c, 910, 1275, 24, ACC2, ramp(lt, 6.6, 7.2))
    chip(c, 300, 1450, "Single-line", ramp(lt, 1.0, 1.6)); chip(c, 700, 1450, "Double-line", ramp(lt, 4.0, 4.6))
    chip(c, 540, 1540, "Real time", ramp(lt, 6.0, 6.6))

def s_light(c, lt, facts, logo, g):
    header(c, "Day, night, rain, glare", facts["products"][0]["features"][1] + ".", lt, 2)
    tiles = [("DAY", 90, 420, (196, 222, 236), 0), ("NIGHT", 550, 420, (22, 38, 66), 1), ("RAIN", 90, 900, (150, 170, 182), 2), ("GLARE", 550, 900, (236, 232, 206), 3)]
    for i, (name, x, y, bg, kind) in enumerate(tiles):
        p = ramp(lt, .6 + i * .45, 1.2 + i * .45); yo = (1 - p) * 30
        if p <= 0: continue
        b = [x, y + yo, x + 440, y + 440 + yo]
        c.rr([b[0] + 4, b[1] + 8, b[2] + 4, b[3] + 8], 28, fill=(200, 220, 208)); c.rr(b, 28, fill=fc(bg, p))
        cx, cy = x + 220, y + yo
        if kind == 0:
            for k in range(10):
                a = lt * .5 + k * math.pi / 5; c.ln([(cx + 150 + 54 * math.cos(a), cy + 90 + 54 * math.sin(a)), (cx + 150 + 82 * math.cos(a), cy + 90 + 82 * math.sin(a))], (236, 196, 90), 5)
            c.el([cx + 118, cy + 58, cx + 182, cy + 122], fill=(240, 202, 96))
        elif kind == 1:
            c.el([cx + 100, cy + 52, cx + 164, cy + 116], fill=(232, 232, 214)); c.el([cx + 124, cy + 44, cx + 180, cy + 104], fill=bg)
            for k, (sx_, sy_) in enumerate([(-150, 60), (-90, 110), (-40, 50), (30, 90), (-120, 30)]):
                r_ = 3 + 2 * math.sin(lt * 4 + k); c.el([cx + sx_ - r_, cy + sy_ - r_, cx + sx_ + r_, cy + sy_ + r_], fill=(240, 240, 220))
        elif kind == 2:
            c.el([cx - 110, cy + 40, cx - 30, cy + 90], fill=(120, 134, 144)); c.el([cx - 70, cy + 20, cx + 40, cy + 100], fill=(120, 134, 144)); c.el([cx, cy + 40, cx + 100, cy + 96], fill=(120, 134, 144))
            for k in range(14):
                rx = cx - 130 + k * 20; ry = cy + 110 + ((lt * 500 + k * 53) % 250)
                if ry < cy + 330: c.ln([(rx, ry), (rx - 8, ry + 24)], (206, 224, 236), 3)
        else:
            pul = .6 + .4 * math.sin(lt * 4)
            for k in range(12):
                a = k * math.pi / 6 + lt * .3; c.ln([(cx + 140, cy + 100), (cx + 140 + 130 * pul * math.cos(a), cy + 100 + 130 * pul * math.sin(a))], (250, 244, 196), 6)
            c.el([cx + 100, cy + 60, cx + 180, cy + 140], fill=(255, 252, 224))
        vehicle(c, "car", x + 70, y + 380 + yo, (84, 128, 150) if kind != 1 else (60, 80, 110), .98, True)
        c.tx(x + 24, y + 22 + yo, name, 26, INK if kind in (0, 3) else (240, 244, 240), FB)
        ok = ramp(lt, 2.0 + i * 1.2, 2.6 + i * 1.2)
        if ok > 0:
            plate(c, x + 220, y + 258 + yo, 250, 60); tick(c, x + 400, y + 40 + yo, 22, ACC, ok)
            brackets(c, (x + 95, y + 228 + yo, x + 345, y + 288 + yo), ACC, 6, 14, 4)
    for i, n_ in enumerate(["Day", "Night", "Rain", "Glare"]): chip(c, 150 + i * 260 if i < 2 else 150 + i * 260, 1450 + (i // 2) * 84 - (i // 2) * 0, n_, ramp(lt, 5.6 + i * .3, 6.2 + i * .3), ACC2, 28) if False else None
    chip(c, 540, 1540, "Reads in every condition", ramp(lt, 6.0, 6.6))

def s_multi(c, lt, facts, logo, g):
    header(c, "Many plates, one view", facts["products"][0]["features"][2] + ".", lt, 3)
    card(c, [80, 420, 1000, 1130], fill=(70, 94, 88), out=(70, 94, 88))
    c.rr([80, 880, 1000, 1130], 28, fill=(96, 118, 112)); c.pg([(80, 880), (1000, 880), (1000, 920), (80, 920)], (112, 132, 126))
    for x in range(120, 1000, 120): c.rr([x, 1010 + 0, x + 60, 1018], 4, fill=(190, 204, 196))
    c.tx(110, 448, "CAMERA VIEW", 24, (210, 232, 220), FB); c.el([904, 450, 920, 466], fill=fc(RED, .5 + .5 * math.sin(lt * 5) ** 2)); c.tx(940, 448, "LIVE", 22, (240, 244, 240), FB)
    veh = [("car", (200, 140, 120), 0.0, 960, .6), ("auto", (202, 168, 70), 1.2, 1060, .75), ("truck", (110, 140, 160), 2.4, 1100, .5)]
    labs = []
    for i, (k, col, d0, gy, sz) in enumerate(veh):
        x = -520 + (lt + d0 - 0.5) * 120 + i * 0 + 560 * (1 if i != 1 else 1) * 0.0 + [260, 0, 520][i] * 0.0
        x = 120 + [0, 300, 560][i] + (lt * 24) * (1 if i != 1 else 1)
        pb = vehicle(c, k, x, gy, col, sz, True)
        det = ramp(lt, 1.6 + i * 1.3, 2.2 + i * 1.3)
        if det > 0:
            brackets(c, pb, ACC if i != 1 else ACC2, 10, 18, 5); labs.append((i, pb))
    for i in range(3):
        p = ramp(lt, 2.2 + i * 1.3, 3.0 + i * 1.3)
        if p > 0:
            y = 1180 + i * 0
            x0 = 80 + i * 312; card(c, [x0, 1160, x0 + 296, 1300], r=20)
            c.tx(x0 + 24, 1182, f"PLATE {i + 1}", 20, fc(ACC if i != 1 else ACC2, p), FB)
            plate(c, x0 + 148, 1252, 240, 54); tick(c, x0 + 268, 1178, 14, ACC if i != 1 else ACC2, p)
    chip(c, 540, 1400, "Three plates, one camera", ramp(lt, 5.4, 6.0))
    chip(c, 540, 1490, "Each read separately", ramp(lt, 6.0, 6.6), ACC2)

def s_types(c, lt, facts, logo, g):
    header(c, "Five vehicle types", facts["products"][0]["features"][3] + ".", lt, 4)
    items = [("Car", "car", (84, 128, 150), 0.62), ("Bus", "bus", (196, 128, 80), .42), ("Truck", "truck", (110, 140, 120), .44), ("Two-wheeler", "bike", (176, 96, 84), .85), ("Auto", "auto", (214, 170, 66), .8)]
    pos = [(90, 430), (550, 430), (90, 770), (550, 770), (320, 1110)]
    act = int(clamp((lt - 1.2) / 1.1, 0, 4.99)) if lt > 1.2 else -1
    for i, (name, k, col, s) in enumerate(items):
        p = ramp(lt, .6 + i * .35, 1.2 + i * .35)
        if p <= 0: continue
        x, y = pos[i]; yo = (1 - p) * 30; on = (i == act)
        c.rr([x + 4, y + 8 + yo, x + 444, y + 308 + yo], 28, fill=(200, 220, 208))
        c.rr([x, y + yo, x + 440, y + 300 + yo], 28, fill=CARD, out=ACC if on else LINE, w=5 if on else 2)
        vw = {"car": 300, "bus": 470, "truck": 450, "bike": 190, "auto": 190}[k] * s
        pb = vehicle(c, k, x + 220 - vw / 2, y + 210 + yo, col, s, True)
        if on: brackets(c, pb, ACC, 8, 12, 4)
        c.rr([x + 20, y + 236 + yo, x + 420, y + 282 + yo], 23, fill=ACC if on else CARD2)
        c.tx(x + 220, y + 260 + yo, name.upper(), 24, (255, 255, 255) if on else GREY, FB, "mm")
    chip(c, 540, 1500, "Car · Bus · Truck · Two-wheeler · Auto", ramp(lt, 5.4, 6.0), ACC, 26)

def s_alert(c, lt, facts, logo, g):
    header(c, "Instant email alerts", facts["products"][0]["features"][4] + ".", lt, 5)
    card(c, [90, 420, 990, 760]); gy = 700
    c.rr([110, gy, 970, gy + 8], 4, fill=LINE); icon_camera(c, 200, 510, .8, lt)
    x = -300 + ramp(lt, .4, 2.2) * 700; pb = vehicle(c, "car", x, gy, (84, 128, 150), 1.0, True)
    flash = clamp(1 - abs(lt - 2.3) * 3)
    if lt > 1.6: brackets(c, pb, ACC, 10, 18, 5)
    if flash > 0: c.rr([90, 420, 990, 760], 28, fill=mix(CARD, (255, 255, 255), flash * .0 + .0)) if False else None
    c.dash((200, 560), (pb[0] + 28, pb[1]), AMB, 3, ph=lt * 40) if 1.0 < lt < 2.4 else None
    # envelope flight
    p = ramp(lt, 2.5, 4.4)
    if 0 < p < 1:
        ex, ey = lerp(540, 540, p), lerp(790, 1050, p); icon_mail(c, ex, ey, .9)
        plate(c, ex, ey + 4, 80, 22) if False else None
    c.dash((540, 790), (540, 920), ACC, 5, ph=lt * 60) if lt > 2.4 else None
    # phone
    ph = ramp(lt, 1.0, 2.0); yo = (1 - ph) * 80
    c.rr([300 + 4, 900 + 8 + yo, 780 + 4, 1480 + 8 + yo], 56, fill=(200, 220, 208))
    c.rr([300, 900 + yo, 780, 1480 + yo], 56, fill=(30, 40, 38)); c.rr([316, 920 + yo, 764, 1460 + yo], 42, fill=(240, 246, 242))
    c.rr([470, 930 + yo, 610, 944 + yo], 7, fill=(30, 40, 38))
    c.tx(344, 980 + yo, "Inbox", 28, INK, FB); c.ln([(340, 1018 + yo), (740, 1018 + yo)], LINE, 2)
    for k in range(2): c.rr([344, 1290 + k * 70 + yo, 740 - k * 80, 1310 + k * 70 + yo], 8, fill=CARD2)
    n = ramp(lt, 3.6, 4.6)
    if n > 0:
        yy = 1040 + yo + (1 - n) * -40
        c.rr([336, yy, 744, yy + 220], 22, fill=fc(CARD, n), out=fc(ACC, n), w=3)
        icon_mail(c, 392, yy + 54, .42, fc(ACC, n)); c.tx(436, yy + 38, "ALERT", 20, fc(ACC, n), FB); c.tx(436, yy + 62, "Plate detected", 26, fc(INK, n), FB)
        plate(c, 540, yy + 152, 300, 70)
    chip(c, 540, 1540, "Plate image attached", ramp(lt, 5.4, 6.0))

def s_gate(c, lt, facts, logo, g):
    header(c, "Only whitelisted plates", facts["products"][0]["features"][5] + ".", lt, 6)
    card(c, [90, 420, 990, 1010]); gy = 930
    c.rr([110, gy, 970, gy + 8], 4, fill=LINE)
    arm = 0.0
    if 2.9 < lt < 3.7: arm = 80 * ramp(lt, 2.9, 3.7)
    elif 3.7 <= lt < 5.0: arm = 80
    elif 5.0 <= lt < 5.8: arm = 80 * (1 - ramp(lt, 5.0, 5.8))
    # car A (whitelisted): enters, stops, then passes. car B (unknown): enters, stops.
    def xa():
        if lt < .6: return -320
        if lt < 2.4: return lerp(-320, 330 - 320 + 0, ramp(lt, .6, 2.4))
        if lt < 3.7: return 10
        return lerp(10, 1100, ramp(lt, 3.7, 5.4))
    xA = xa(); pbA = vehicle(c, "car", xA, gy, (84, 128, 150), .9, True)
    xB = lerp(-320, 10, ramp(lt, 5.2, 6.8)) if lt > 5.2 else -320
    pbB = vehicle(c, "auto", xB + 60, gy, (214, 170, 66), .9, True) if lt > 5.2 else None
    icon_barrier(c, 770, gy, arm, 1.0)
    if 1.8 < lt < 3.6: brackets(c, pbA, ACC, 8, 14, 4)
    if lt > 2.2 and lt < 4.6: tick(c, pbA[0] + 30, pbA[1] - 150, 26, ACC, ramp(lt, 2.2, 2.8)) if lt < 3.7 else None
    if 6.4 < lt: brackets(c, pbB, RED, 8, 14, 4); cross(c, pbB[0] + 20, pbB[1] - 150, 26, RED)
    # whitelist card
    card(c, [90, 1060, 990, 1420]); c.tx(130, 1090, "WHITELIST", 24, ACC, FB)
    for i in range(3):
        y = 1170 + i * 78; hit = (i == 0 and 2.0 < lt < 4.8)
        c.rr([130, y - 30, 760, y + 30], 14, fill=ACCL if hit else CARD2)
        c.tx(160, y, "XX 00 XX 0000", 30, INK, FM, "lm")
        if hit: tick(c, 700, y, 18, ACC, ramp(lt, 2.2, 2.8))
    pn = ramp(lt, 6.4, 7.0)
    if pn > 0:
        c.rr([790, 1140, 950, 1210], 14, fill=fc(CARD, pn), out=fc(RED, pn), w=3); c.tx(870, 1175, "Not listed", 22, fc(RED, pn), FB, "mm")
    chip(c, 330, 1520, "Whitelisted: opens", ramp(lt, 4.2, 4.8)); chip(c, 760, 1520, "Others: stays closed", ramp(lt, 6.6, 7.2), RED, 26) if False else None
    chip(c, 760, 1520, "Others: closed", ramp(lt, 6.6, 7.2), RED, 28)

def s_reports(c, lt, facts, logo, g):
    header(c, "Reports by email", facts["products"][0]["features"][6] + ".", lt, 7)
    docs = [(260, "PDF", RED), (540, "WORD", BLUE), (820, "CSV", ACC)]
    for i, (x, lab, col) in enumerate(docs):
        p = ramp(lt, .6 + i * .5, 1.3 + i * .5)
        if p > 0:
            yo = (1 - p) * 40; card(c, [x - 125, 440 + yo, x + 125, 800 + yo])
            icon_doc(c, x, 620 + yo, lab, col, 1.25)
    # calendar
    p = ramp(lt, 2.6, 3.4)
    if p > 0:
        card(c, [160, 880, 920, 1100]); c.tx(200, 910, "DELIVERY", 24, ACC, FB)
        for i, lab in enumerate(["Daily", "Weekly"]):
            on = (int((lt - 3.4) / 1.5) % 2 == i) if lt > 3.4 else False
            c.rr([200 + i * 360, 960, 540 + i * 360 - 20, 1060], 24, fill=ACC if on else CARD2)
            c.tx(370 + i * 360 - 10, 1010, lab, 36, (255, 255, 255) if on else GREY, FB, "mm")
    # envelope with attachment
    q = ramp(lt, 4.4, 6.2)
    c.dash((540, 1110), (540, 1230), ACC, 5, ph=lt * 60) if lt > 4.2 else None
    if q > 0:
        card(c, [240, 1240, 840, 1480]); icon_mail(c, 540, 1360 + (1 - ramp(lt, 4.4, 5.2)) * -20, 1.5)
        for i, (x, lab, col) in enumerate([(180, "PDF", RED), (240, "DOC", BLUE), (300, "CSV", ACC)]):
            pp = ramp(lt, 5.2 + i * .3, 5.7 + i * .3)
            if pp > 0: c.rr([620 + i * 66, 1410 - pp * 0, 680 + i * 66, 1450], 8, fill=fc(col, pp)); c.tx(650 + i * 66, 1430, lab[0], 22, (255, 255, 255), FB, "mm")
    chip(c, 540, 1540, "Sent to your inbox", ramp(lt, 6.4, 7.0))

def s_outro(c, lt, facts, logo, g):
    badge(c, logo, 540, 330, 520, 410)
    c.tx(540, 830, "SytronANPR", 104, fc(INK, ramp(lt, .3, 1.0)), FB, "mm")
    for i, (t_, col) in enumerate([("Read every plate.", INK), ("Track every vehicle.", ACC2), ("Control every gate.", ACC)]):
        pp = ramp(lt, .9 + i * .8, 1.6 + i * .8); c.tx(540, 960 + i * 70 - (1 - pp) * 16, t_, 50, fc(col, pp), FB, "mm")
    pb = ramp(lt, 3.6, 4.4); pul = 1 + .03 * math.sin(lt * 4)
    if pb > 0:
        w = 640 * pul; c.rr([540 - w / 2, 1280 - 52, 540 + w / 2, 1280 + 52], 52, fill=fc(ACC, pb))
        c.tx(540, 1280, facts["website"], 40, fc((255, 255, 255), pb), FB, "mm")
    c.tx(540, 1400, facts["tagline"], 32, fc(GREY, ramp(lt, 4.4, 5.2)), FR, "mm")
    gy = 1600; c.rr([0, gy, 1080, gy + 10], 5, fill=LINE)
    vehicle(c, "bus", -520 + (lt / 8.0) * 1700, gy, (196, 128, 80), .8, True)

FUN = {"intro": s_intro, "how": s_how, "plates": s_plates, "light": s_light, "multi": s_multi, "types": s_types,
       "alert": s_alert, "gate": s_gate, "reports": s_reports, "outro": s_outro}

# ---------------------------------------------------------------- frame
def make_bg():
    im = Image.new("RGB", (W * K, H * K)); d = ImageDraw.Draw(im)
    for y in range(0, H * K, 4): d.rectangle([0, y, W * K, y + 4], fill=mix(BGT, BGB, y / (H * K)))
    return im
def hills(c, t):
    for lay, (col, amp, ph, base) in enumerate([((200, 226, 212), 40, 0.0, 1800), ((188, 218, 202), 30, 2.0, 1830)]):
        pts = [(x, base + amp * math.sin(x / 170 + ph + t * .15)) for x in range(0, W + 41, 40)] + [(W, H), (0, H)]
        c.pg(pts, col)

def frame(t, facts, logo, g):
    base = g["bg"].copy().convert("RGBA")
    c0 = Cv(); hills(c0, t)
    for i in range(16):   # drifting soft dots
        x = (i * 173 + t * (10 + i % 5 * 4)) % (W + 80) - 40; y = (i * 331 - t * (14 + i % 4 * 6)) % 1500 + 100
        r = 6 + i % 4 * 3; c0.el([x - r, y - r, x + r, y + r], fill=(206, 230, 216))
    base.alpha_composite(c0.im)
    idx = next(i for i, (a, b, n) in enumerate(SCENES) if a <= t < b) if t < DUR else len(SCENES) - 1
    a, b, name = SCENES[idx]; lt = t - a; c = Cv()
    FUN[name](c, lt, facts, logo, g)
    fade = min(ramp(lt, 0, .35), 1 - ramp(lt, (b - a) - .3, b - a))
    if fade < 1: c.im.putalpha(c.im.getchannel("A").point(lambda v: int(v * fade)))
    base.alpha_composite(c.im)
    ov = Cv()
    bar(ov, t)
    tag = Image.new("RGBA", (1, 1))
    ov.rr([860, 60, 1010, 108], 24, fill=NAVY); ov.tx(935, 84, "sytronsoft", 24, (236, 244, 240), FB, "mm")
    base.alpha_composite(ov.im)
    return base.convert("RGB").resize((W, H), Image.LANCZOS)

def make_voice(path):
    """One flite clip per scene; scene length = clip + small pad (min MINLEN), voice starts 0.25 s into its scene, so there is no silence between lines."""
    global SCENES, DUR
    tmp = tempfile.mkdtemp(); ins, fl, t0, SCENES = [], [], 0.0, []
    for k, name in enumerate(ORDER):
        wav = os.path.join(tmp, f"v{k}.wav")
        subprocess.run(["flite", "-voice", "slt", "--setf", "duration_stretch=1.12", "-t", NARRATION[name], "-o", wav], check=True, capture_output=True)
        with wave.open(wav) as w: dur = w.getnframes() / w.getframerate()
        ln = max(MINLEN, dur + 0.25 + PAD)
        print(f"{name}: {t0:.1f}s, voice {dur:.1f}s, scene {ln:.1f}s")
        SCENES.append((t0, t0 + ln, name)); ins += ["-i", wav]
        fl.append(f"[{k}:a]adelay={int((t0 + .25) * 1000)}|{int((t0 + .25) * 1000)},apad[a{k}]"); t0 += ln
    DUR = t0
    mix_ = "".join(f"[a{k}]" for k in range(len(ORDER)))
    fcx = ";".join(fl) + f";{mix_}amix=inputs={len(ORDER)}:normalize=0,atrim=0:{DUR},loudnorm=I=-16:TP=-1.5[a]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", fcx, "-map", "[a]", "-ar", "44100", "-ac", "2", path], check=True)
    return path

_G = {}
def _init(yml, logo_p):
    _G["facts"] = yaml.safe_load(open(yml)); _G["logo"] = Image.open(logo_p).convert("RGB"); _G["bg"] = make_bg()
def _render(i): return frame(i / FPS, _G["facts"], _G["logo"], _G).tobytes()

def main():
    yml, logo_p, outp = sys.argv[1:4]
    if len(sys.argv) > 4:
        make_voice(os.path.join(tempfile.mkdtemp(), "voice.wav")); _init(yml, logo_p)
        for tt in sys.argv[4:]: frame(float(tt), _G["facts"], _G["logo"], _G).save(f"prev_{float(tt):05.2f}.png")
        return
    wav = make_voice(os.path.join(tempfile.mkdtemp(), "voice.wav"))
    n = int(DUR * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
           "-shortest", "-movflags", "+faststart", outp]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4, initializer=_init, initargs=(yml, logo_p)) as pool:
        for b in pool.imap(_render, range(n), chunksize=8): pr.stdin.write(b)
    pr.stdin.close(); pr.wait()
    print(f"reel: {outp} ({DUR:.0f} s, {n} frames, voice-over)")

if __name__ == "__main__":
    main()
