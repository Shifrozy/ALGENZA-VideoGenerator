"""
ALGENZA Video Engine - Voiceover Generation (TTS)
Generates crystal-clear narration using Edge Neural Studio TTS or Kokoro ONNX,
with automatic fallback and support for custom audio recordings.
Outputs v0.wav .. v8.wav and tts.json
"""

import os
import sys
import json
import asyncio
import soundfile as sf
import numpy as np
from tl import LINES as L

# Preferred voices:
# Edge Neural: 'en-US-ChristopherNeural' (Deep, authoritative institutional quant tone)
# Alternative: 'en-US-GuyNeural', 'en-US-EricNeural', 'en-GB-RyanNeural'
EDGE_VOICE = os.environ.get("VOICE", "en-US-ChristopherNeural")

def clean_speech_text(text: str) -> str:
    """Preprocess acronyms and technical trading terms for natural phonetics"""
    t = text
    t = t.replace("XAUUSD", "Gold X A U U S D")
    t = t.replace("MQL5", "M Q L 5")
    t = t.replace("MT5", "M T 5")
    t = t.replace("MT4", "M T 4")
    t = t.replace("EAs", "Expert Advisors")
    t = t.replace("EA", "E A")
    t = t.replace("FIX API", "Fix A P I")
    t = t.replace("IBKR", "I B K R")
    t = t.replace("FTMO", "F T M O")
    t = t.replace("$12M+", "twelve million dollars plus")
    t = t.replace("200+", "over two hundred")
    t = t.replace("99.4%", "ninety-nine point four percent")
    t = t.replace("99.9%", "ninety-nine point nine percent")
    t = t.replace("<0.4ms", "under zero point four milliseconds")
    t = t.replace("0.2ms", "zero point two milliseconds")
    t = t.replace("1%", "one percent")
    t = t.replace("algenza.com", "al-gen-za dot com")
    return t

async def gen_edge_tts(lines):
    import edge_tts
    print(f"Generating studio voiceover with Edge-TTS voice: {EDGE_VOICE}...")
    durations = []
    sr = 24000
    
    for i, line in enumerate(lines):
        clean_text = clean_speech_text(line)
        mp3_file = f"v{i}.mp3"
        wav_file = f"v{i}.wav"
        
        communicate = edge_tts.Communicate(clean_text, EDGE_VOICE, rate="+0%", pitch="+0Hz")
        await communicate.save(mp3_file)
        
        # Read and convert to WAV 48kHz for pristine audio mixing
        # Try soundfile directly or use ffmpeg
        try:
            import imageio_ffmpeg
            import subprocess
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            subprocess.run([
                ffmpeg_exe, "-y", "-loglevel", "error",
                "-i", mp3_file, "-ar", "48000", "-ac", "1", wav_file
            ], check=True)
            data, sr = sf.read(wav_file)
            dur = len(data) / sr
        except Exception:
            data, sr = sf.read(mp3_file)
            sf.write(wav_file, data, sr)
            dur = len(data) / sr
            
        durations.append(dur)
        if os.path.exists(mp3_file):
            try: os.remove(mp3_file)
            except Exception: pass
            
        print(f"  [v{i}.wav] ({dur:.2f}s): {line[:40]}...")
        
    return sr, durations

def gen_kokoro_tts(lines):
    from kokoro_onnx import Kokoro
    print("Generating voiceover with Kokoro-ONNX...")
    k = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
    durations = []
    sr = 24000
    for i, l in enumerate(lines):
        clean = clean_speech_text(l)
        s, sr = k.create(clean, voice="am_michael", speed=1.0, lang="en-us")
        wav_file = f"v{i}.wav"
        sf.write(wav_file, s, sr)
        durations.append(len(s) / sr)
        print(f"  [v{i}.wav] ({len(s)/sr:.2f}s): {l[:40]}...")
    return sr, durations

def gen_synthetic_speech_fallback(lines):
    """Procedural fallback speech signal in case offline without TTS packages"""
    print("Synthesizing calibrated speech envelope fallback...")
    sr = 48000
    durations = [3.8, 5.2, 5.5, 4.8, 5.4, 4.9, 5.3, 4.6, 3.8]
    for i, dur in enumerate(durations):
        n_samples = int(dur * sr)
        t = np.arange(n_samples) / sr
        # Formant frequencies for vocal simulation
        sig = 0.25 * np.sin(2 * np.pi * 140 * t) + 0.15 * np.sin(2 * np.pi * 420 * t)
        env = np.clip(np.sin(np.pi * t / dur) * 1.5, 0, 1)
        # Add modulation simulating speech cadence
        mod = 0.5 + 0.5 * np.sin(2 * np.pi * 3.5 * t)
        out = sig * env * mod
        sf.write(f"v{i}.wav", out.astype(np.float32), sr)
    return sr, durations

def main():
    # Check if user already provided manual custom recordings v0.wav .. v8.wav
    has_custom = all(os.path.exists(f"v{i}.wav") for i in range(len(L)))
    if has_custom and "--force" not in sys.argv:
        print("Using existing voice recordings v0.wav .. v8.wav")
        durations = []
        sr = 48000
        for i in range(len(L)):
            data, r = sf.read(f"v{i}.wav")
            sr = r
            durations.append(len(data) / r)
        json.dump({"sr": sr, "d": durations}, open("tts.json", "w"), indent=2)
        print("TTSDONE", [round(d, 2) for d in durations])
        return

    # Try Edge-TTS first (crystal clear neural voice)
    try:
        import edge_tts
        sr, durations = asyncio.run(gen_edge_tts(L))
    except Exception as e:
        print(f"Edge-TTS unavailable or offline ({e}). Trying Kokoro-ONNX...")
        if os.path.exists("kokoro-v1.0.onnx") and os.path.exists("voices-v1.0.bin"):
            try:
                sr, durations = gen_kokoro_tts(L)
            except Exception as e2:
                print(f"Kokoro-ONNX error: {e2}")
                sr, durations = gen_synthetic_speech_fallback(L)
        else:
            sr, durations = gen_synthetic_speech_fallback(L)

    json.dump({"sr": sr, "d": durations}, open("tts.json", "w"), indent=2)
    print("TTS Completed Successfully! Durations:", [round(d, 2) for d in durations])

if __name__ == "__main__":
    main()
