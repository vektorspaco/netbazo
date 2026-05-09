@echo off
setlocal
echo ===========================================
echo  DEDUPE - lanzando Dedupe.ps1
echo ===========================================
echo.
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Dedupe.ps1"
echo.
echo Presiona Enter para cerrar.
pause >nul
