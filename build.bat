@echo off
REM ALGENZA Explainer Video Engine - Windows 1-Click Builder
echo =================================================================
echo     ALGENZA VIDEO ENGINE - HIGH-PERFORMANCE VIDEO BUILDER
echo     algenza.com  -  Lead Architect: Muhammad Hassan
echo =================================================================

python -m pip install -r requirements.txt
python tts.py
python mix.py
python cli.py build --aspect 16:9
echo.
echo Build finished! Check assets\algenza-explainer-16x9.mp4
pause
