"""
ALGENZA Video Engine - Universal Multi-Format Frame Renderer
Renders 60fps explainer video for algenza.com in 16:9, 9:16, or 1:1 aspect ratios.
Streams frames directly into FFmpeg for parallel or full video encoding.
"""

import os
import sys
import math
import re
import subprocess
import io

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from tl import *
from engine.config import (
    COLORS, BRAND_NAME, BRAND_TAG, BRAND_SLOGAN, BRAND_DISPLAY_URL,
    WHATSAPP_NUMBER, FOUNDER_NAME, FOUNDER_ROLE, PRODUCTS, METRICS, hex_to_rgb, hex_to_rgba
)

# 1. Video Resolution & Aspect Ratio Setup
ASPECT = os.environ.get("ASPECT", "16:9").strip()
if ASPECT == "9:16":
    W, H = 1080, 1920
    IS_VERTICAL = True
elif ASPECT == "1:1":
    W, H = 1080, 1080
    IS_VERTICAL = False
else:
    W, H = 1920, 1080
    IS_VERTICAL = False

FPS = 60

# Discover FFmpeg executable
try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"

# 2. Font Loading with Robust System Fallbacks
FONT_CACHE = {}

def get_font_paths():
    paths = []
    # Windows system fonts
    win_fonts = r"C:\Windows\Fonts"
    if os.path.exists(win_fonts):
        paths.append(win_fonts)
    # Local assets fonts
    local_fonts = os.path.join(os.path.dirname(__file__), "assets", "fonts")
    if os.path.exists(local_fonts):
        paths.append(local_fonts)
    # Linux system fonts
    for p in ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/msttcorefonts"]:
        if os.path.exists(p):
            paths.append(p)
    return paths

FONT_PATHS = get_font_paths()

def find_font_file(filenames):
    for base in FONT_PATHS:
        for fn in filenames:
            p = os.path.join(base, fn)
            if os.path.exists(p):
                return p
    return None

FONT_FILES = {
    "h": find_font_file(["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]),
    "b": find_font_file(["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"]),
    "bb": find_font_file(["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]),
    "m": find_font_file(["consolab.ttf", "consola.ttf", "DejaVuSansMono.ttf"]),
    "mb": find_font_file(["consolab.ttf", "DejaVuSansMono-Bold.ttf"]),
    "lg": find_font_file(["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"])
}

def get_font(key, size):
    size = int(size)
    cache_key = (key, size)
    if cache_key in FONT_CACHE:
        return FONT_CACHE[cache_key]
    
    font_path = FONT_FILES.get(key)
    if font_path and os.path.exists(font_path):
        try:
            f = ImageFont.truetype(font_path, size)
            FONT_CACHE[cache_key] = f
            return f
        except Exception:
            pass
    try:
        f = ImageFont.load_default()
        FONT_CACHE[cache_key] = f
        return f
    except Exception:
        return None

# 3. Easing & Math Interpolation Utilities
def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def ease_out(x):
    x = clamp(x)
    return 1.0 - (1.0 - x) ** 3

def smooth_step(t, a, b):
    if b <= a:
        return 1.0 if t >= b else 0.0
    return ease_out((t - a) / (b - a))

def bounce_out(x):
    x = clamp(x)
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * ((x - 1.0) ** 3) + c1 * ((x - 1.0) ** 2)

# 4. Drawing Helpers
TEAL_RGB = hex_to_rgb(COLORS["teal"])
ROSE_RGB = hex_to_rgb(COLORS["rose"])
GOLD_RGB = hex_to_rgb(COLORS["gold"])
GREEN_RGB = hex_to_rgb(COLORS["green"])
RED_RGB = hex_to_rgb(COLORS["red"])
BLUE_RGB = hex_to_rgb(COLORS["blue"])
TEXT_RGB = hex_to_rgb(COLORS["text"])
MUTED_RGB = hex_to_rgb(COLORS["muted"])
PANEL_RGB = hex_to_rgb(COLORS["panel"])
BORDER_RGB = hex_to_rgb(COLORS["border"])

def draw_round_rect(draw, bbox, radius, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = bbox
    r = int(radius)
    if r * 2 > (x1 - x0):
        r = int((x1 - x0) / 2)
    if r * 2 > (y1 - y0):
        r = int((y1 - y0) / 2)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill, outline=outline, width=width)

def draw_text(draw, s, x, y, font_key, size, color=TEXT_RGB, alpha=1.0, align="l"):
    font = get_font(font_key, size)
    bbox = draw.textbbox((0, 0), s, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    
    if align == "c":
        x = x - w / 2.0
    elif align == "r":
        x = x - w
        
    c = color
    if isinstance(color, str):
        c = hex_to_rgb(color)
    if alpha < 0.999:
        c = (c[0], c[1], c[2], int(clamp(alpha) * 255))
        
    draw.text((x, y), s, font=font, fill=c)
    return w, h

def draw_algenza_logo_mark(draw, cx, cy, size=100, alpha=1.0, glow=False):
    """Draws the authentic ALGENZA dual-polygon geometric chevron mark"""
    s = size / 100.0
    a = int(clamp(alpha) * 255)
    
    # Polygon 1 (Teal)
    pts1 = [
        (cx + (30.77 - 50.0) * s, cy + (45.55 - 50.0) * s),
        (cx + (43.12 - 50.0) * s, cy + (69.50 - 50.0) * s),
        (cx + (26.34 - 50.0) * s, cy + (100.0 - 50.0) * s),
        (cx + (0.000 - 50.0) * s, cy + (100.0 - 50.0) * s)
    ]
    
    # Polygon 2 (Rose)
    pts2 = [
        (cx + (49.42 - 50.0) * s, cy + (0.000 - 50.0) * s),
        (cx + (100.0 - 50.0) * s, cy + (100.0 - 50.0) * s),
        (cx + (71.79 - 50.0) * s, cy + (100.0 - 50.0) * s),
        (cx + (36.13 - 50.0) * s, cy + (26.50 - 50.0) * s)
    ]
    
    draw.polygon(pts1, fill=(TEAL_RGB[0], TEAL_RGB[1], TEAL_RGB[2], a))
    draw.polygon(pts2, fill=(ROSE_RGB[0], ROSE_RGB[1], ROSE_RGB[2], a))

def draw_card_panel(draw, bbox, alpha=1.0, border_color=BORDER_RGB, border_width=2):
    a = clamp(alpha)
    fill_c = (PANEL_RGB[0], PANEL_RGB[1], PANEL_RGB[2], int(235 * a))
    border_c = (border_color[0], border_color[1], border_color[2], int(255 * a))
    draw_round_rect(draw, bbox, radius=18, fill=fill_c, outline=border_c, width=border_width)

# 5. Background Generation (Precomputed Static Layer with Glow Grid)
def make_background():
    img = Image.new("RGBA", (W, H), hex_to_rgba(COLORS["bg"]))
    d = ImageDraw.Draw(img)
    
    # Grid lines
    grid_gap = 64
    grid_color = (20, 32, 50, 90)
    for x in range(0, W + 1, grid_gap):
        d.line([(x, 0), (x, H)], fill=grid_color, width=1)
    for y in range(0, H + 1, grid_gap):
        d.line([(0, y), (W, y)], fill=grid_color, width=1)
        
    # Subtle radial teal & rose ambient lighting
    # Top-right glow
    glow_teal = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d_gt = ImageDraw.Draw(glow_teal)
    center_tr = (int(W * 0.75), int(H * 0.35))
    d_gt.ellipse([center_tr[0] - 500, center_tr[1] - 500, center_tr[0] + 500, center_tr[1] + 500],
                 fill=(112, 224, 214, 28))
    glow_teal = glow_teal.filter(ImageFilter.GaussianBlur(140))
    
    # Bottom-left glow
    glow_rose = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d_gr = ImageDraw.Draw(glow_rose)
    center_bl = (int(W * 0.25), int(H * 0.75))
    d_gr.ellipse([center_bl[0] - 450, center_bl[1] - 450, center_bl[0] + 450, center_bl[1] + 450],
                 fill=(244, 144, 151, 20))
    glow_rose = glow_rose.filter(ImageFilter.GaussianBlur(130))
    
    img = Image.alpha_composite(img, glow_teal)
    img = Image.alpha_composite(img, glow_rose)
    return img

BACKGROUND_LAYER = make_background()

# 6. Candlestick & Market Data Generation
rng = np.random.default_rng(101)
CANDLES = []
p = 2680.0  # Gold spot price simulation
for k in range(16):
    o = p
    c = p + float(rng.normal(1.8, 2.4))
    h = max(o, c) + abs(float(rng.normal(0, 1.2)))
    l = min(o, c) - abs(float(rng.normal(0, 1.2)))
    CANDLES.append((o, h, l, c))
    p = c

PRICE_MIN = min(x[2] for x in CANDLES) - 2.0
PRICE_MAX = max(x[1] for x in CANDLES) + 2.0

def price_to_y(val, top=280, bottom=780):
    return bottom - (val - PRICE_MIN) / (PRICE_MAX - PRICE_MIN) * (bottom - top)

# 7. Ambient Floating Quant Particles
_pr = np.random.default_rng(77)
PARTICLES = list(zip(
    _pr.uniform(0, W, 65),
    _pr.uniform(0, H, 65),
    _pr.uniform(14, 38, 65),      # speed
    _pr.uniform(2, 6, 65),        # radius
    _pr.uniform(0, 2 * math.pi, 65),
    _pr.choice([TEAL_RGB, ROSE_RGB, BLUE_RGB, GOLD_RGB], 65)
))

def draw_particles(draw, t):
    for x0, y0, sp, r, ph, col in PARTICLES:
        y = (y0 - t * sp) % H
        x = (x0 + math.sin(t * 0.4 + ph) * 20.0) % W
        alpha = int((0.15 + 0.35 * (0.5 + 0.5 * math.sin(t * 2.5 + ph))) * 255)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(col[0], col[1], col[2], alpha))

# 8. Load Lip-sync Data
try:
    MOUTH = np.load("mouth.npy")
except Exception:
    MOUTH = np.zeros(10)

def get_mouth_val(t):
    idx = int(t * FPS)
    if idx < len(MOUTH):
        return float(MOUTH[idx])
    return 0.0

# 9. Animated Cyber-Quant Sentinel Character & HUD
def draw_quant_sentinel(draw, t, mouth_val, x, y, scale=1.0, scene_idx=0):
    """
    Renders ALGENZA's signature institutional Quant Sentinel / AI Trader Avatar.
    Features audio-reactive glowing visor, holographic rings, and circuit lines.
    """
    s = scale
    m = clamp(mouth_val)
    
    # Ambient holographic ring around sentinel
    ring_r = int(140 * s)
    pulse = 1.0 + 0.05 * math.sin(t * 4.0)
    draw.ellipse([x - ring_r * pulse, y - ring_r * pulse, x + ring_r * pulse, y + ring_r * pulse],
                 outline=(TEAL_RGB[0], TEAL_RGB[1], TEAL_RGB[2], 40), width=int(2 * s))
    
    # Shoulders & Institutional Jacket
    shoulder_w = int(130 * s)
    shoulder_h = int(90 * s)
    draw_round_rect(draw, [x - shoulder_w, y + int(45 * s), x + shoulder_w, y + int(45 * s) + shoulder_h],
                    radius=int(22 * s), fill=(PANEL_RGB[0], PANEL_RGB[1], PANEL_RGB[2], 250),
                    outline=(BORDER_RGB[0], BORDER_RGB[1], BORDER_RGB[2], 255), width=int(3 * s))
    
    # Signature ALGENZA Tie / Core polygon badge
    draw_algenza_logo_mark(draw, x, y + int(75 * s), size=int(34 * s), alpha=0.95)
    
    # Head & Mask
    head_w = int(80 * s)
    head_h = int(95 * s)
    head_box = [x - head_w, y - head_h, x + head_w, y + int(40 * s)]
    draw_round_rect(draw, head_box, radius=int(28 * s),
                    fill=(COLORS["bg_alt"] if isinstance(COLORS["bg_alt"], tuple) else hex_to_rgb(COLORS["bg_alt"])),
                    outline=(BORDER_RGB[0], BORDER_RGB[1], BORDER_RGB[2], 255), width=int(3 * s))
    
    # Cybernetic Glowing Visor (Eyes / Holographic Display)
    visor_w = int(62 * s)
    visor_h = int(22 * s)
    visor_y = y - int(25 * s)
    visor_box = [x - visor_w, visor_y - visor_h, x + visor_w, visor_y + visor_h]
    
    # Visor Glow & Fill
    draw_round_rect(draw, visor_box, radius=int(10 * s), fill=(10, 24, 38, 255),
                    outline=(TEAL_RGB[0], TEAL_RGB[1], TEAL_RGB[2], 255), width=int(2 * s))
    
    # Visor internal holographic scanline / waveform
    scan_x = x - int(50 * s)
    scan_w = int(100 * s)
    for k in range(9):
        bar_x = scan_x + k * (scan_w / 8.0)
        bar_h = int((6 + 18 * m * math.sin(k * 0.8 + t * 8.0) ** 2) * s)
        draw.line([(bar_x, visor_y - bar_h / 2), (bar_x, visor_y + bar_h / 2)],
                  fill=(TEAL_RGB[0], TEAL_RGB[1], TEAL_RGB[2], 230), width=int(2 * s))
                  
    # Audio-Reactive Mouth (Frequency Aperture)
    mouth_w = int((30 - 6 * m) * s)
    mouth_h = int((4 + 26 * m) * s)
    mouth_y = y + int(14 * s)
    draw_round_rect(draw, [x - mouth_w / 2, mouth_y, x + mouth_w / 2, mouth_y + mouth_h],
                    radius=int(max(2, min(mouth_w, mouth_h) / 2)),
                    fill=(ROSE_RGB[0], ROSE_RGB[1], ROSE_RGB[2], int(180 + 75 * m)))
                    
    # Dynamic Hand / Pointer
    # In scenes 0, 3, 4, 7 pointing towards data; in scene 2 & 8 waving/welcoming
    arm_angle = -0.7 + 0.15 * math.sin(t * 3.0) if scene_idx in (2, 8) else 0.5 + 0.08 * math.sin(t * 2.0)
    arm_x = x + int(70 * s)
    arm_y = y + int(50 * s)
    end_x = arm_x + int(60 * s * math.cos(arm_angle))
    end_y = arm_y + int(60 * s * math.sin(arm_angle))
    draw.line([(arm_x, arm_y), (end_x, end_y)],
              fill=(TEAL_RGB[0], TEAL_RGB[1], TEAL_RGB[2], 240), width=int(7 * s))
    draw.ellipse([end_x - int(7 * s), end_y - int(7 * s), end_x + int(7 * s), end_y + int(7 * s)],
                 fill=TEXT_RGB)

# 10. The 9 Dedicated Scenes for ALGENZA
def scene_0(draw, t):
    """Scene 0: Candlestick Chart - Gold XAUUSD Breakdown"""
    draw_text(draw, "You have a proven strategy.", 120 if not IS_VERTICAL else 60,
              140 if not IS_VERTICAL else 180, "h", 64 if not IS_VERTICAL else 54, TEXT_RGB)
    draw_text(draw, "It works when you execute it by hand on Gold & Forex.", 120 if not IS_VERTICAL else 60,
              215 if not IS_VERTICAL else 245, "b", 30 if not IS_VERTICAL else 26, MUTED_RGB)
              
    chart_left = 120 if not IS_VERTICAL else 50
    chart_right = 1150 if not IS_VERTICAL else W - 50
    chart_top = 290 if not IS_VERTICAL else 340
    chart_bottom = 880 if not IS_VERTICAL else 1150
    
    # Chart Panel
    draw_card_panel(draw, [chart_left, chart_top, chart_right, chart_bottom], alpha=0.9)
    draw_text(draw, "XAUUSD  \u00b7  1-MINUTE INSTITUTIONAL TICK DATA", chart_left + 30, chart_top + 25, "mb", 22, GOLD_RGB)
    
    # Draw Candlesticks progressively
    num_candles = len(CANDLES)
    candle_w = (chart_right - chart_left - 80) / num_candles
    
    curve_pts = []
    for k, (o, h, l, c) in enumerate(CANDLES):
        t_cand = cand_t(k)
        g = smooth_step(t, t_cand, t_cand + 0.22)
        if g <= 0:
            continue
            
        cx = chart_left + 40 + k * candle_w + candle_w / 2.0
        col = GREEN_RGB if c >= o else RED_RGB
        
        yh = price_to_y(h, chart_top + 70, chart_bottom - 50)
        yl = price_to_y(l, chart_top + 70, chart_bottom - 50)
        yo = price_to_y(o, chart_top + 70, chart_bottom - 50)
        yc = yo + (price_to_y(c, chart_top + 70, chart_bottom - 50) - yo) * g
        
        # Wick
        draw.line([(cx, yh), (cx, yl)], fill=col, width=2)
        # Body
        body_top = min(yo, yc)
        body_bot = max(yo, yc)
        if body_bot - body_top < 2:
            body_bot = body_top + 2
        bw = max(4, candle_w * 0.6)
        draw_round_rect(draw, [cx - bw / 2, body_top, cx + bw / 2, body_bot], radius=3, fill=col)
        
        curve_pts.append((cx, yc))
        
    # Moving Average Curve
    if len(curve_pts) > 1:
        for j in range(len(curve_pts) - 1):
            draw.line([curve_pts[j], curve_pts[j + 1]], fill=(TEAL_RGB[0], TEAL_RGB[1], TEAL_RGB[2], 180), width=3)

def scene_1(draw, t):
    """Scene 1: The Dilemma - 24/7 Market Exhaustion & Missed Entries"""
    u = t - SS[1]
    draw_text(draw, "Markets never sleep.", 120 if not IS_VERTICAL else 60,
              140 if not IS_VERTICAL else 180, "h", 64 if not IS_VERTICAL else 54, TEXT_RGB)
    draw_text(draw, "You miss entries. Emotions take over. Drawdown hits.", 120 if not IS_VERTICAL else 60,
              215 if not IS_VERTICAL else 245, "b", 30 if not IS_VERTICAL else 26, MUTED_RGB)
              
    box_l = 120 if not IS_VERTICAL else 50
    box_r = 1250 if not IS_VERTICAL else W - 50
    box_t = 290 if not IS_VERTICAL else 340
    box_b = 880 if not IS_VERTICAL else 1150
    draw_card_panel(draw, [box_l, box_t, box_r, box_b], alpha=0.92)
    
    # Oscillating high-frequency price sine wave
    sc = u * 240.0
    pts = []
    for sx in range(int(box_l + 20), int(box_r - 20), 8):
        wx = sx + sc
        sy = (box_t + box_b) / 2.0 - (70 * math.sin(wx * 0.012) + 40 * math.sin(wx * 0.028) + 15 * math.sin(wx * 0.07))
        pts.append((sx, sy))
        
    for j in range(len(pts) - 1):
        draw.line([pts[j], pts[j + 1]], fill=TEAL_RGB, width=3)
        
    # Trigger Missed and Late Entry indicators
    for k in range(int(sc / 350) - 1, int((sc + 1200) / 350) + 2):
        wx = k * 350 + 175
        sx = wx - sc
        if not (box_l + 60 < sx < box_r - 60):
            continue
        sy = (box_t + box_b) / 2.0 - (70 * math.sin(wx * 0.012) + 40 * math.sin(wx * 0.028) + 15 * math.sin(wx * 0.07))
        
        if sx < (box_l + box_r) / 2.0 + 80:
            draw.ellipse([sx - 8, sy - 8, sx + 8, sy + 8], fill=RED_RGB)
            draw_card_panel(draw, [sx - 65, sy - 64, sx + 65, sy - 24], alpha=0.95, border_color=RED_RGB)
            draw_text(draw, "MISSED ENTRY", sx, sy - 52, "bb", 16, RED_RGB, align="c")
        else:
            draw.ellipse([sx - 8, sy - 8, sx + 8, sy + 8], fill=GREEN_RGB)
            draw_text(draw, "LATE CHASE", sx, sy - 30, "bb", 16, MUTED_RGB, align="c")
            
    # 24/7 Clock indicator
    cx_clk = box_r - 80
    cy_clk = box_t + 80
    draw.ellipse([cx_clk - 35, cy_clk - 35, cx_clk + 35, cy_clk + 35], outline=MUTED_RGB, width=3)
    hr_angle = u * 4.0
    draw.line([(cx_clk, cy_clk), (cx_clk + 22 * math.cos(hr_angle), cy_clk + 22 * math.sin(hr_angle))], fill=TEXT_RGB, width=3)
    draw_text(draw, "24/7 LIQUIDITY", cx_clk, cy_clk + 45, "mb", 16, MUTED_RGB, align="c")

def scene_2(draw, t):
    """Scene 2: ALGENZA Brand Reveal - Electric Shockwave & Logo Assembly"""
    u = t - SS[2]
    cx = W / 2.0
    cy = (H / 2.0) - (0 if not IS_VERTICAL else 140)
    
    g_mark = smooth_step(u, 0.15, 0.8)
    g_text = smooth_step(u, 0.45, 1.0)
    
    # Expanding shockwave rings
    if 0 < u < 1.8:
        for ring_idx in (1, 2):
            rad = int((u * 420.0 + ring_idx * 90) % 750)
            a_ring = int(max(0, 1.0 - rad / 750.0) * 120)
            draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad],
                         outline=(TEAL_RGB[0], TEAL_RGB[1], TEAL_RGB[2], a_ring), width=3)
                         
    # Main ALGENZA Logo Mark
    mark_size = int(140 * bounce_out(g_mark))
    draw_algenza_logo_mark(draw, cx, cy - 60, size=mark_size, alpha=g_mark)
    
    # Title Text "ALGENZA"
    draw_text(draw, BRAND_NAME, cx - 40, cy + 50, "h", 86, TEXT_RGB, alpha=g_text, align="c")
    
    # "PRO" Badge
    badge_w = 75
    badge_h = 36
    draw_round_rect(draw, [cx + 140, cy + 42, cx + 140 + badge_w, cy + 42 + badge_h],
                    radius=8, fill=(TEAL_RGB[0], TEAL_RGB[1], TEAL_RGB[2], int(40 * g_text)),
                    outline=(TEAL_RGB[0], TEAL_RGB[1], TEAL_RGB[2], int(255 * g_text)), width=2)
    draw_text(draw, BRAND_TAG, cx + 140 + badge_w / 2, cy + 48, "mb", 22, TEAL_RGB, alpha=g_text, align="c")
    
    # Slogan / Tagline
    draw_text(draw, BRAND_SLOGAN, cx, cy + 130, "b", 32, MUTED_RGB, alpha=smooth_step(u, 0.8, 1.4), align="c")
    draw_text(draw, "algenza.com  \u00b7  Lead Architect Muhammad Hassan", cx, cy + 180, "mb", 24, GOLD_RGB, alpha=smooth_step(u, 1.1, 1.7), align="c")

def scene_3(draw, t):
    """Scene 3: Flagship Products Showcase - Apex Scalper, Titan Grid, Prop Risk Guard"""
    draw_text(draw, "Engineered For Peak Performance.", 100 if not IS_VERTICAL else 50,
              120 if not IS_VERTICAL else 160, "h", 58 if not IS_VERTICAL else 48, TEXT_RGB)
    draw_text(draw, "Proprietary Expert Advisors built for MT5, FIX API & Prop Firms.", 100 if not IS_VERTICAL else 50,
              190 if not IS_VERTICAL else 225, "b", 28 if not IS_VERTICAL else 24, MUTED_RGB)
              
    num_cards = len(PRODUCTS)
    if not IS_VERTICAL:
        card_w = (W - 200 - (num_cards - 1) * 24) / num_cards
        card_h = 560
        y0 = 270
        for k, prod in enumerate(PRODUCTS):
            g = smooth_step(t, card_t(k), card_t(k) + 0.45)
            if g <= 0:
                continue
            x = 100 + k * (card_w + 24)
            y = y0 + (1.0 - g) * 50.0
            
            draw_card_panel(draw, [x, y, x + card_w, y + card_h], alpha=g, border_color=hex_to_rgb(prod["color"]))
            # Top color accent strip
            draw_round_rect(draw, [x, y, x + card_w, y + 8], radius=4, fill=hex_to_rgb(prod["color"]))
            
            # Badge
            draw_text(draw, prod["badge"].upper(), x + 24, y + 35, "mb", 18, hex_to_rgb(prod["color"]), alpha=g)
            # Title
            draw_text(draw, prod["name"], x + 24, y + 75, "h", 28, TEXT_RGB, alpha=g)
            # Tagline
            draw_text(draw, prod["tagline"], x + 24, y + 120, "mb", 18, GOLD_RGB if "Gold" in prod["tagline"] else TEAL_RGB, alpha=g)
            
            # Decorative Mini Diagram
            diag_y = y + 175
            if k == 0:  # Apex Scalper (Candles + Volatility)
                for c_idx in range(5):
                    cx_bar = x + 40 + c_idx * 50
                    draw.line([(cx_bar, diag_y + 10), (cx_bar, diag_y + 110)], fill=GREEN_RGB, width=2)
                    draw_round_rect(draw, [cx_bar - 12, diag_y + 30 + c_idx * 8, cx_bar + 12, diag_y + 80], radius=3, fill=GREEN_RGB)
                draw_text(draw, "+45.2 Pips (0.24ms)", x + card_w / 2, diag_y + 140, "mb", 20, GREEN_RGB, alpha=g, align="c")
            elif k == 1:  # Titan Grid (Multi-level grid lines)
                for gl in range(4):
                    draw.line([(x + 30, diag_y + 20 + gl * 28), (x + card_w - 30, diag_y + 20 + gl * 28)],
                              fill=TEAL_RGB, width=2)
                draw_text(draw, "Trailing Take-Profit", x + card_w / 2, diag_y + 140, "mb", 20, TEAL_RGB, alpha=g, align="c")
            elif k == 2:  # Prop Risk Guard (Shield icon & FTMO safe)
                cx_sh = x + card_w / 2
                cy_sh = diag_y + 60
                draw.ellipse([cx_sh - 45, cy_sh - 45, cx_sh + 45, cy_sh + 45], outline=GREEN_RGB, width=3)
                draw_text(draw, "100%", cx_sh, cy_sh - 12, "h", 26, GREEN_RGB, alpha=g, align="c")
                draw_text(draw, "FTMO / Prop Safe", cx_sh, diag_y + 140, "mb", 20, GREEN_RGB, alpha=g, align="c")
            else:  # FIX Bridge (Sub-ms sockets)
                draw_text(draw, "</> FIX API", x + card_w / 2, diag_y + 50, "h", 34, BLUE_RGB, alpha=g, align="c")
                draw_text(draw, "0.2ms Tick Latency", x + card_w / 2, diag_y + 140, "mb", 20, BLUE_RGB, alpha=g, align="c")
                
            # Description text
            words = prod["desc"].split()
            line_str = ""
            dy_desc = 0
            for w in words:
                if len(line_str) + len(w) > 28:
                    draw_text(draw, line_str, x + 24, y + 360 + dy_desc, "b", 19, MUTED_RGB, alpha=g)
                    line_str = w
                    dy_desc += 26
                else:
                    line_str += (" " if line_str else "") + w
            if line_str:
                draw_text(draw, line_str, x + 24, y + 360 + dy_desc, "b", 19, MUTED_RGB, alpha=g)
    else:
        # Vertical 9:16 layout: stacked 2x2 or 4 rows
        row_h = 190
        for k, prod in enumerate(PRODUCTS):
            g = smooth_step(t, card_t(k), card_t(k) + 0.45)
            if g <= 0: continue
            y = 300 + k * (row_h + 16)
            draw_card_panel(draw, [50, y, W - 50, y + row_h], alpha=g, border_color=hex_to_rgb(prod["color"]))
            draw_text(draw, prod["name"], 80, y + 25, "h", 32, TEXT_RGB, alpha=g)
            draw_text(draw, prod["tagline"], 80, y + 68, "mb", 22, hex_to_rgb(prod["color"]), alpha=g)
            draw_text(draw, prod["desc"], 80, y + 110, "b", 20, MUTED_RGB, alpha=g)

def scene_4(draw, t):
    """Scene 4: The 5-Step Quant Pipeline - Rules -> Code -> Backtest -> FIX API -> Live"""
    u = t - SS[4]
    draw_text(draw, "From Quantitative Rules to Live Execution.", 100 if not IS_VERTICAL else 50,
              120 if not IS_VERTICAL else 160, "h", 58 if not IS_VERTICAL else 46, TEXT_RGB)
              
    NODES = ["RULES", "MQL5 CODE", "BACKTEST", "BROKER API", "LIVE PROFITS"]
    num_nodes = len(NODES)
    
    # Progress node dots along horizontal line
    start_x = 180 if not IS_VERTICAL else 80
    end_x = W - 180 if not IS_VERTICAL else W - 80
    node_y = 230 if not IS_VERTICAL else 260
    
    step_w = (end_x - start_x) / (num_nodes - 1)
    
    # Connecting pipeline track
    draw.line([(start_x, node_y), (end_x, node_y)], fill=BORDER_RGB, width=4)
    
    active_idx = 0
    for k in range(num_nodes):
        nx = start_x + k * step_w
        t_n = node_t(k)
        is_active = (t >= t_n)
        if is_active:
            active_idx = k
            
        circ_col = TEAL_RGB if is_active else BORDER_RGB
        glow_rad = int(32 * bounce_out(clamp((t - t_n) / 0.35))) if is_active else 20
        
        draw.ellipse([nx - glow_rad, node_y - glow_rad, nx + glow_rad, node_y + glow_rad],
                     fill=circ_col, outline=TEXT_RGB if is_active else BORDER_RGB, width=2)
        draw_text(draw, str(k + 1), nx, node_y - 12, "mb", 22, COLORS["dark"] if is_active else MUTED_RGB, align="c")
        draw_text(draw, NODES[k], nx, node_y + 40, "mb", 18 if not IS_VERTICAL else 15,
                  TEXT_RGB if is_active else MUTED_RGB, align="c")
                  
    # Active Node Detail Display Box
    box_l = 100 if not IS_VERTICAL else 50
    box_r = W - 100 if not IS_VERTICAL else W - 50
    box_t = 340 if not IS_VERTICAL else 370
    box_b = 920 if not IS_VERTICAL else 1250
    draw_card_panel(draw, [box_l, box_t, box_r, box_b], alpha=0.95)
    
    # Content depends on active node
    if active_idx == 0:  # Rules
        draw_text(draw, "// STRATEGY RULE SPECIFICATION", box_l + 50, box_t + 50, "mb", 26, TEAL_RGB)
        rules = [
            ("RULE 1:", "XAUUSD Tick Volatility Filter > 1.8 ATR"),
            ("RULE 2:", "Micro-Liquidity Sweep Detection @ High/Low"),
            ("RULE 3:", "Instant Dynamic Stop-Loss = 15 Pips Hard Fixed"),
            ("RULE 4:", "Trailing Break-Even Lock at +10 Pips Profit")
        ]
        for r_i, (tag, val) in enumerate(rules):
            draw_text(draw, tag, box_l + 50, box_t + 130 + r_i * 80, "h", 28, GOLD_RGB)
            draw_text(draw, val, box_l + 200, box_t + 130 + r_i * 80, "m", 28, TEXT_RGB)
            
    elif active_idx == 1:  # MQL5 Code
        draw_text(draw, "// COMPILED MQL5 & PYTHON 3.12 KERNEL", box_l + 50, box_t + 50, "mb", 26, TEAL_RGB)
        code_lines = [
            "void OnTick() {",
            "    if (VolatilityFilter.Check() && Account.DailyLoss() < 2.0) {",
            "        double lot = RiskEngine.CalculateLot(risk_pct=1.0);",
            "        trade.PositionOpen(_Symbol, ORDER_TYPE_BUY, lot, ask, sl, tp);",
            "        TelegramAlert.Send('Apex Scalper: BUY Filled @ ' + DoubleToString(ask));",
            "    }",
            "}"
        ]
        for c_i, cl in enumerate(code_lines):
            col_l = GOLD_RGB if "OnTick" in cl or "void" in cl else GREEN_RGB if "BUY" in cl else TEXT_RGB
            draw_text(draw, f"{c_i+1:02d}   {cl}", box_l + 50, box_t + 110 + c_i * 55, "m", 25, col_l)
            
    elif active_idx == 2:  # Backtest Equity Curve
        draw_text(draw, "99.9% REAL TICK BACKTEST  \u00b7  MONTE CARLO VERIFIED", box_l + 50, box_t + 40, "mb", 26, GREEN_RGB)
        # Skyrocketing equity curve
        chart_x0 = box_l + 80
        chart_x1 = box_r - 80
        chart_y0 = box_b - 60
        chart_y1 = box_t + 120
        draw.line([(chart_x0, chart_y0), (chart_x1, chart_y0)], fill=BORDER_RGB, width=2)
        draw.line([(chart_x0, chart_y1), (chart_x0, chart_y0)], fill=BORDER_RGB, width=2)
        
        eq_pts = []
        n_pts = 60
        for j in range(n_pts):
            gx = chart_x0 + (chart_x1 - chart_x0) * (j / float(n_pts - 1))
            gy = chart_y0 - (chart_y0 - chart_y1) * (0.85 * (j / float(n_pts - 1)) ** 1.35 + 0.04 * math.sin(j * 0.7))
            eq_pts.append((gx, gy))
            
        for j in range(len(eq_pts) - 1):
            draw.line([eq_pts[j], eq_pts[j + 1]], fill=GREEN_RGB, width=4)
        draw_text(draw, "PROFIT FACTOR: 3.42  \u00b7  MAX DRAWDOWN: 2.1%", box_l + 80, box_t + 85, "h", 30, TEXT_RGB)
        
    elif active_idx == 3:  # Broker API
        draw_text(draw, "SUB-MILLISECOND FIX 4.4 API BRIDGE", box_l + 50, box_t + 50, "mb", 26, BLUE_RGB)
        broker_logs = [
            "> Initializing FIX Protocol 4.4 Session ... [OK]",
            "> Authenticating Broker Handshake (Interactive Brokers / MT5) ... [AUTHENTICATED]",
            "> Raw Market Depth L2 Streaming ... [0.22ms Latency]",
            "> Zero-Slippage Execution Engine ... [ARMED]"
        ]
        for b_i, bl in enumerate(broker_logs):
            draw_text(draw, bl, box_l + 50, box_t + 130 + b_i * 70, "m", 26, TEAL_RGB if "OK" in bl or "ARMED" in bl else TEXT_RGB)
            
    else:  # Live Profits
        draw_text(draw, "LIVE EXECUTION FEED  \u00b7  VERIFIED PROP FIRM AUDIT", box_l + 50, box_t + 40, "mb", 26, GREEN_RGB)
        orders = [
            ("09:31:02", "BUY", "XAUUSD", "2.00 Lots", "FILLED", "+$920.00"),
            ("10:14:45", "BUY", "EURUSD", "5.00 Lots", "FILLED", "+$480.00"),
            ("11:05:12", "SELL", "US30", "1.50 Lots", "FILLED", "+$1,150.00"),
            ("12:22:30", "BUY", "XAUUSD", "2.00 Lots", "FILLED", "+$1,420.00")
        ]
        headers = ["TIME", "SIDE", "SYMBOL", "SIZE", "STATUS", "REALIZED PNL"]
        col_xs = [box_l + 50, box_l + 200, box_l + 320, box_l + 470, box_l + 650, box_l + 820 if not IS_VERTICAL else box_l + 650]
        
        for h_i, h in enumerate(headers if not IS_VERTICAL else headers[:5]):
            draw_text(draw, h, col_xs[h_i], box_t + 100, "mb", 22, MUTED_RGB)
            
        for o_i, row in enumerate(orders):
            for r_j, val in enumerate(row if not IS_VERTICAL else row[:5]):
                col_val = GREEN_RGB if val in ("BUY", "FILLED") or "+" in val else RED_RGB if val == "SELL" else TEXT_RGB
                draw_text(draw, val, col_xs[r_j], box_t + 160 + o_i * 65, "m", 24, col_val)

def scene_5(draw, t):
    """Scene 5: Prop-Firm Risk Guardians & Live Telegram/Discord Alerts"""
    u = t - SS[5]
    draw_text(draw, "Prop-Firm Risk Guardians Built-In.", 100 if not IS_VERTICAL else 50,
              120 if not IS_VERTICAL else 160, "h", 58 if not IS_VERTICAL else 46, TEXT_RGB)
    draw_text(draw, "100% compliant with FTMO, FundedNext, and institutional limits.", 100 if not IS_VERTICAL else 50,
              190 if not IS_VERTICAL else 225, "b", 28 if not IS_VERTICAL else 24, MUTED_RGB)
              
    left_w = 680 if not IS_VERTICAL else W - 100
    panel_y0 = 280
    panel_y1 = 920 if not IS_VERTICAL else 680
    
    # Left: Risk Limits Panel
    draw_card_panel(draw, [100 if not IS_VERTICAL else 50, panel_y0, 100 + left_w, panel_y1], alpha=0.92)
    draw_text(draw, "INSTITUTIONAL RISK CONTROLS", 140 if not IS_VERTICAL else 80, panel_y0 + 40, "mb", 24, TEAL_RGB)
    
    metrics = [
        ("Max Daily Loss Guardian", "2.0% Hard Lock", 0.40, GREEN_RGB),
        ("Max Overall Drawdown", "4.5% FTMO Cap", 0.35, GREEN_RGB),
        ("Dynamic Risk Per Trade", "1.0% Fixed", 0.25, GOLD_RGB),
        ("News Volatility Pause", "30min High Impact", 0.50, BLUE_RGB)
    ]
    
    for m_i, (title, val, pct, col) in enumerate(metrics):
        my = panel_y0 + 110 + m_i * 125
        draw_text(draw, title, 140 if not IS_VERTICAL else 80, my, "h", 26, TEXT_RGB)
        draw_text(draw, val, 100 + left_w - 40, my, "mb", 26, col, align="r")
        # Progress track
        track_x0 = 140 if not IS_VERTICAL else 80
        track_x1 = 100 + left_w - 40
        track_y = my + 45
        draw_round_rect(draw, [track_x0, track_y, track_x1, track_y + 14], radius=7, fill=BORDER_RGB)
        g_bar = smooth_step(u, 0.2 + m_i * 0.25, 0.9 + m_i * 0.25)
        fill_w = (track_x1 - track_x0) * pct * g_bar
        draw_round_rect(draw, [track_x0, track_y, track_x0 + fill_w, track_y + 14], radius=7, fill=col)
        
    # Right: Smartphone Mockup with Telegram Alerts
    if not IS_VERTICAL:
        phone_l = W - 680
        phone_r = W - 180
        phone_t = 270
        phone_b = 940
        draw_card_panel(draw, [phone_l, phone_t, phone_r, phone_b], alpha=0.98, border_color=BORDER_RGB)
        # Notch
        notch_cx = (phone_l + phone_r) / 2
        draw_round_rect(draw, [notch_cx - 60, phone_t + 14, notch_cx + 60, phone_t + 36], radius=11, fill=COLORS["dark"])
        draw_text(draw, "9:41", phone_l + 45, phone_t + 38, "mb", 18, TEXT_RGB)
        draw_text(draw, "INSTANT ALERTS", phone_l + 40, phone_t + 95, "h", 30, TEXT_RGB)
        
        # Telegram notification card 1
        card1_y = phone_t + 145
        draw_card_panel(draw, [phone_l + 25, card1_y, phone_r - 25, card1_y + 170], alpha=0.95, border_color=TEAL_RGB)
        draw.ellipse([phone_l + 45, card1_y + 20, phone_l + 75, card1_y + 50], fill=BLUE_RGB)
        draw_text(draw, "Telegram \u00b7 ALGENZA Bot", phone_l + 90, card1_y + 25, "mb", 20, TEXT_RGB)
        draw_text(draw, "now", phone_r - 45, card1_y + 25, "b", 18, MUTED_RGB, align="r")
        draw_text(draw, "Apex Scalper: BUY XAUUSD", phone_l + 45, card1_y + 75, "h", 22, GREEN_RGB)
        draw_text(draw, "Entry: 2684.50 | SL: 2679.50 | TP: 2705.00", phone_l + 45, card1_y + 115, "mb", 18, MUTED_RGB)
        
        # Discord notification card 2
        card2_y = card1_y + 195
        draw_card_panel(draw, [phone_l + 25, card2_y, phone_r - 25, card2_y + 170], alpha=0.95, border_color=GOLD_RGB)
        draw.ellipse([phone_l + 45, card2_y + 20, phone_l + 75, card2_y + 50], fill=(88, 101, 242))
        draw_text(draw, "Discord \u00b7 Prop Guard", phone_l + 90, card2_y + 25, "mb", 20, TEXT_RGB)
        draw_text(draw, "now", phone_r - 45, card2_y + 25, "b", 18, MUTED_RGB, align="r")
        draw_text(draw, "Trailing Take-Profit Executed", phone_l + 45, card2_y + 75, "h", 22, GOLD_RGB)
        draw_text(draw, "Realized: +$1,420.00 | FTMO Safe", phone_l + 45, card2_y + 115, "mb", 18, MUTED_RGB)

def scene_6(draw, t):
    """Scene 6: 100% Proprietary Code Ownership & Clean Architecture"""
    u = t - SS[6]
    draw_text(draw, "100% Proprietary Code Ownership.", 100 if not IS_VERTICAL else 50,
              120 if not IS_VERTICAL else 160, "h", 58 if not IS_VERTICAL else 46, TEXT_RGB)
    draw_text(draw, "No black box. You own every line of code, test report, and file.", 100 if not IS_VERTICAL else 50,
              190 if not IS_VERTICAL else 225, "b", 28 if not IS_VERTICAL else 24, MUTED_RGB)
              
    box_w = 640 if not IS_VERTICAL else W - 100
    draw_card_panel(draw, [100 if not IS_VERTICAL else 50, 280, 100 + box_w, 900 if not IS_VERTICAL else 680], alpha=0.92)
    draw_text(draw, "ALGENZA_DEPLOYMENT_PACKAGE /", 140 if not IS_VERTICAL else 80, 330, "mb", 22, MUTED_RGB)
    
    files = [
        ("ApexScalper_XAUUSD.mq5", "MQL5 High-Speed Scalper Source", GOLD_RGB),
        ("TitanGridEngine.mq5", "Dynamic Multi-Asset Hedging", TEAL_RGB),
        ("RiskGuardian_PropPass.py", "Hard Daily Loss Guard Module", GREEN_RGB),
        ("FIX_Protocol_Bridge.cpp", "Sub-Millisecond Execution Bridge", BLUE_RGB),
        ("RealTick_Backtest_99.9.pdf", "Verified Institutional Tick Audit", ROSE_RGB),
        ("README_Setup_Guide.md", "Full Documentation & Deployment Guide", TEXT_RGB)
    ]
    
    for f_i, (fname, fdesc, fcol) in enumerate(files):
        g = smooth_step(u, 0.2 + f_i * 0.18, 0.6 + f_i * 0.18)
        fy = 390 + f_i * 78
        draw_round_rect(draw, [140 if not IS_VERTICAL else 80, fy - 22, 168 if not IS_VERTICAL else 108, fy + 6], radius=4, fill=fcol)
        draw_text(draw, fname, 185 if not IS_VERTICAL else 125, fy - 18, "m", 24, TEXT_RGB, alpha=g)
        draw_text(draw, fdesc, 185 if not IS_VERTICAL else 125, fy + 14, "b", 17, MUTED_RGB, alpha=g)
        
    # Right: Institutional Trust Badges with Checkmarks
    right_x = W - 780 if not IS_VERTICAL else 80
    checklist = [
        ("Clean, Modular Source Code", "Fully commented & standardized architecture"),
        ("Institutional Documentation", "Complete video setup and parameter optimization"),
        ("Dedicated Engineering Support", "Direct strategy guidance with Muhammad Hassan")
    ]
    
    for c_i, (c_title, c_sub) in enumerate(checklist):
        g = smooth_step(u, 0.4 + c_i * 0.35, 0.9 + c_i * 0.35)
        cy = 380 + c_i * 170 if not IS_VERTICAL else 740 + c_i * 120
        # Checkmark Circle
        draw.ellipse([right_x - 30, cy - 30, right_x + 30, cy + 30], fill=GREEN_RGB)
        # Checkmark tick lines
        draw.line([(right_x - 14, cy - 2), (right_x - 4, cy + 10)], fill=COLORS["dark"], width=4)
        draw.line([(right_x - 4, cy + 10), (right_x + 14, cy - 10)], fill=COLORS["dark"], width=4)
        
        draw_text(draw, c_title, right_x + 55, cy - 16, "h", 32 if not IS_VERTICAL else 26, TEXT_RGB, alpha=g)
        draw_text(draw, c_sub, right_x + 55, cy + 24, "b", 22 if not IS_VERTICAL else 18, MUTED_RGB, alpha=g)

def scene_7(draw, t):
    """Scene 7: Verified Performance Metrics & Track Record"""
    u = t - SS[7]
    draw_text(draw, "Proven Track Record in Production.", 100 if not IS_VERTICAL else 50,
              120 if not IS_VERTICAL else 160, "h", 58 if not IS_VERTICAL else 46, TEXT_RGB)
    draw_text(draw, "Over 200+ funded traders and institutional funds rely on ALGENZA.", 100 if not IS_VERTICAL else 50,
              190 if not IS_VERTICAL else 225, "b", 28 if not IS_VERTICAL else 24, MUTED_RGB)
              
    num_metrics = len(METRICS)
    if not IS_VERTICAL:
        card_w = (W - 200 - (num_metrics - 1) * 30) / num_metrics
        card_h = 560
        y = 280
        for k, met in enumerate(METRICS):
            g = smooth_step(u, 0.25 + k * 0.3, 0.75 + k * 0.3)
            if g <= 0: continue
            x = 100 + k * (card_w + 30)
            draw_card_panel(draw, [x, y, x + card_w, y + card_h], alpha=g, border_color=hex_to_rgb(met["color"]))
            
            # Counter Value
            v = smooth_step(u, 0.3 + k * 0.3, 1.6 + k * 0.3)
            draw_text(draw, met["num"], x + card_w / 2, y + 170, "h", 68, hex_to_rgb(met["color"]), alpha=g, align="c")
            draw_text(draw, met["label"], x + card_w / 2, y + 270, "b", 24, TEXT_RGB, alpha=g, align="c")
            
            # Five golden stars
            for s_idx in range(5):
                star_x = x + card_w / 2 - 80 + s_idx * 40
                draw.ellipse([star_x - 10, y + 360 - 10, star_x + 10, y + 360 + 10], fill=GOLD_RGB)
            draw_text(draw, "5.0 Verified Rating", x + card_w / 2, y + 405, "mb", 20, GOLD_RGB, alpha=g, align="c")
    else:
        # Vertical 9:16 layout
        row_h = 160
        for k, met in enumerate(METRICS):
            g = smooth_step(u, 0.25 + k * 0.3, 0.75 + k * 0.3)
            if g <= 0: continue
            y = 300 + k * (row_h + 20)
            draw_card_panel(draw, [50, y, W - 50, y + row_h], alpha=g, border_color=hex_to_rgb(met["color"]))
            draw_text(draw, met["num"], 90, y + 40, "h", 58, hex_to_rgb(met["color"]), alpha=g)
            draw_text(draw, met["label"], 90, y + 110, "b", 22, TEXT_RGB, alpha=g)

def scene_8(draw, t):
    """Scene 8: High-Converting Call to Action"""
    u = t - SS[8]
    cx = W / 2.0
    cy = (H / 2.0) - (0 if not IS_VERTICAL else 140)
    
    # Glowing ALGENZA Crest
    draw_algenza_logo_mark(draw, cx, cy - 140, size=150, alpha=smooth_step(u, 0.1, 0.6))
    
    draw_text(draw, "Ready to Automate Your Trading Edge?", cx, cy + 20, "h", 64 if not IS_VERTICAL else 48, TEXT_RGB,
              alpha=smooth_step(u, 0.25, 0.75), align="c")
    draw_text(draw, "Visit algenza.com to deploy institutional EAs or request a custom build.", cx, cy + 95, "b", 32 if not IS_VERTICAL else 24,
              MUTED_RGB, alpha=smooth_step(u, 0.45, 0.95), align="c")
              
    # Glowing CTA Button
    btn_g = bounce_out(clamp((t - BTN_T) / 0.55))
    if btn_g > 0.01:
        btn_w = int(520 * btn_g)
        btn_h = int(90 * btn_g)
        btn_x0 = cx - btn_w / 2
        btn_y0 = cy + 180 - btn_h / 2
        
        # Outer glow
        draw_round_rect(draw, [btn_x0 - 6, btn_y0 - 6, btn_x0 + btn_w + 6, btn_y0 + btn_h + 6],
                        radius=int(btn_h / 2) + 6, fill=(112, 224, 214, int(80 * btn_g)))
        # Button body
        draw_round_rect(draw, [btn_x0, btn_y0, btn_x0 + btn_w, btn_y0 + btn_h],
                        radius=int(btn_h / 2), fill=TEAL_RGB)
                        
        cta_label = os.environ.get("CTA_LABEL", "VISIT ALGENZA.COM")
        draw_text(draw, cta_label, cx, btn_y0 + int(24 * btn_g), "h", int(36 * btn_g), COLORS["dark"], align="c")
        
    # Founder credibility badge
    draw_text(draw, f"Lead Quantitative Engineer: {FOUNDER_NAME}", cx, cy + 290, "mb", 22, GOLD_RGB,
              alpha=smooth_step(u, 0.8, 1.4), align="c")
    draw_text(draw, f"WhatsApp Direct: {WHATSAPP_NUMBER}  \u00b7  {BRAND_DISPLAY_URL}", cx, cy + 325, "b", 20, MUTED_RGB,
              alpha=smooth_step(u, 1.0, 1.6), align="c")

SCENES = [scene_0, scene_1, scene_2, scene_3, scene_4, scene_5, scene_6, scene_7, scene_8]

# 11. Word-Wrap Subtitle Bar
def wrap_text(s, max_chars=60):
    words = s.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 > max_chars and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines

def draw_subtitles(draw, t):
    for i, s0 in enumerate(ST):
        e = s0 + D[i]
        if s0 - 0.1 <= t <= e + 0.35:
            alpha = min(smooth_step(t, s0 - 0.1, s0 + 0.15), 1.0 - smooth_step(t, e + 0.05, e + 0.35))
            if alpha <= 0.01:
                continue
                
            lines = wrap_text(LINES[i], max_chars=56 if not IS_VERTICAL else 34)
            sub_y0 = H - 90 - (len(lines) - 1) * 44 if not IS_VERTICAL else H - 160 - (len(lines) - 1) * 44
            
            # Find max text width
            f = get_font("b", 30 if not IS_VERTICAL else 26)
            max_w = 0
            for l in lines:
                bb = draw.textbbox((0, 0), l, font=f)
                max_w = max(max_w, bb[2] - bb[0])
                
            pill_l = W / 2 - max_w / 2 - 28
            pill_r = W / 2 + max_w / 2 + 28
            pill_t = sub_y0 - 24
            pill_b = sub_y0 + len(lines) * 44 + 6
            
            draw_round_rect(draw, [pill_l, pill_t, pill_r, pill_b], radius=14,
                            fill=(5, 11, 20, int(210 * alpha)),
                            outline=(TEAL_RGB[0], TEAL_RGB[1], TEAL_RGB[2], int(160 * alpha)), width=1)
                            
            for j, l in enumerate(lines):
                draw_text(draw, l, W / 2, sub_y0 + j * 44 - 10, "b", 30 if not IS_VERTICAL else 26,
                          TEXT_RGB, alpha=alpha, align="c")

# 12. Persistent Top Watermark
def draw_watermark(draw, t):
    if t < 1.0:
        return
    a = smooth_step(t, 1.0, 2.0) * (1.0 - smooth_step(t, SS[-1] + 1.0, SS[-1] + 2.0))
    if a <= 0.01:
        return
        
    wx = 60
    wy = 55
    draw_algenza_logo_mark(draw, wx + 20, wy + 20, size=36, alpha=a)
    draw_text(draw, "ALGENZA", wx + 52, wy + 8, "h", 26, TEXT_RGB, alpha=a)
    draw_text(draw, "PRO", wx + 190, wy + 11, "mb", 16, TEAL_RGB, alpha=a)

# 13. Master Frame Renderer
def render_frame(frame_idx):
    t = frame_idx / float(FPS)
    img = BACKGROUND_LAYER.copy()
    draw = ImageDraw.Draw(img)
    
    # Floating ambient particles
    draw_particles(draw, t)
    
    # Active Scene Rendering
    for i in range(NS):
        if not (SS[i] - 0.05 <= t <= SE[i] + 0.08):
            continue
        SCENES[i](draw, t)
        
    # Sentinel HUD Character Positioning
    # In 16:9, positioned on right; in 9:16 positioned near bottom/mid
    if not IS_VERTICAL:
        char_x = W - 320
        char_y = H - 340
        char_scale = 1.0
    else:
        char_x = W / 2.0
        char_y = H - 380
        char_scale = 0.85
        
    mouth_val = get_mouth_val(t)
    cur_scene_idx = 0
    for k in range(NS):
        if t >= SS[k]:
            cur_scene_idx = k
    draw_quant_sentinel(draw, t, mouth_val, char_x, char_y, scale=char_scale, scene_idx=cur_scene_idx)
    
    # Watermark & Subtitles
    draw_watermark(draw, t)
    draw_subtitles(draw, t)
    
    return img

# 14. CLI Interface & Parallel Segment Worker
def main():
    if len(sys.argv) < 2:
        print("Usage: python render.py [still <ts> ... | enc <worker_idx> <num_workers> | full <output.mp4>]")
        return

    mode = sys.argv[1].lower()
    
    if mode == "still":
        timestamps = [float(x) for x in sys.argv[2:]] if len(sys.argv) > 2 else [3.0, 15.0, 25.0, 45.0, 60.0]
        for ts in timestamps:
            fi = int(ts * FPS)
            img = render_frame(fi)
            out_png = f"still_{ts:.1f}.png"
            img.save(out_png)
            print(f"Saved snapshot: {out_png}")
            
    elif mode == "enc":
        w = int(sys.argv[2])
        n = int(sys.argv[3])
        total_frames = int(END * FPS)
        a = total_frames * w // n
        b = total_frames * (w + 1) // n
        out_seg = sys.argv[4] if len(sys.argv) > 4 else f"seg{w}.mp4"
        
        print(f"Rendering segment {w}/{n} (frames {a} to {b}) into {out_seg}...", flush=True)
        cmd = [
            FFMPEG_EXE, "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgba",
            "-s", f"{W}x{H}", "-r", str(FPS),
            "-i", "-",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-g", "120",
            out_seg
        ]
        
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for fi in range(a, b):
            frame_img = render_frame(fi)
            proc.stdin.write(frame_img.tobytes())
            
        proc.stdin.close()
        proc.wait()
        print(f"Segment {w} complete.")
        
    elif mode == "full":
        out_file = sys.argv[2] if len(sys.argv) > 2 else "algenza-explainer-raw.mp4"
        total_frames = int(END * FPS)
        print(f"Rendering full video ({total_frames} frames @ {W}x{H}, 60fps) into {out_file}...")
        cmd = [
            FFMPEG_EXE, "-y", "-loglevel", "info",
            "-f", "rawvideo", "-pix_fmt", "rgba",
            "-s", f"{W}x{H}", "-r", str(FPS),
            "-i", "-",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-g", "120",
            out_file
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for fi in range(total_frames):
            frame_img = render_frame(fi)
            proc.stdin.write(frame_img.tobytes())
            if fi % 120 == 0:
                print(f"  Frame {fi}/{total_frames} ({fi/total_frames*100:.1f}%)")
        proc.stdin.close()
        proc.wait()
        print(f"Full render complete: {out_file}")

if __name__ == "__main__":
    main()
