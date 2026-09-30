<#
.SYNOPSIS
ALGENZA Explainer Video Engine - Automated Windows Build Script
Generates voiceover, procedural cyber-quant audio, frames, and final MP4 video.
#>

param (
    [string]$Aspect = "16:9",
    [int]$Workers = 4,
    [switch]$All
)

$ErrorActionPreference = "Stop"
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "    ▲  ALGENZA VIDEO ENGINE - HIGH-PERFORMANCE VIDEO BUILDER" -ForegroundColor Cyan
Write-Host "       algenza.com  ·  Lead Architect: Muhammad Hassan" -ForegroundColor DarkGray
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "Python 3.10+ was not found in PATH. Please install Python to proceed."
}

# 2. Install dependencies if needed
Write-Host "`n[1/4] Checking Python Dependencies..." -ForegroundColor Yellow
python -m pip install -r requirements.txt --quiet

# 3. Generate Voiceover
Write-Host "`n[2/4] Generating Neural Voiceover (Edge-TTS / Kokoro)..." -ForegroundColor Yellow
if (-not (Test-Path "v8.wav") -or -not (Test-Path "tts.json")) {
    python tts.py
} else {
    Write-Host "Using existing voiceover audio." -ForegroundColor Green
}

# 4. Synthesize Audio & Lip-Sync Envelope
Write-Host "`n[3/4] Synthesizing Cyber-Quant Soundtrack & Lip-Sync..." -ForegroundColor Yellow
python mix.py

# 5. Render Video Frames & Mux MP4
Write-Host "`n[4/4] Rendering Video Frames & Assembling Final MP4..." -ForegroundColor Yellow
if ($All) {
    python cli.py build --aspect all --workers $Workers --skip-tts --skip-mix
} else {
    python cli.py build --aspect $Aspect --workers $Workers --skip-tts --skip-mix
}

Write-Host "`n=================================================================" -ForegroundColor Green
Write-Host "  BUILD COMPLETE! Videos are ready in the assets/ directory." -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
