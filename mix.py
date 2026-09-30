"""
ALGENZA Video Engine - Procedural Audio Synthesizer & Mixer
Generates institutional cyber-quant soundtrack, procedural sound effects,
speech sidechain ducking, master loudness normalization, and mouth.npy lip-sync.
Outputs: mix.wav and mouth.npy
"""

import os
import sys
import numpy as np
import soundfile as sf
from tl import *

SR = 48000
N = int((END + 0.6) * SR)
tt = np.arange(N) / SR
V = np.zeros(N)

# 1. Load and align voice lines
for i, s0 in enumerate(ST):
    wav_path = f"v{i}.wav"
    if not os.path.exists(wav_path):
        continue
    s, r = sf.read(wav_path)
    if s.ndim > 1:
        s = s.mean(axis=1)
    if r != SR:
        n2 = int(len(s) * SR / r)
        s = np.interp(np.arange(n2) * r / SR, np.arange(len(s)), s)
    a = int(s0 * SR)
    if a < N:
        avail = min(len(s), N - a)
        V[a:a + avail] += s[:avail]

# Normalize voice
max_v = np.abs(V).max()
if max_v > 1e-9:
    V = (V / max_v) * 0.92

# 2. Musical Note Frequency Helper
def midi_to_freq(m):
    return 440.0 * 2.0 ** ((m - 69.0) / 12.0)

def add_signal(target, sig, t0, gain=1.0):
    i = int(t0 * SR)
    if 0 <= i < N:
        j = min(N, i + len(sig))
        target[i:j] += gain * sig[:j - i]

# 3. Synthesize Institutional Cyber-Quant Soundtrack
rng = np.random.default_rng(42)
M = np.zeros(N)
bpm = 104.0
bt = 60.0 / bpm
bar = 4.0 * bt

# Elegant Minor Harmonic Progression (A minor -> F maj7 -> D minor -> E minor/G)
CHORDS = [
    [57, 60, 64, 67],  # Am7
    [53, 57, 60, 64],  # Fmaj7
    [50, 53, 57, 60],  # Dm7
    [55, 59, 62, 67]   # Gadd9
]

total_bars = int(END / bar) + 2

for b in range(total_bars):
    a = int(b * bar * SR)
    e = min(N, int((b + 1) * bar * SR))
    if a >= N:
        break
    
    u = tt[a:e] - b * bar
    # Smooth bar envelope
    env = np.clip(u / 0.35, 0, 1) * np.clip((bar - u) / 0.35, 0, 1)
    ch = CHORDS[b % len(CHORDS)]
    
    # Lush detuned pad chords
    for m in ch:
        f = midi_to_freq(m)
        for detune in (0.996, 1.000, 1.004):
            pad = np.sin(2 * np.pi * f * detune * tt[a:e])
            # Add warm 2nd harmonic
            pad += 0.3 * np.sin(4 * np.pi * f * detune * tt[a:e])
            M[a:e] += 0.022 * env * pad
            
    # Deep Analog Bass (Sub)
    bass_freq = midi_to_freq(ch[0] - 24)
    bass = np.sin(2 * np.pi * bass_freq * tt[a:e])
    bass += 0.4 * np.sin(4 * np.pi * bass_freq * tt[a:e])
    M[a:e] += 0.09 * env * bass
    
    # Quantized Arpeggio Plucks (8th notes)
    for k in range(8):
        pl_len = int(0.35 * SR)
        u_pl = np.arange(pl_len) / SR
        note = ch[k % len(ch)] + 12 + (12 if k % 4 == 2 else 0)
        pluck = np.sin(2 * np.pi * midi_to_freq(note) * u_pl) * np.exp(-u_pl * 12.0)
        add_signal(M, pluck, b * bar + k * (bt / 2.0), gain=0.035)

# 4. Drums (808 Kick, Rolling Trap Hats, Crisp Claps)
# Punchy 808 Kick
u_k = np.arange(int(0.42 * SR)) / SR
pitch_drop = 50.0 * u_k + 120.0 * (1.0 - np.exp(-32.0 * u_k)) / 32.0
kick = np.sin(2 * np.pi * pitch_drop) * np.exp(-u_k * 8.5)
# Add transient click
kick[:int(0.006 * SR)] += 0.4 * np.sin(2 * np.pi * 1200 * u_k[:int(0.006 * SR)])

# Hi-hat (filtered noise)
u_h = np.arange(int(0.05 * SR)) / SR
hat_noise = rng.normal(0, 1, len(u_h) + 1)
hat = np.diff(hat_noise) * np.exp(-u_h * 90.0)

# Snare / Clap
u_c = np.arange(int(0.24 * SR)) / SR
clap = rng.normal(0, 1, len(u_c)) * np.exp(-u_c * 24.0)

# Beat arrangement: start after intro hook
t_beat = SS[2] + 0.15
beat_idx = 0
while t_beat < END - 1.8:
    # Kick on beat 1 and 3 (and syncopated)
    if beat_idx % 4 in (0, 2):
        add_signal(M, kick, t_beat, gain=0.24)
    # Hi-hats every 8th note
    add_signal(M, hat, t_beat, gain=0.025)
    add_signal(M, hat, t_beat + bt / 2.0, gain=0.020)
    # Clap on 2 and 4
    if beat_idx % 2 == 1:
        add_signal(M, clap, t_beat, gain=0.045)
        
    t_beat += bt
    beat_idx += 1

# 5. Procedural Sound Effects
X = np.zeros(N)

for ev in events():
    t0 = ev[0]
    kind = ev[1]
    param = ev[2]
    
    if kind == "whoosh":
        L_w = int(0.75 * SR)
        raw_noise = rng.normal(0, 1, L_w)
        # Smooth bandpass shape
        smooth_kernel = np.ones(12) / 12.0
        smoothed = np.convolve(raw_noise, smooth_kernel, mode="same")
        envelope = (np.sin(np.pi * np.arange(L_w) / L_w) ** 2)
        add_signal(X, smoothed * envelope, t0 - 0.35, gain=0.35)
        
    elif kind == "tick":
        L_t = int(0.035 * SR)
        u_t = np.arange(L_t) / SR
        freq = param if param > 0 else 2400.0
        tick_sig = np.sin(2 * np.pi * freq * u_t) * np.exp(-u_t * 140.0)
        add_signal(X, tick_sig, t0, gain=0.08)
        
    elif kind == "pop":
        L_p = int(0.18 * SR)
        u_p = np.arange(L_p) / SR
        f0 = param if param > 0 else 520.0
        pop_sig = np.sin(2 * np.pi * f0 * u_p * (1.0 + 0.6 * np.exp(-u_p * 35.0))) * np.exp(-u_p * 22.0)
        add_signal(X, pop_sig, t0, gain=0.18)
        
    elif kind == "ding":
        L_d = int(1.1 * SR)
        u_d = np.arange(L_d) / SR
        f0 = param if param > 0 else 880.0
        # Multi-harmonic crystalline chime
        chime = (
            np.sin(2 * np.pi * f0 * u_d) +
            0.45 * np.sin(2 * np.pi * (f0 * 2.0) * u_d) +
            0.20 * np.sin(2 * np.pi * (f0 * 3.01) * u_d) +
            0.12 * np.sin(2 * np.pi * (f0 * 4.18) * u_d)
        ) * np.exp(-u_d * 5.5)
        add_signal(X, chime, t0, gain=0.14)
        
    elif kind == "boom":
        L_b = int(1.8 * SR)
        u_b = np.arange(L_b) / SR
        sub_drop = np.sin(2 * np.pi * (38.0 * u_b + 70.0 * (1.0 - np.exp(-7.0 * u_b)) / 7.0)) * np.exp(-u_b * 2.2)
        noise_impact = 0.35 * rng.normal(0, 1, L_b) * np.exp(-u_b * 12.0)
        add_signal(X, sub_drop + noise_impact, t0, gain=0.48)

# 6. Moving Average & Speech Sidechain Ducking
def moving_average(x, w):
    c = np.cumsum(np.insert(x, 0, 0))
    y = (c[w:] - c[:-w]) / w
    hw = w // 2
    return np.concatenate([np.full(hw, y[0]), y, np.full(len(x) - len(y) - hw, y[-1])])

# Voice energy envelope for ducking
voice_env = moving_average(np.abs(V), int(0.14 * SR))
max_env = voice_env.max() if voice_env.max() > 0 else 1.0
# Duck music by up to 65% when voice is loud
ducking_gain = 1.0 - 0.65 * np.clip(voice_env / (0.22 * max_env), 0, 1)
ducking_gain = moving_average(ducking_gain, int(0.28 * SR))

# Master fade in and out
fade_in = np.clip(tt / 0.45, 0, 1)
fade_out = np.clip((END + 0.35 - tt) / 1.6, 0, 1)
master_envelope = fade_in * fade_out

# Combine voice, ducked music, and sound effects
music_stem = M * ducking_gain * 0.58 * master_envelope
sfx_stem = X * 0.85 * master_envelope
mix_out = V + music_stem + sfx_stem

# Master limiting & peak headroom
peak = np.abs(mix_out).max()
if peak > 0:
    mix_out = (mix_out / peak) * 0.94

# Write stereo mix
stereo = np.stack([mix_out, mix_out], axis=1)
sf.write("mix.wav", stereo, SR, subtype="PCM_16")

# 7. Generate Lip-sync / Audio-Reactive Envelope (mouth.npy)
FPS = 60
NF = int(END * FPS) + 4
hop = SR // FPS
rms = np.array([
    np.sqrt(np.mean(V[i * hop:(i + 1) * hop] ** 2)) if i * hop < N else 0.0
    for i in range(NF)
])

active_speech = rms[rms > 0.008]
ref = np.percentile(active_speech, 90) if len(active_speech) > 0 else 1.0
raw_mouth = np.clip((rms / ref - 0.07) / 0.93, 0, 1)

smooth_mouth = np.zeros(NF)
for i in range(1, NF):
    # Fast attack, smooth decay
    factor = 0.65 if raw_mouth[i] > smooth_mouth[i - 1] else 0.28
    smooth_mouth[i] = smooth_mouth[i - 1] + (raw_mouth[i] - smooth_mouth[i - 1]) * factor

np.save("mouth.npy", smooth_mouth)
print(f"MIXDONE: mix.wav ({round(END, 2)}s, 48kHz Stereo) & mouth.npy ({len(smooth_mouth)} frames)")
