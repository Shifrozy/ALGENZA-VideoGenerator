"""
ALGENZA Video Engine - Script & Timeline
Narrative timeline for algenza.com explainer video.
Edit LINES below to customize the voiceover; all scene timings and sound events adapt automatically.
"""

import json
import os

# The 9 Core Narration Lines for ALGENZA Institutional Algorithmic Systems
LINES = [
    "You trade the markets, but you can't watch the charts all day.",
    "Missed Gold entries, emotional hesitation, and prop firm drawdown rules hold you back.",
    "Welcome to ALGENZA. Institutional algorithmic trading systems engineered for peak precision.",
    "Apex Scalper Pro for Gold. Titan Grid Engine. And Prop Risk Guard 360.",
    "Your rules become high-performance MQL5 and Python code, backtested on real tick data.",
    "Strict daily loss protection, sub-millisecond execution, and instant alerts to Telegram.",
    "100% proprietary code ownership. Clean architecture, full documentation, and engineering support.",
    "Over 200 custom Expert Advisors delivered, with a 99.4% prop pass rate.",
    "Deploy your algorithmic edge today at algenza.com."
]

NS = len(LINES)

# Load TTS durations or use calibrated speech defaults
DEFAULT_DURATIONS = [3.8, 5.2, 5.5, 4.8, 5.4, 4.9, 5.3, 4.6, 3.8]

TTS_FILE = "tts.json"
if os.path.exists(TTS_FILE):
    try:
        with open(TTS_FILE, "r") as f:
            T = json.load(f)
            D = T.get("d", DEFAULT_DURATIONS)
            if len(D) != NS:
                D = DEFAULT_DURATIONS
    except Exception:
        D = DEFAULT_DURATIONS
else:
    D = DEFAULT_DURATIONS

GAP = 0.55
ST = []
_t = 1.8

for x in D:
    ST.append(_t)
    _t += x + GAP

END = _t + 2.5
SS = [0.0] + [s - 0.35 for s in ST[1:]]
SE = SS[1:] + [END]

CHAR_T = 1.6
BTN_T = SS[-1] + 0.85

def cand_t(k):
    return 0.8 + k * 0.09

def card_t(k):
    return SS[3] + 0.35 + k * 0.40

def node_t(k):
    return SS[4] + 0.3 + k * (SE[4] - SS[4] - 0.5) / 5.0

def alert_t(k):
    return SS[5] + 1.2 + k * 1.1

def check_t(k):
    return SS[6] + 1.1 + k * 0.55

def events():
    """Returns procedural sound events (timestamp, type, frequency/param)"""
    E = []
    # Scene transitions: futuristic cyber whoosh
    for i in range(1, NS):
        E.append((SS[i], "whoosh", 0))
    
    # Scene 0: Candlestick price ticks
    for k in range(16):
        E.append((cand_t(k), "tick", 2400 + k * 30))
    
    # Scene 1: Alert / missed trade ding & stress pop
    E.append((SS[1] + 1.2, "ding", 720))
    E.append((SS[1] + 2.8, "pop", 380))
    
    # Scene 2: ALGENZA Brand Drop - cinematic sub boom & pop
    E.append((CHAR_T, "pop", 520))
    E.append((SS[2] + 0.20, "boom", 0))
    E.append((SS[2] + 0.90, "ding", 1040))
    
    # Scene 3: Algorithm Product Cards reveal
    for k in range(4):
        E.append((card_t(k), "pop", 540 + k * 90))
    
    # Scene 4: Pipeline Node activations (Rules -> Code -> Backtest -> FIX API -> Live)
    for k in range(5):
        E.append((node_t(k), "pop", 460 + k * 80))
    
    # Scene 5: Prop Guard Alerts (Telegram & Discord notification dings)
    E.append((alert_t(0), "ding", 880))
    E.append((alert_t(1), "ding", 1120))
    
    # Scene 6: Architecture Checkmarks
    for k in range(3):
        E.append((check_t(k), "pop", 640 + k * 110))
    
    # Scene 7: Performance Metric counters
    E.append((SS[7] + 0.35, "pop", 720))
    E.append((SS[7] + 0.75, "pop", 840))
    E.append((SS[7] + 1.20, "ding", 960))
    
    # Scene 8: Final CTA Button
    E.append((BTN_T, "ding", 1050))
    
    return E
