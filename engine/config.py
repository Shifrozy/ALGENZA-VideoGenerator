"""
ALGENZA Video Engine - Configuration & Design Tokens
"""

import os
import sys

# Brand Identity
BRAND_NAME = "ALGENZA"
BRAND_TAG = "PRO"
BRAND_SLOGAN = "Institutional Algorithmic Trading Systems"
BRAND_URL = "https://algenza.com"
BRAND_DISPLAY_URL = "algenza.com"
FOUNDER_NAME = "Muhammad Hassan"
FOUNDER_ROLE = "Lead Quantitative Systems Engineer & CEO"
WHATSAPP_NUMBER = "+92 319 7375850"
WHATSAPP_LINK = "https://wa.me/923197375850"
SUPPORT_EMAIL = "muhammadhassanchanna8@gmail.com"

# Color Palette (Hex & RGBA)
COLORS = {
    "bg": "#050b14",
    "bg_alt": "#08101d",
    "panel": "#0c1524",
    "panel_light": "#121e33",
    "border": "#1b2940",
    "border_glow": "#243754",
    "teal": "#70e0d6",       # Primary brand polygon
    "teal_glow": "#00f2fe",
    "rose": "#f49097",       # Secondary brand polygon
    "rose_glow": "#ff4b72",
    "gold": "#ffd700",       # XAUUSD Gold accent
    "gold_glow": "#f59e0b",
    "green": "#00e676",      # Buy / Profit / Verified
    "red": "#ef4444",        # Sell / Missed / Drawdown
    "blue": "#38bdf8",       # API / Tick Latency
    "purple": "#a855f7",     # AI / Neural Quant
    "text": "#ffffff",
    "text_secondary": "#cbd5e1",
    "muted": "#94a3b8",
    "dark": "#02060d"
}

def hex_to_rgb(hex_code):
    h = hex_code.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def hex_to_rgba(hex_code, alpha=255):
    rgb = hex_to_rgb(hex_code)
    return (rgb[0], rgb[1], rgb[2], int(alpha))

# Video Format Aspect Ratios
ASPECT_RATIOS = {
    "16:9": {
        "width": 1920,
        "height": 1080,
        "name": "Landscape (YouTube, Web, Desktop)",
        "orientation": "landscape"
    },
    "9:16": {
        "width": 1080,
        "height": 1920,
        "name": "Vertical (TikTok, Reels, Shorts)",
        "orientation": "vertical"
    },
    "1:1": {
        "width": 1080,
        "height": 1080,
        "name": "Square (Instagram, LinkedIn, X)",
        "orientation": "square"
    }
}

DEFAULT_ASPECT = "16:9"
DEFAULT_FPS = 60
DEFAULT_SAMPLE_RATE = 48000

# Products Catalog
PRODUCTS = [
    {
        "name": "Apex Scalper Pro",
        "tagline": "XAUUSD Gold Tick Scalper",
        "desc": "High-frequency volatility scalping with microsecond tick filters and hard stop-loss.",
        "badge": "Institutional Gold",
        "color": COLORS["gold"]
    },
    {
        "name": "Titan Grid Engine",
        "tagline": "Dynamic Multi-Pair Hedging",
        "desc": "Adaptive algorithmic grid with dynamic trailing take-profit and zero martingale.",
        "badge": "Multi-Asset",
        "color": COLORS["teal"]
    },
    {
        "name": "Prop Risk Guard 360",
        "tagline": "FTMO & Prop Challenge Safe",
        "desc": "Automated daily loss locks, equity guardians, and strict 1% risk per trade limits.",
        "badge": "100% Rule Compliant",
        "color": COLORS["green"]
    },
    {
        "name": "Python & FIX API Bridge",
        "tagline": "Sub-Millisecond Routing",
        "desc": "Direct broker bridges for Interactive Brokers, Binance, Bybit with 0.2ms latency.",
        "badge": "FIX Protocol",
        "color": COLORS["blue"]
    }
]

# Verified Metrics
METRICS = [
    {"num": "200+", "label": "Custom EAs Delivered", "color": COLORS["teal"]},
    {"num": "$12M+", "label": "Live Volume Routed", "color": COLORS["gold"]},
    {"num": "99.4%", "label": "Verified Pass Rate", "color": COLORS["green"]},
    {"num": "<0.4ms", "label": "Tick Execution Latency", "color": COLORS["blue"]}
]
