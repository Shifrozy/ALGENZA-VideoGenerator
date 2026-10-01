@echo off
REM ALGENZA Explainer Video Engine - Windows 1-Click Builder
echo =================================================================
echo     ALGENZA VIDEO ENGINE - HIGH-PERFORMANCE VIDEO BUILDER
echo     algenza.com  -  Lead Architect: Muhammad Hassan
echo =================================================================

set ASPECT=%1
if "%ASPECT%"=="" set ASPECT=16:9

python cli.py build --aspect %ASPECT% --workers 4
echo.
echo Build finished! Check assets\ directory.
pause
