"""
ALGENZA Video Engine - Command Line Interface (CLI)
Automates video compilation for multiple social media formats (16:9, 9:16, 1:1)
"""

import os
import sys
import argparse
import subprocess
import time
import io

# Ensure UTF-8 stdout encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

from tl import LINES, NS, ST, D, END, SS, SE

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"

def print_banner():
    print("=" * 68)
    print("      [*]  ALGENZA VIDEO ENGINE - HIGH-PERFORMANCE QUANTITATIVE VIDEO")
    print("         algenza.com  -  Lead Architect: Muhammad Hassan")
    print("=" * 68)

def run_tts():
    print("\n[1/3] Generating Voiceover Narration...")
    import tts
    tts.main()

def run_mix():
    print("\n[2/3] Synthesizing Cyber-Quant Soundtrack & Lip-Sync Envelope...")
    cmd = [sys.executable, "mix.py"]
    subprocess.run(cmd, check=True)

def render_aspect(aspect="16:9", workers=4, cta="website"):
    print(f"\n[3/3] Rendering Video Frames for Aspect Ratio: {aspect}...")
    
    clean_aspect_name = aspect.replace(":", "x")
    out_name = f"assets/algenza-explainer-{clean_aspect_name}.mp4"
    os.makedirs("assets", exist_ok=True)
    
    env = os.environ.copy()
    env["ASPECT"] = aspect
    env["CTA"] = cta
    
    # Render segments in parallel
    workers = max(1, min(workers, 8))
    segment_files = []
    procs = []
    
    t_start = time.time()
    print(f"  Spawning {workers} parallel render workers...")
    for w in range(workers):
        seg_file = f"seg_{clean_aspect_name}_{w}.mp4"
        segment_files.append(seg_file)
        
        # Invoke render.py with custom segment output name
        p = subprocess.Popen([
            sys.executable, "render.py", "enc", str(w), str(workers), seg_file
        ], env=env)
        procs.append(p)
        
    for p in procs:
        p.wait()
        if p.returncode != 0:
            raise RuntimeError(f"Render process exited with error code {p.returncode}")
            
    # Create FFmpeg concat list
    list_path = f"list_{clean_aspect_name}.txt"
    with open(list_path, "w") as f:
        for seg in segment_files:
            f.write(f"file '{seg}'\n")
            
    print("  Muxing audio soundtrack and applying broadcast normalization...")
    mux_cmd = [
        FFMPEG_EXE, "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", list_path,
        "-i", "mix.wav",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy",
        "-af", "loudnorm=I=-16:TP=-1.5",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart",
        out_name
    ]
    subprocess.run(mux_cmd, check=True)
    
    # Cleanup temporary segment files
    for seg in segment_files:
        if os.path.exists(seg):
            try: os.remove(seg)
            except Exception: pass
    if os.path.exists(list_path):
        try: os.remove(list_path)
        except Exception: pass
        
    elapsed = time.time() - t_start
    size_mb = os.path.getsize(out_name) / (1024 * 1024) if os.path.exists(out_name) else 0
    print(f"SUCCESS! Rendered: {out_name} ({size_mb:.2f} MB, {elapsed:.1f}s)")
    return out_name

def show_info():
    print_banner()
    print(f"\nNarrative Script Timeline ({NS} Scenes, Total: {END:.2f}s):\n")
    print(f"{'#':<4} {'Start':<8} {'Duration':<10} {'Scene Text':<50}")
    print("-" * 68)
    for i in range(NS):
        dur = D[i] if i < len(D) else 0.0
        st = ST[i] if i < len(ST) else 0.0
        print(f"{i+1:<4} {st:<8.2f} {dur:<10.2f} {LINES[i][:48]}...")
    print("\nTarget Social Media Platforms:")
    print("  - 16:9 Landscape (1920x1080): YouTube, Website, Client Presentations")
    print("  - 9:16 Vertical  (1080x1920): TikTok, Instagram Reels, YouTube Shorts")
    print("  - 1:1  Square    (1080x1080): Instagram Feed, LinkedIn, Twitter / X")

def main():
    parser = argparse.ArgumentParser(description="ALGENZA Video Engine CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    # info
    subparsers.add_parser("info", help="Display script timeline and scene timestamps")
    
    # tts
    subparsers.add_parser("tts", help="Generate voiceover audio")
    
    # mix
    subparsers.add_parser("mix", help="Synthesize soundtrack and audio effects")
    
    # preview
    p_prev = subparsers.add_parser("preview", help="Render still frames for preview")
    p_prev.add_argument("--aspect", default="16:9", choices=["16:9", "9:16", "1:1"])
    
    # build
    p_build = subparsers.add_parser("build", help="Build and render explainer video")
    p_build.add_argument("--aspect", default="16:9", choices=["16:9", "9:16", "1:1", "all"])
    p_build.add_argument("--workers", type=int, default=4, help="Number of parallel render workers")
    p_build.add_argument("--skip-tts", action="store_true", help="Skip TTS regeneration")
    p_build.add_argument("--skip-mix", action="store_true", help="Skip audio mix regeneration")
    
    args = parser.parse_args()
    
    if args.command == "info" or not args.command:
        show_info()
        return
        
    if args.command == "tts":
        run_tts()
        return
        
    if args.command == "mix":
        run_mix()
        return
        
    if args.command == "preview":
        env = os.environ.copy()
        env["ASPECT"] = args.aspect
        subprocess.run([sys.executable, "render.py", "still", "2.0", "15.0", "25.0", "36.0", "52.0"], env=env)
        return
        
    if args.command == "build":
        print_banner()
        if not args.skip_tts or not os.path.exists("tts.json"):
            run_tts()
        if not args.skip_mix or not os.path.exists("mix.wav"):
            run_mix()
            
        if args.aspect == "all":
            for asp in ["16:9", "9:16", "1:1"]:
                render_aspect(aspect=asp, workers=args.workers)
        else:
            render_aspect(aspect=args.aspect, workers=args.workers)

if __name__ == "__main__":
    main()
