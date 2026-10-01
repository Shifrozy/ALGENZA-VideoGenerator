"""
ALGENZA Video Engine - Primary Multi-Format Frame Renderer
Faithfully renders 60fps explainer video for algenza.com across all major social media & web formats:
- 16:9 Landscape (1920x1080): YouTube, Web, LinkedIn, Twitter/X
- 9:16 Vertical  (1080x1920): TikTok, Instagram Reels, YouTube Shorts
- 1:1  Square    (1080x1080): Instagram Feed, LinkedIn Feed, Twitter/X Post
- 4:5  Portrait  (1080x1350): Instagram Portrait Feed, Facebook Post

Powered by pure-Python Skia engine with zero native crashes on Windows.
"""

import os
import sys
import math
import re
import subprocess
import io
import numpy as np

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

import skia
from tl import *

# 1. Discover FFmpeg Executable
try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"

# 2. Aspect Ratio & Resolution Configuration
ASPECT = os.environ.get("ASPECT", "16:9").strip().lower()
if ASPECT in ("9:16", "vertical", "reels", "shorts", "tiktok"):
    W, H = 1080, 1920
    MODE = "9:16"
elif ASPECT in ("1:1", "square", "instagram"):
    W, H = 1080, 1080
    MODE = "1:1"
elif ASPECT in ("4:5", "portrait", "feed"):
    W, H = 1080, 1350
    MODE = "4:5"
else:
    W, H = 1920, 1080
    MODE = "16:9"

IS_LAND = (MODE == "16:9")
IS_VERT = (MODE == "9:16")
IS_SQUARE = (MODE == "1:1")
IS_PORT = (MODE == "4:5")

FPS = 60

# 3. Fonts Setup (Robust System & Cross-Platform Fallbacks)
FD = os.environ.get('FD', '/usr/share/fonts/truetype/')
HF = FD + 'higgsfield/Montserrat-ExtraBold.ttf'
if not os.path.exists(HF): HF = FD + 'dejavu/DejaVuSans-Bold.ttf'

TF = {
    'h': skia.Typeface.MakeFromFile(HF),
    'b': skia.Typeface.MakeFromFile(FD + 'dejavu/DejaVuSans.ttf'),
    'bb': skia.Typeface.MakeFromFile(FD + 'dejavu/DejaVuSans-Bold.ttf'),
    'm': skia.Typeface.MakeFromFile(FD + 'dejavu/DejaVuSansMono.ttf'),
    'mb': skia.Typeface.MakeFromFile(FD + 'dejavu/DejaVuSansMono-Bold.ttf'),
    'lg': skia.Typeface.MakeFromFile(FD + 'higgsfield/Inter-Bold.ttf')
}

FC = {}
def F(k, s):
    s = int(s)
    if (k, s) not in FC:
        FC[(k, s)] = skia.Font(TF[k], s)
    return FC[(k, s)]

# 4. Brand Color Palette (Clean Minimalist Cyber-Quant Palette)
G = '#3FCB90'       # Algenza Emerald
CYAN = '#00E5FF'    # Algenza Quantum Accent Cyan
WH = '#F1F3F6'      # Crisp White
MU = '#8B9A92'      # Muted Slate
RD = '#EF4444'      # Missed / Sell Red
PN = '#11151C'      # Deep Panel Black
LN = '#252C38'      # Panel Border Gray
DK = '#07251A'      # Dark Pupil / Visor Tint

def P(h, a=1.0, sw=0):
    h = h.lstrip('#')
    a = max(0.0, min(1.0, a))
    p = skia.Paint(AntiAlias=True, Color=skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(a * 255)))
    if sw:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(sw)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    return p

def GL(h, a, sw=0, sig=12):
    p = P(h, a, sw)
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, sig))
    return p

def dash(a):
    p = P(MU, a, 2)
    p.setPathEffect(skia.DashPathEffect.Make([10, 8], 0))
    return p

def cl(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def eo(x): x = cl(x); return 1 - (1 - x) ** 3
def sm(t, a, b): return eo((t - a) / (b - a))
def bo(x):
    x = cl(x)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

def tx(c, s, x, y, k, sz, col=WH, a=1.0, al='l'):
    f = F(k, sz)
    w = f.measureText(s)
    if al == 'c': x -= w / 2
    elif al == 'r': x -= w
    c.drawString(s, x, y, f, P(col, a))
    return w

def logo(c, x, y, sz, a=1.0, al='l', glow=0.0):
    f = F('lg', sz)
    w1 = f.measureText("AL")
    w2 = f.measureText("GENZA")
    w = w1 + w2
    if al == 'c': x -= w / 2
    if glow > 0:
        gp = P(G, glow * a)
        gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, sz * 0.12))
        c.drawString("AL", x, y, f, gp)
    c.drawString("AL", x, y, f, P(G, a))
    c.drawString("GENZA", x + w1, y, f, P(WH, a))
    return w

def rr(c, l, t, r, b, rad, p):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(l, t, r, b), rad, rad), p)

def panel(c, l, t, r, b, a=1):
    rr(c, l, t, r, b, 18, P(PN, 0.92 * a))
    rr(c, l, t, r, b, 18, P(LN, a, 2))

CUR = [0.0, 0.0]
def head(c, s, x, y, a, sz=64):
    f = F('h', sz)
    sp = f.measureText(' ')
    for k, wd in enumerate(s.split()):
        g = sm(CUR[0], CUR[1] + 0.05 + k * 0.09, CUR[1] + 0.4 + k * 0.09)
        c.drawString(wd, x, y + (1 - g) * 22, f, P(WH, a * g))
        x += f.measureText(wd) + sp

def sub(c, s, x, y, a, sz=32):
    tx(c, s, x, y, 'b', sz, MU, a)

# 5. Pre-rendered Background with Soft Radial Glow & Tech Grid
def mkbg():
    s = skia.Surface(W, H)
    c = s.getCanvas()
    c.clear(skia.Color(12, 14, 19))
    gp = P('#181D26', 0.8, 1)
    grid_sz = 60 if IS_LAND else 48
    for x in range(0, W + 1, grid_sz): c.drawLine(x, 0, x, H, gp)
    for y in range(0, H + 1, grid_sz): c.drawLine(0, y, W, y, gp)
    
    # Subtle emerald ambient halo
    p = skia.Paint(AntiAlias=True)
    center_pt = skia.Point(W * 0.6 if IS_LAND else W * 0.5, H * 0.45)
    rad = max(W, H) * 0.55
    p.setShader(skia.GradientShader.MakeRadial(center_pt, rad, [skia.Color(63, 203, 144, 38), skia.Color(63, 203, 144, 0)]))
    c.drawRect(skia.Rect.MakeWH(W, H), p)
    
    # Subtle vignette
    p2 = skia.Paint(AntiAlias=True)
    p2.setShader(skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), max(W, H) * 0.7, [skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 160)]))
    c.drawRect(skia.Rect.MakeWH(W, H), p2)
    return s.makeImageSnapshot()

BG = mkbg()

# Load speech lip-sync envelope
try:
    MO = np.load('mouth.npy')
except Exception:
    MO = np.zeros(10)

# Procedural Candlestick Data
rng = np.random.default_rng(0)
CAND = []
p_val = 100.0
for k in range(16):
    o = p_val
    c_ = p_val + rng.normal(1.1, 1.5)
    h_ = max(o, c_) + abs(rng.normal(0, 0.8))
    l_ = min(o, c_) - abs(rng.normal(0, 0.8))
    CAND.append((o, h_, l_, c_))
    p_val = c_
PMIN = min(x[2] for x in CAND)
PMAX = max(x[1] for x in CAND)

def CY(v, base_y=820, height_span=430):
    return base_y - (v - PMIN) / (PMAX - PMIN) * height_span

EQ = np.cumsum(np.random.default_rng(7).normal(0.32, 1.0, 220))
EQ = (EQ - EQ.min()) / (EQ.max() - EQ.min())

# Character Waypoints Across Scenes for All 4 Aspect Ratios
if IS_VERT:
    # 9:16 Vertical coordinates
    A = [
        (540, 1420, 1.1),   # S0: Below chart
        (540, 1460, 1.0),   # S1: Below missed chart
        (540, 1380, 1.1),   # S2: Below ALGENZA logo
        (540, 1500, 0.95),  # S3: Below cards
        (540, 1520, 0.9),   # S4: Below pipeline
        (540, 1540, 0.9),   # S5: Below risk panel
        (540, 1520, 0.9),   # S6: Below files
        (540, 1460, 1.05),  # S7: Below metrics
        (540, 1320, 1.2)    # S8: Centered below CTA
    ]
elif IS_SQUARE:
    # 1:1 Square coordinates (1080x1080)
    A = [
        (870, 540, 0.85),   # S0: Beside chart
        (540, 780, 0.85),   # S1: Below chart
        (540, 700, 1.00),   # S2: Below ALGENZA logo
        (540, 780, 0.80),   # S3: Below 3 cards
        (540, 780, 0.75),   # S4: Below pipeline & code
        (540, 780, 0.75),   # S5: Below risk & phone
        (540, 780, 0.75),   # S6: Below package & checklist
        (540, 780, 0.85),   # S7: Below metric cards
        (540, 740, 1.05)    # S8: Centered below CTA
    ]
elif IS_PORT:
    # 4:5 Portrait coordinates (1080x1350)
    A = [
        (870, 680, 0.90),   # S0: Beside chart
        (540, 1050, 0.95),  # S1: Below chart
        (540, 950, 1.05),   # S2: Below ALGENZA logo
        (540, 1080, 0.85),  # S3: Below cards
        (540, 1100, 0.80),  # S4: Below pipeline
        (540, 1100, 0.80),  # S5: Below risk panel
        (540, 1100, 0.80),  # S6: Below package
        (540, 1040, 0.95),  # S7: Below metrics
        (540, 940, 1.15)    # S8: Centered below CTA
    ]
else:
    # 16:9 Landscape coordinates (1920x1080)
    A = [
        (1560, 560, 1.0),   # S0: Beside chart
        (300, 600, 0.9),    # S1: Left of chart
        (300, 600, 0.9),    # S2: Left of logo
        (290, 650, 0.8),    # S3: Left of cards
        (270, 700, 0.7),    # S4: Left of pipeline
        (270, 700, 0.7),    # S5: Left of risk
        (270, 700, 0.7),    # S6: Left of files
        (300, 640, 0.85),   # S7: Left of metrics
        (540, 560, 1.1)     # S8: Left of CTA
    ]

# 6. Algenza Mascot - Blueprint Construction (Scene 0)
def build(c, t, x, y, s):
    g = sm(t, 0.2, 0.5) * (1 - sm(t, 2.0, 2.5))
    bp = sm(t, 0.3, 1.7)
    if g > 0:
        c.drawLine(x - 200 * s, y, x + 200 * s, y, dash(0.5 * g))
        c.drawLine(x, y - 230 * s, x, y + 230 * s, dash(0.5 * g))
        for yy in (-105, 105):
            c.drawLine(x - 200 * s, y + yy * s, x + 200 * s, y + yy * s, dash(0.25 * g))
        for ex in (-22, 22):
            c.drawCircle(x + ex * s, y - 37 * s, 24 * s, dash(0.6 * g))
        c.drawArc(skia.Rect.MakeLTRB(x - 160 * s, y - 160 * s, x + 160 * s, y + 160 * s), -120, 320 * bp, False, P(G, 0.35 * g, 2))
        ang = math.radians(-120 + 320 * bp)
        c.drawLine(x, y, x + 160 * s * math.cos(ang), y + 160 * s * math.sin(ang), P(MU, 0.5 * g, 2))
        c.drawCircle(x, y, 5, P(WH, g))
    pa = skia.Path()
    pa.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(x - 64 * s, y - 105 * s, x + 64 * s, y + 105 * s), 26 * s, 26 * s))
    pm = skia.PathMeasure(pa, False)
    L = pm.getLength()
    seg = skia.Path()
    pm.getSegment(0, L * bp, seg, True)
    c.drawPath(seg, GL(G, 0.6 * g, 8))
    c.drawPath(seg, P(G, 1, 4))
    if g > 0:
        q = g * sm(bp, 0.05, 0.3)
        for hx, hy in ((-64, -105), (64, -105), (64, 105), (-64, 105)):
            px, py = x + hx * s, y + hy * s
            c.drawLine(px - 34 * s, py, px + 34 * s, py, P(G, 0.7 * q, 2))
            rr(c, px - 6, py - 6, px + 6, py + 6, 1, P(WH, q))
            c.drawCircle(px - 34 * s, py, 5, P(G, q))
            c.drawCircle(px + 34 * s, py, 5, P(G, q))
    c.drawLine(x, y - 105 * s, x, y - 105 * s - 60 * s * bp, P(G, 1, 7 * s))
    c.drawLine(x, y + 105 * s, x, y + 105 * s + 55 * s * bp, P(G, 1, 7 * s))
    return sm(t, 1.6, 2.1)

# 7. Algenza Mascot - Body, Expressions & Motion
def body(c, t, m, x, y, s, i):
    wave = i in (2, NS - 1)
    happy = i in (2, 7, NS - 1) and not any(ST[j] - 0.05 <= t <= ST[j] + D[j] + 0.1 for j in range(NS))
    worried = i == 1
    lk = -4 if x > W / 2 else 4
    
    # 1. Soft radial energy aura
    c.drawCircle(x, y, 150 * s, GL(G, 0.14, 0, 40))
    
    # 2. Cyber Signal Antenna (Wick)
    c.drawLine(x, y - 105 * s, x, y - 165 * s, P(G, 1, 6 * s))
    # Dual angled sensor antenna prongs
    c.drawLine(x - 18 * s, y - 130 * s, x - 32 * s, y - 158 * s, P(LN, 1, 3 * s))
    c.drawLine(x + 18 * s, y - 130 * s, x + 32 * s, y - 158 * s, P(LN, 1, 3 * s))
    
    signal_pulse = 0.5 + 0.5 * math.sin(t * 8)
    c.drawCircle(x, y - 165 * s, 15 * s, GL(CYAN, 0.45 * signal_pulse, 0, 12))
    c.drawCircle(x, y - 165 * s, 8 * s, P(CYAN if signal_pulse > 0.4 else G))
    
    # Bottom stabilizer wick & thruster fin
    c.drawLine(x, y + 105 * s, x, y + 155 * s, P(G, 1, 6 * s))
    c.drawLine(x - 20 * s, y + 120 * s, x - 34 * s, y + 144 * s, P(LN, 1, 3 * s))
    c.drawLine(x + 20 * s, y + 120 * s, x + 34 * s, y + 144 * s, P(LN, 1, 3 * s))
    c.drawCircle(x, y + 155 * s, 7 * s, GL(CYAN, 0.5, 0, 10))
    c.drawCircle(x, y + 155 * s, 5 * s, P(WH))
    
    # 3. Dynamic Articulated Arms
    # Left pointing arm
    al = 3.35 if i == 0 else 2.25 - 0.9 * m
    c.drawCircle(x - 62 * s, y + 25 * s, 9 * s, P('#162720'))
    c.drawLine(x - 62 * s, y + 25 * s, x - 62 * s + 72 * s * math.cos(al), y + 25 * s + 72 * s * math.sin(al), P(G, 1, 9 * s))
    c.drawCircle(x - 62 * s + 72 * s * math.cos(al), y + 25 * s + 72 * s * math.sin(al), 8 * s, P(WH))
    
    # Right waving arm
    an = (-1.0 + 0.4 * math.sin(t * 9)) if wave else (-0.35 + 0.08 * math.sin(t * 3)) if 3 <= i <= 7 else 0.95
    c.drawCircle(x + 62 * s, y + 25 * s, 9 * s, P('#162720'))
    c.drawLine(x + 62 * s, y + 25 * s, x + 62 * s + 62 * s * math.cos(an), y + 25 * s + 62 * s * math.sin(an), P(G, 1, 9 * s))
    c.drawCircle(x + 62 * s + 62 * s * math.cos(an), y + 25 * s + 62 * s * math.sin(an), 8 * s, P(WH))
    
    # 4. Algenza Mascot Main Body (Emerald Capsule)
    rr(c, x - 64 * s, y - 105 * s, x + 64 * s, y + 105 * s, 26 * s, P(G))
    
    # Dark titanium side shoulder armor plates
    rr(c, x - 64 * s, y - 85 * s, x - 50 * s, y + 65 * s, 8 * s, P('#10221A'))
    rr(c, x + 50 * s, y - 85 * s, x + 64 * s, y + 65 * s, 8 * s, P('#10221A'))
    c.drawLine(x - 50 * s, y - 75 * s, x - 50 * s, y + 55 * s, P(CYAN, 0.6, 2 * s))
    c.drawLine(x + 50 * s, y - 75 * s, x + 50 * s, y + 55 * s, P(CYAN, 0.6, 2 * s))
    
    # Tech ear sensor nodes (Algenza tech styling)
    rr(c, x - 74 * s, y - 38 * s, x - 62 * s, y + 16 * s, 6 * s, P('#0E1F18'))
    rr(c, x + 62 * s, y - 38 * s, x + 74 * s, y + 16 * s, 6 * s, P('#0E1F18'))
    c.drawCircle(x - 68 * s, y - 11 * s, 4 * s, P(CYAN))
    c.drawCircle(x + 68 * s, y - 11 * s, 4 * s, P(CYAN))
    
    # Cyber Visor housing in upper chassis
    rr(c, x - 46 * s, y - 62 * s, x + 46 * s, y - 12 * s, 14 * s, P('#0B1713'))
    rr(c, x - 46 * s, y - 62 * s, x + 46 * s, y - 12 * s, 14 * s, P(LN, 0.8, 1.5 * s))
    
    # Gloss reflection highlight
    rr(c, x - 42 * s, y - 92 * s, x - 30 * s, y + 20 * s, 6 * s, P('#FFFFFF', 0.22))
    
    # 5. Expressive Digital Eyes & Blinking
    eh = 0.12 if (t % 3.7) < 0.13 else 1.0
    for ex in (-22, 22):
        cx_eye = x + ex * s
        cy_eye = y - 37 * s
        if happy:
            c.drawArc(skia.Rect.MakeLTRB(cx_eye - 13 * s, cy_eye - 9 * s, cx_eye + 13 * s, cy_eye + 15 * s), 200, 140, False, P('#FFFFFF', 1, 5 * s))
            continue
        c.drawOval(skia.Rect.MakeLTRB(cx_eye - 14 * s, cy_eye - 16 * s * eh, cx_eye + 14 * s, cy_eye + 16 * s * eh), P('#FFFFFF'))
        if eh > 0.5:
            c.drawCircle(cx_eye + lk * s, cy_eye + 2 * s, 6.5 * s, P(DK))
            c.drawCircle(cx_eye + lk * s + 3 * s, cy_eye - 2 * s, 2.5 * s, P('#FFFFFF'))
        if worried:
            c.drawLine(cx_eye - 12 * s, cy_eye - 25 * s - (ex > 0) * 6 * s, cx_eye + 12 * s, cy_eye - 25 * s - (ex < 0) * 6 * s, P(CYAN, 1, 4 * s))
            
    # Sweat drop when worried
    if worried:
        dy = (t * 40) % 30
        c.drawCircle(x + 68 * s, y - 76 * s + dy * s, 7 * s, P('#7DD3FC', 0.9))
        
    # 6. Audio-Reactive Talking Mouth / Smile
    mh = (5 + 32 * m) * s
    mw = (34 - 8 * m) * s
    r = min(mw, mh) / 2
    if happy:
        c.drawArc(skia.Rect.MakeLTRB(x - 18 * s, y + 2 * s, x + 18 * s, y + 30 * s), 20, 140, False, P(DK, 1, 5 * s))
    else:
        rr(c, x - mw / 2, y + 14 * s, x + mw / 2, y + 14 * s + mh, r, P(DK))
        
    # 7. Algenza Chest Chevron Insignia
    ap = skia.Path()
    ap.moveTo(x - 14 * s, y + 78 * s)
    ap.lineTo(x, y + 56 * s)
    ap.lineTo(x + 14 * s, y + 78 * s)
    c.drawPath(ap, GL(CYAN, 0.4, 6 * s))
    c.drawPath(ap, P('#FFFFFF', 0.9, 4 * s))
    c.drawCircle(x, y + 68 * s, 4 * s, P(CYAN))

def char(c, t, m):
    if t < 0.25: return
    i = max(k for k in range(NS) if t >= SS[k])
    if i == 0:
        x, y, s = A[0]
    else:
        g = sm(t, SS[i], SS[i] + 0.7)
        a, b = A[i - 1], A[i]
        x, y, s = [a[j] + (b[j] - a[j]) * g for j in range(3)]
        
    # Gentle idle breathing bob
    y += math.sin(t * 2.4) * 6 * s * sm(t, 2.3, 2.8)
    
    if i == 0 and t < 2.5:
        f = build(c, t, x, y, s)
        if f <= 0.01: return
        c.saveLayerAlpha(None, int(f * 255))
        body(c, t, m, x, y, s, i)
        c.restore()
        return
    body(c, t, m, x, y, s, i)

# 8. Individual Scene Renders
def s0(c, t):
    if IS_LAND:
        base_x, base_y, span_y, cand_step = 180, 820, 430, 64
        tx_x, tx_y = 140, 200
        head_sz, sub_sz = 70, 32
    elif IS_VERT:
        base_x, base_y, span_y, cand_step = 80, 980, 360, 58
        tx_x, tx_y = 70, 260
        head_sz, sub_sz = 56, 26
    elif IS_SQUARE:
        base_x, base_y, span_y, cand_step = 65, 660, 280, 45
        tx_x, tx_y = 60, 170
        head_sz, sub_sz = 52, 24
    else:  # IS_PORT (4:5)
        base_x, base_y, span_y, cand_step = 70, 780, 320, 46
        tx_x, tx_y = 70, 220
        head_sz, sub_sz = 54, 26
    
    for k, (o, h, l, cc) in enumerate(CAND):
        g = sm(t, cand_t(k), cand_t(k) + 0.25)
        if g <= 0: continue
        x = base_x + k * cand_step
        col = G if cc >= o else RD
        c.drawLine(x, CY(h, base_y, span_y), x, CY(l, base_y, span_y), P(col, g, 3))
        yo = CY(o, base_y, span_y)
        yc = yo + (CY(cc, base_y, span_y) - yo) * g
        rr(c, x - 13, min(yo, yc), x + 13, max(yo, yc) + 2, 4, P(col))
        
    g = sm(t, 2.4, 3.2)
    n = int(16 * g)
    if n > 1:
        pa = skia.Path()
        pa.moveTo(base_x, CY(CAND[0][3], base_y, span_y))
        for k in range(1, n):
            pa.lineTo(base_x + k * cand_step, CY(CAND[k][3], base_y, span_y))
        c.drawPath(pa, GL('#A7F3C9', 0.5, 8))
        c.drawPath(pa, P('#A7F3C9', 0.8, 3))
        
    head(c, "You have a strategy.", tx_x, tx_y, 1, head_sz)
    sub(c, "It works when you trade it by hand.", tx_x, tx_y + (58 if IS_LAND else 46), sm(t, 2.6, 3.1), sub_sz)

def pf(w):
    return 600 - (80 * math.sin(w * .006) + 45 * math.sin(w * .017 + 1) + 18 * math.sin(w * .05))

def s1(c, t):
    u = t - SS[1]
    if IS_LAND:
        tx_x, tx_y = 520, 190
        head_sz, sub_sz = 64, 32
        pan_l, pan_t, pan_r, pan_b = 520, 300, 1800, 900
        wave_y_offset = 0
    elif IS_VERT:
        tx_x, tx_y = 70, 260
        head_sz, sub_sz = 54, 26
        pan_l, pan_t, pan_r, pan_b = 70, 360, 1010, 960
        wave_y_offset = 80
    elif IS_SQUARE:
        tx_x, tx_y = 60, 170
        head_sz, sub_sz = 52, 24
        pan_l, pan_t, pan_r, pan_b = 60, 270, 1020, 650
        wave_y_offset = 140
    else:  # 4:5
        tx_x, tx_y = 70, 220
        head_sz, sub_sz = 54, 26
        pan_l, pan_t, pan_r, pan_b = 70, 340, 1010, 830
        wave_y_offset = 60
    
    head(c, "Markets never sleep.", tx_x, tx_y, 1, head_sz)
    sub(c, "You miss entries. Emotions take over.", tx_x, tx_y + (55 if IS_LAND else 44), 1, sub_sz)
    panel(c, pan_l, pan_t, pan_r, pan_b)
    
    sc = u * 260
    pa = skia.Path()
    step_x = 6
    x_range = range(pan_l + 20, pan_r - 19, step_x)
    for j, sx in enumerate(x_range):
        (pa.moveTo if j == 0 else pa.lineTo)(sx, pf(sx + sc) - wave_y_offset)
    c.drawPath(pa, GL(G, 0.5, 10))
    c.drawPath(pa, P(G, 1, 3))
    
    for k in range(int(sc / 380) - 1, int((sc + 1300) / 380) + 2):
        wx = k * 380 + 190
        sx = wx - sc
        if not (pan_l + 50 < sx < pan_r - 40): continue
        py = pf(wx) - wave_y_offset
        if sx < (pan_l + pan_r) * 0.55:
            c.drawCircle(sx, py, 9, P(RD))
            rr(c, sx - 62, py - 66, sx + 62, py - 24, 10, P(RD, 0.9))
            tx(c, "MISSED", sx, py - 36, 'bb', 22, '#FFFFFF', 1, 'c')
        else:
            c.drawCircle(sx, py, 9, P(G))
            tx(c, "ENTRY", sx, py - 30, 'bb', 20, G, 1, 'c')
            
    # Analog clock
    cx = pan_r - 65
    cy = pan_t - (100 if IS_LAND else 60)
    c.drawCircle(cx, cy, 36, P(WH, 0.8, 4))
    for ang, ln in ((u * 7, 26), (u * 0.6, 17)):
        c.drawLine(cx, cy, cx + ln * math.sin(ang), cy - ln * math.cos(ang), P(WH, 0.9, 4))

def s2(c, t):
    u = t - SS[2]
    if IS_LAND:
        cx, cy, font_sz, sub_sz = 1160, 500, 170, 36
    elif IS_VERT:
        cx, cy, font_sz, sub_sz = 540, 620, 128, 28
    elif IS_SQUARE:
        cx, cy, font_sz, sub_sz = 540, 410, 120, 26
    else:  # 4:5
        cx, cy, font_sz, sub_sz = 540, 520, 128, 28
        
    f = F('lg', font_sz)
    wT = f.measureText("AL")
    wN = f.measureText("GENZA")
    w = wT + wN
    x0 = cx - w / 2
    gT = sm(u, 0.15, 0.75)
    gN = sm(u, 0.4, 0.95)
    
    c.drawOval(skia.Rect.MakeLTRB(cx - w * 0.6, cy - 190, cx + w * 0.6, cy + 60), GL(G, 0.14 * gT, 0, 70))
    gp = GL(G, 0.55 * gT, 0, 20)
    c.drawString("AL", x0 - (1 - gT) * 90, cy, f, gp)
    c.drawString("AL", x0 - (1 - gT) * 90, cy, f, P(G, gT))
    c.drawString("GENZA", x0 + wT + (1 - gN) * 90, cy, f, P(WH, gN))
    
    g = sm(u, 0.8, 1.5)
    if g > 0:
        c.drawLine(x0, cy + 50, x0 + w * g, cy + 50, GL(G, 0.6, 10))
        c.drawLine(x0, cy + 50, x0 + w * g, cy + 50, P(G, 1, 4))
        c.drawCircle(x0 + w * g, cy + 50, 7, P(WH, 1 - sm(u, 1.4, 1.7)))
    tx(c, "Trading strategies  \u2192  automated systems", cx, cy + (125 if IS_LAND else 105), 'b', sub_sz, MU, sm(u, 1.4, 1.9), 'c')

CARDS = [("MT4 / MT5", "Expert Advisors"), ("IBKR API", "Interactive Brokers"), ("Crypto Bots", "Exchange APIs")]
def s3(c, t):
    tx_x = 540 if IS_LAND else 70 if not IS_SQUARE else 60
    tx_y = 215 if IS_LAND else 260 if not IS_SQUARE else 170
    head(c, "Built for your platform.", tx_x, tx_y, 1, 64 if IS_LAND else 52)
    
    for k, (ti, su) in enumerate(CARDS):
        g = sm(t, card_t(k), card_t(k) + 0.5)
        if g <= 0: continue
        
        if IS_LAND:
            x = 540 + k * 420
            y = 310 + (1 - g) * 60
            card_w, card_h = 380, 400
        elif IS_SQUARE:
            x = 65 + k * 330
            y = 270 + (1 - g) * 40
            card_w, card_h = 290, 360
        elif IS_PORT:
            x = 70
            y = 330 + k * 220 + (1 - g) * 40
            card_w, card_h = 940, 190
        else:  # 9:16
            x = 70
            y = 360 + k * 230 + (1 - g) * 40
            card_w, card_h = 940, 200
            
        panel(c, x, y, x + card_w, y + card_h, g)
        rr(c, x, y, x + card_w, y + 6, 3, P(G, g))
        
        if IS_LAND or IS_SQUARE:
            ix = x + card_w / 2
            iy = y + 140 if IS_LAND else y + 120
        else:
            ix = x + 100
            iy = y + 100
        
        if k == 0:
            for dx, h, col in ((-44, 60, G), (0, 40, RD), (44, 80, G)):
                c.drawLine(ix + dx, iy - h / 2 - 14, ix + dx, iy + h / 2 + 14, P(col, g, 3))
                rr(c, ix + dx - 12, iy - h / 2, ix + dx + 12, iy + h / 2, 4, P(col, g))
        elif k == 1:
            tx(c, "</>", ix, iy + 22, 'mb', 74 if IS_LAND else 56, G, g, 'c')
        else:
            for dx in (-36, 0, 36):
                c.drawCircle(ix + dx, iy, 32, P(PN, g))
                c.drawCircle(ix + dx, iy, 32, P(G, g, 4))
            tx(c, "$", ix + 36, iy + 12, 'bb', 34, G, g, 'c')
            
        if IS_LAND or IS_SQUARE:
            tx(c, ti, ix, y + (280 if IS_LAND else 240), 'h', 36 if IS_LAND else 28, WH, g, 'c')
            tx(c, su, ix, y + (330 if IS_LAND else 285), 'b', 22 if IS_LAND else 18, MU, g, 'c')
        else:
            tx(c, ti, x + 240, y + 80, 'h', 40, WH, g, 'l')
            tx(c, su, x + 240, y + 130, 'b', 24, MU, g, 'l')

KW = {'def', 'if', 'and'}
def colmap(l):
    cols = [WH] * len(l)
    for mm in re.finditer(r"[A-Za-z_][A-Za-z_0-9]*|\d+(\.\d+)?", l):
        w = mm.group(0)
        col = None
        if w in KW: col = G
        elif w[0].isdigit(): col = '#FBBF24'
        elif mm.end() < len(l) and l[mm.end()] == '(': col = '#7DD3FC'
        if col: cols[mm.start():mm.end()] = [col] * (mm.end() - mm.start())
    return cols

NL = ["RULES", "CODE", "BACKTEST", "BROKER API", "LIVE"]
CODE = ["def on_bar(bar):", "    if rsi(bar, 14) < 30 and bar.close > ema(bar, 200):", "        size = risk.position_size(pct=1.0)", "        broker.buy(bar.symbol, size, sl=stop, tp=target)"]
CMAP = [colmap(l) for l in CODE]
LOG = [("09:31:02", "BUY", "XAUUSD", "1.50", "FILLED"), ("10:47:15", "SELL", "XAUUSD", "1.50", "FILLED"), ("11:02:40", "BUY", "EURUSD", "2.00", "FILLED")]

def s4(c, t):
    tx_x = 520 if IS_LAND else 70 if not IS_SQUARE else 60
    tx_y = 200 if IS_LAND else 260 if not IS_SQUARE else 170
    head(c, "From rules to live execution.", tx_x, tx_y, 1, 64 if IS_LAND else 50)
    
    if IS_LAND:
        pan_l, pan_r, pan_t, pan_b = 520, 1800, 450, 920
        NY = 320
        NX = [620 + k * 280 for k in range(5)]
    elif IS_SQUARE:
        pan_l, pan_r, pan_t, pan_b = 60, 1020, 350, 660
        NY = 265
        NX = [140 + k * 200 for k in range(5)]
    elif IS_PORT:
        pan_l, pan_r, pan_t, pan_b = 70, 1010, 460, 960
        NY = 340
        NX = [140 + k * 200 for k in range(5)]
    else:  # 9:16
        pan_l, pan_r, pan_t, pan_b = 70, 1010, 480, 1020
        NY = 360
        NX = [170 + k * 180 for k in range(5)]
    
    for k in range(4):
        c.drawLine(NX[k] + 32, NY, NX[k + 1] - 32, NY, P(LN, 1, 4))
        g = sm(t, node_t(k) + 0.2, node_t(k + 1))
        if g > 0:
            c.drawLine(NX[k] + 32, NY, NX[k] + 32 + (NX[k + 1] - NX[k] - 64) * g, NY, GL(G, 0.6, 8))
            c.drawLine(NX[k] + 32, NY, NX[k] + 32 + (NX[k + 1] - NX[k] - 64) * g, NY, P(G, 1, 4))
            
    st = -1
    for k in range(5):
        c.drawCircle(NX[k], NY, 30, P(PN))
        c.drawCircle(NX[k], NY, 30, P(LN, 1, 3))
        a = cl((t - node_t(k)) / 0.35)
        if a > 0:
            st = k
            c.drawCircle(NX[k], NY, 40 * bo(a), GL(G, 0.45, 0, 14))
            c.drawCircle(NX[k], NY, 30 * bo(a), P(G))
        tx(c, str(k + 1), NX[k], NY + 10, 'bb', 26, DK if a > 0.5 else MU, 1, 'c')
        tx(c, NL[k], NX[k], NY + 70, 'bb', 20 if IS_LAND else 15, WH if a > 0.5 else MU, 1, 'c')
        
    panel(c, pan_l, pan_t, pan_r, pan_b)
    if st < 0: return
    
    u = t - node_t(st)
    a = sm(u, 0, 0.3)
    X = pan_l + 45
    Y = pan_t + (70 if IS_LAND else 55)
    
    if st == 0:
        for j, (kw, rest) in enumerate((("IF  ", "RSI(14) < 30  AND  close > EMA(200)"), ("THEN", "BUY  \u00b7  risk 1% of account"), ("EXIT", "at 2R  or  trailing stop"))):
            b = a * sm(u, j * 0.25, j * 0.25 + 0.3)
            tx(c, kw, X, Y + 50 + j * 75, 'mb', 34 if IS_LAND else 24, G, b)
            tx(c, rest, X + (130 if IS_LAND else 85), Y + 50 + j * 75, 'm', 34 if IS_LAND else 24, WH, b)
    elif st == 1:
        n = int(u * 60)
        for j, l in enumerate(CODE):
            s = l[:max(0, n)]
            n -= len(l)
            tx(c, str(j + 1), X, Y + 35 + j * 54, 'm', 26 if IS_LAND else 20, MU, a)
            cw = F('m', 26 if IS_LAND else 20).measureText('M')
            q = 0
            while q < len(s):
                e = q
                while e < len(s) and CMAP[j][e] == CMAP[j][q]: e += 1
                tx(c, s[q:e], X + 45 + q * cw, Y + 35 + j * 54, 'm', 26 if IS_LAND else 20, CMAP[j][q], a)
                q = e
    elif st == 2:
        tx(c, "Backtest \u00b7 equity curve", X, Y + 5, 'bb', 22, MU, a)
        L_eq, R_eq, T_eq, B_eq = X + 20, pan_r - 50, Y + 35, pan_b - 35
        c.drawLine(L_eq, B_eq, R_eq, B_eq, P(LN, a, 2))
        c.drawLine(L_eq, T_eq, L_eq, B_eq, P(LN, a, 2))
        n = max(2, int(len(EQ) * sm(u, 0, 1.6)))
        pa = skia.Path()
        fa = skia.Path()
        fa.moveTo(L_eq, B_eq)
        for j in range(n):
            x = L_eq + (R_eq - L_eq) * j / (len(EQ) - 1)
            y = B_eq - 10 - EQ[j] * (B_eq - T_eq - 25)
            (pa.moveTo if j == 0 else pa.lineTo)(x, y)
            fa.lineTo(x, y)
        fa.lineTo(L_eq + (R_eq - L_eq) * (n - 1) / (len(EQ) - 1), B_eq)
        fa.close()
        c.drawPath(fa, P(G, 0.12 * a))
        c.drawPath(pa, GL(G, 0.5 * a, 10))
        c.drawPath(pa, P(G, a, 4))
    elif st == 3:
        for j, l in enumerate(("> connecting to broker API ...", "> authenticated (Interactive Brokers / MT5)", "> market data stream      OK", "> order routing           OK")):
            tx(c, l, X, Y + 45 + j * 60, 'm', 28 if IS_LAND else 22, WH if j else MU, a * sm(u, j * 0.3, j * 0.3 + 0.2))
        pu = 0.6 + 0.4 * math.sin(t * 6)
        conn_x = pan_r - (240 if IS_LAND else 180)
        c.drawCircle(conn_x, Y + 35, 10, P(G, a * pu))
        tx(c, "CONNECTED", conn_x + 20, Y + 44, 'bb', 24 if IS_LAND else 18, G, a)
    else:
        step_col = 180 if IS_LAND else 125
        cols = [X + k * step_col for k in range(5)]
        for j, h in enumerate(("TIME", "SIDE", "SYMBOL", "QTY", "STATUS")):
            tx(c, h, cols[j], Y + 20, 'bb', 22 if IS_LAND else 16, MU, a)
        for r_idx, row in enumerate(LOG):
            b = a * sm(u, 0.2 + r_idx * 0.4, 0.4 + r_idx * 0.4)
            for j, v in enumerate(row):
                tx(c, v, cols[j], Y + 75 + r_idx * 65, 'm', 28 if IS_LAND else 20, (G if v == "BUY" else RD if v == "SELL" else G if v == "FILLED" else WH), b)
        pu = 0.6 + 0.4 * math.sin(t * 6)
        live_x = pan_r - (200 if IS_LAND else 150)
        c.drawCircle(live_x, Y + 10, 10, P(G, a * pu))
        tx(c, "LIVE", live_x + 20, Y + 18, 'bb', 24 if IS_LAND else 18, G, a)

def s5(c, t):
    u = t - SS[5]
    tx_x = 520 if IS_LAND else 70 if not IS_SQUARE else 60
    tx_y = 200 if IS_LAND else 260 if not IS_SQUARE else 170
    head(c, "Risk management, built in.", tx_x, tx_y, 1, 64 if IS_LAND else 50)
    
    if IS_LAND:
        pan1_l, pan1_r, pan1_t, pan1_b = 520, 1120, 290, 900
        X0, Y0, X1, Y1 = 1250, 280, 1690, 925
    elif IS_SQUARE:
        pan1_l, pan1_r, pan1_t, pan1_b = 60, 520, 270, 740
        X0, Y0, X1, Y1 = 550, 260, 1020, 750
    elif IS_PORT:
        pan1_l, pan1_r, pan1_t, pan1_b = 70, 1010, 340, 640
        X0, Y0, X1, Y1 = 140, 680, 940, 1080
    else:  # 9:16
        pan1_l, pan1_r, pan1_t, pan1_b = 70, 1010, 360, 720
        X0, Y0, X1, Y1 = 140, 780, 940, 1260
        
    panel(c, pan1_l, pan1_t, pan1_r, pan1_b)
    
    for k, (lb, v, fr) in enumerate((("Max daily loss", "2%", 0.4), ("Risk per trade", "1%", 0.25), ("Max open trades", "3", 0.6))):
        y = pan1_t + 90 + k * (180 if IS_LAND else 130 if IS_SQUARE else 105)
        tx(c, lb, pan1_l + 40, y, 'bb', 28 if IS_LAND else 22, WH)
        tx(c, v, pan1_r - 40, y, 'mb', 30 if IS_LAND else 24, G, 1, 'r')
        rr(c, pan1_l + 40, y + 35, pan1_r - 40, y + 48, 6, P(LN))
        g = sm(u, 0.3 + k * 0.25, 1.2 + k * 0.25)
        if g > 0:
            rr(c, pan1_l + 40, y + 35, pan1_l + 40 + (pan1_r - pan1_l - 80) * fr * g, y + 48, 6, P(G))
            
    # Phone mockup (Telegram & Discord alerts)
    mx = (X0 + X1) / 2
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(X0, Y0, X1, Y1), 45, 45), GL(G, 0.16, 0, 26))
    rr(c, X0, Y0, X1, Y1, 45, P('#05080A'))
    rr(c, X0, Y0, X1, Y1, 45, P('#2E4038', 1, 4))
    rr(c, mx - 55, Y0 + 16, mx + 55, Y0 + 40, 12, P('#000000'))
    tx(c, "9:41", X0 + 35, Y0 + 38, 'bb', 18, WH)
    tx(c, "Alerts", X0 + 35, Y0 + 95, 'h', 30, WH)
    
    for k, (app, col, l1, l2) in enumerate((("Telegram", "#2AABEE", "BUY  XAUUSD  @ 2704.66", "SL 2697.50  \u00b7  TP 2718.00"), ("Discord", "#5865F2", "Prop Target Reached", "Daily drawdown locked safely"))):
        g = sm(t, alert_t(k), alert_t(k) + 0.45)
        if g <= 0: continue
        x = X0 + 20
        y = Y0 + 130 + k * (180 if not IS_SQUARE else 160) - (1 - g) * 40
        panel(c, x, y, X1 - 20, y + (160 if not IS_SQUARE else 145), g)
        c.drawCircle(x + 35, y + 36, 12, P(col, g))
        tx(c, app, x + 56, y + 44, 'bb', 22 if not IS_SQUARE else 18, WH, g)
        tx(c, "now", X1 - 38, y + 44, 'b', 18 if not IS_SQUARE else 15, MU, g, 'r')
        tx(c, l1, x + 24, y + 92, 'bb', 22 if not IS_SQUARE else 17, WH, g)
        tx(c, l2, x + 24, y + 128, 'b', 19 if not IS_SQUARE else 15, MU, g)

FILES = ["ApexScalper_XAUUSD.mq5", "TitanGridEngine.mq5", "RiskGuardian_PropPass.py", "FIX_Bridge.cpp", "README_Setup.md"]
CHK = ["Clean, modular source code", "Full documentation", "Dedicated engineering support"]

def s6(c, t):
    u = t - SS[6]
    tx_x = 520 if IS_LAND else 70 if not IS_SQUARE else 60
    tx_y = 200 if IS_LAND else 260 if not IS_SQUARE else 170
    head(c, "No black box.", tx_x, tx_y, 1, 76 if IS_LAND else 56)
    sub(c, "You own everything we build.", tx_x, tx_y + (58 if IS_LAND else 46), 1, 32 if IS_LAND else 24)
    
    if IS_LAND:
        pan_l, pan_r, pan_t, pan_b = 520, 1080, 310, 880
        chk_x = 1200
        chk_y_base, chk_step = 440, 160
    elif IS_SQUARE:
        pan_l, pan_r, pan_t, pan_b = 60, 540, 270, 740
        chk_x = 590
        chk_y_base, chk_step = 370, 130
    elif IS_PORT:
        pan_l, pan_r, pan_t, pan_b = 70, 1010, 340, 760
        chk_x = 120
        chk_y_base, chk_step = 840, 120
    else:  # 9:16
        pan_l, pan_r, pan_t, pan_b = 70, 1010, 360, 820
        chk_x = 120
        chk_y_base, chk_step = 920, 140
        
    panel(c, pan_l, pan_t, pan_r, pan_b)
    tx(c, "ALGENZA_DEPLOYMENT_PACKAGE /", pan_l + 40, pan_t + 55, 'mb', 24 if IS_LAND else 18, MU)
    
    for k, fn in enumerate(FILES):
        a = sm(u, 0.3 + k * 0.15, 0.6 + k * 0.15)
        y = pan_t + (115 if IS_LAND else 105) + k * (80 if IS_LAND else 65)
        rr(c, pan_l + 45, y - 26, pan_l + 70, y + 4, 4, P(G, a, 3))
        tx(c, fn, pan_l + 90, y, 'm', 28 if IS_LAND else 19, WH, a)
        
    for k, s in enumerate(CHK):
        y = chk_y_base + k * chk_step
        g = cl((t - check_t(k)) / 0.4)
        c.drawCircle(chk_x, y, 28, P(LN, 1, 3))
        if g > 0:
            c.drawCircle(chk_x, y, 28 * bo(g), P(G))
            pa = skia.Path()
            pa.moveTo(chk_x - 12, y)
            pa.lineTo(chk_x - 3, y + 10)
            pa.lineTo(chk_x + 14, y - 10)
            c.drawPath(pa, P(DK, g, 5))
        tx(c, s, chk_x + 50, y + 11, 'bb', 34 if IS_LAND else 24, WH, 0.35 + 0.65 * g)

def star(c, cx, cy, R, p):
    pa = skia.Path()
    for j in range(10):
        rad = R if j % 2 == 0 else R * 0.45
        an = -math.pi / 2 + j * math.pi / 5
        (pa.moveTo if j == 0 else pa.lineTo)(cx + rad * math.cos(an), cy + rad * math.sin(an))
    pa.close()
    c.drawPath(pa, p)

def s7(c, t):
    u = t - SS[7]
    tx_x = 520 if IS_LAND else 70 if not IS_SQUARE else 60
    tx_y = 200 if IS_LAND else 260 if not IS_SQUARE else 170
    head(c, "Proven in production.", tx_x, tx_y, 1, 64 if IS_LAND else 50)
    
    for k in range(2):
        g = sm(u, 0.35 + k * 0.4, 0.85 + k * 0.4)
        if g <= 0: continue
        
        if IS_LAND:
            x = 540 + k * 640
            y = 310 + (1 - g) * 50
            card_w, card_h = 560, 440
        elif IS_SQUARE:
            x = 60 + k * 500
            y = 280 + (1 - g) * 40
            card_w, card_h = 460, 400
        elif IS_PORT:
            x = 70
            y = 340 + k * 370 + (1 - g) * 40
            card_w, card_h = 940, 330
        else:  # 9:16
            x = 70
            y = 380 + k * 450 + (1 - g) * 50
            card_w, card_h = 940, 400
            
        cx = x + card_w / 2
        panel(c, x, y, x + card_w, y + card_h, g)
        rr(c, x, y, x + card_w, y + 6, 3, P(G, g))
        v = sm(u, 0.4 + k * 0.4, 1.8 + k * 0.4)
        
        if k == 0:
            tx(c, f"{int(round(200 * v))}+", cx, y + (220 if IS_LAND else 200), 'h', 130 if IS_LAND else 100, G, g, 'c')
            tx(c, "algorithms delivered", cx, y + (320 if IS_LAND else 290), 'b', 32 if IS_LAND else 24, MU, g, 'c')
        else:
            tx(c, f"{4.9 * v:.1f}", cx, y + (200 if IS_LAND else 180), 'h', 120 if IS_LAND else 95, G, g, 'c')
            for j in range(5):
                q = sm(u, 1.0 + j * 0.12, 1.3 + j * 0.12)
                star(c, cx - 100 + j * 50, y + (260 if IS_LAND else 240), 22, P(G, g * (0.25 + 0.75 * q)))
            tx(c, "client rating", cx, y + (330 if IS_LAND else 300), 'b', 32 if IS_LAND else 24, MU, g, 'c')

def s8(c, t):
    u = t - SS[8]
    a = sm(u, 0.1, 0.5)
    
    if IS_LAND:
        cx, cy = 800, 370
        head_y, sub_y = 470, 535
        btn_cx, btn_cy = 1030, 640
        btn_w = 460
    elif IS_SQUARE:
        cx, cy = 540, 310
        head_y, sub_y = 410, 475
        btn_cx, btn_cy = 540, 580
        btn_w = 480
    elif IS_PORT:
        cx, cy = 540, 400
        head_y, sub_y = 510, 580
        btn_cx, btn_cy = 540, 700
        btn_w = 540
    else:  # 9:16
        cx, cy = 540, 480
        head_y, sub_y = 590, 660
        btn_cx, btn_cy = 540, 780
        btn_w = 620
        
    logo(c, cx, cy, 52 if IS_LAND else 44, a, glow=0.4, al='l' if IS_LAND else 'c')
    head(c, "Deploy your algorithmic edge.", cx if IS_LAND else 70, head_y, sm(u, 0.2, 0.7), 64 if IS_LAND else 48)
    sub(c, "Visit algenza.com or request a custom build.", cx if IS_LAND else 70, sub_y, sm(u, 0.5, 1.0), 34 if IS_LAND else 25)
    
    g = bo((t - BTN_T) / 0.5)
    if g > 0.01:
        hw, hh = btn_w / 2 * g, 44 * g
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(btn_cx - hw, btn_cy - hh, btn_cx + hw, btn_cy + hh), hh, hh), GL(G, 0.55, 0, 22))
        rr(c, btn_cx - hw, btn_cy - hh, btn_cx + hw, btn_cy + hh, hh, P(G))
        lab = "algenza.com"
        tx(c, lab, btn_cx, btn_cy + 13, 'bb', int(38 * g) + 1, DK, 1, 'c')

SC = [s0, s1, s2, s3, s4, s5, s6, s7, s8]

# 9. Subtitle Wrapping & Display
def wrap(s, n):
    out = []
    cur = ""
    for w in s.split():
        if len(cur) + len(w) + 1 > n and cur:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    out.append(cur)
    return out

def subs(c, t):
    wrap_limit = 72 if IS_LAND else 46 if IS_SQUARE else 42
    font_sz = 30 if IS_LAND else 24
    sub_cx = W / 2
    sub_y_base = (H - 35) if IS_LAND else (H - 45) if IS_SQUARE else (H - 70) if IS_PORT else (H - 140)
    
    for i, s0_ in enumerate(ST):
        e = s0_ + D[i]
        if s0_ - 0.1 <= t <= e + 0.3:
            a = min(sm(t, s0_ - 0.1, s0_ + 0.15), 1 - sm(t, e + 0.05, e + 0.3))
            ls = wrap(LINES[i], wrap_limit)
            f = F('b', font_sz)
            mw = max(f.measureText(l) for l in ls)
            y0 = sub_y_base - (len(ls) - 1) * 36
            rr(c, sub_cx - mw / 2 - 24, y0 - 34, sub_cx + mw / 2 + 24, sub_y_base + 16, 12, P('#000000', 0.55 * a))
            for j, l in enumerate(ls):
                tx(c, l, sub_cx, y0 + j * 36, 'b', font_sz, WH, a, 'c')

def wm(c, t):
    a = sm(t, SS[2] + 1.5, SS[2] + 2.2) * (1 - sm(t, SS[NS - 1], SS[NS - 1] + 0.4))
    if a <= 0: return
    logo(c, 56 if IS_LAND else 50, 76 if IS_LAND else 90 if not IS_VERT else 110, 32 if IS_LAND else 26, a)

# Floating ambient particles
_pr = np.random.default_rng(11)
PT = list(zip(_pr.uniform(0, W, 70), _pr.uniform(0, H, 70), _pr.uniform(8, 30, 70), _pr.uniform(1.2, 3.2, 70), _pr.uniform(0, 6.28, 70)))

def parts(c, t):
    for x0, y0, sp, sz, ph in PT:
        y = (y0 - t * sp) % H
        x = x0 + math.sin(t * 0.5 + ph) * 18
        c.drawCircle(x, y, sz, P(G, 0.10 + 0.18 * (0.5 + 0.5 * math.sin(t * 2 + ph))))

def sweep(c, t):
    for i in range(1, NS):
        u = (t - (SS[i] - 0.15)) / 0.55
        if 0 < u < 1:
            x = -100 + u * (W + 200)
            c.drawRect(skia.Rect.MakeLTRB(x - 40, 0, x + 40, H), GL(G, 0.18, 0, 30))
            c.drawRect(skia.Rect.MakeLTRB(x - 1.5, 0, x + 1.5, H), P('#A7F3C9', 0.7))

SURF = skia.Surface(W, H)

def frame(fi):
    t = fi / FPS
    c = SURF.getCanvas()
    c.drawImage(BG, 0, 0)
    parts(c, t)
    CUR[0] = t
    
    for i in range(NS):
        if not (SS[i] - 0.01 <= t <= SE[i] + 0.06): continue
        a = 1.0 if i == 0 else sm(t, SS[i], SS[i] + 0.35)
        CUR[1] = SS[i] + (2.0 if i == 0 else 0)
        if i < NS - 1: a *= 1 - sm(t, SE[i] - 0.3, SE[i] + 0.05)
        if a <= 0.002: continue
        
        c.saveLayerAlpha(None, int(a * 255))
        # Subtle slow cinematic Ken Burns push-in
        z = 1 + 0.035 * cl((t - SS[i]) / (SE[i] - SS[i]))
        c.translate(W / 2, H / 2 + (1 - a) * 18)
        c.scale(z, z)
        c.translate(-W / 2, -H / 2)
        SC[i](c, t)
        c.restore()
        
    sweep(c, t)
    wm(c, t)
    char(c, t, float(MO[min(fi, len(MO) - 1)]))
    subs(c, t)
    return SURF

if __name__ == '__main__':
    clean_mode = MODE.replace(':', 'x')
    if len(sys.argv) > 1 and sys.argv[1] == 'still':
        for ts in sys.argv[2:]:
            out_name = f'still_{clean_mode}_{ts}.png'
            frame(int(float(ts) * FPS)).makeImageSnapshot().save(out_name, skia.kPNG)
            print(f"Saved {out_name}")
    else:
        w = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        out_seg = sys.argv[4] if len(sys.argv) > 4 else f'seg_{clean_mode}_{w}.mp4'
        NF = int(END * FPS)
        a = NF * w // n
        b = NF * (w + 1) // n
        
        cmd = [
            FFMPEG_EXE, '-y', '-loglevel', 'error',
            '-f', 'rawvideo', '-pix_fmt', 'rgba',
            '-s', f'{W}x{H}', '-r', str(FPS),
            '-i', '-',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
            '-pix_fmt', 'yuv420p', '-g', '60',
            '-bf', '0', '-flags', '+cgop',
            out_seg
        ]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for fi in range(a, b):
            p.stdin.write(frame(fi).makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType).tobytes())
        p.stdin.close()
        p.wait()
        print(f"seg {w} done", flush=True)
