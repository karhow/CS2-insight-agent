@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -WindowStyle Normal -ExecutionPolicy Bypass -File "%~dp0Launch-CS2Insight.ps1"
endlocal
