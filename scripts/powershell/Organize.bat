@echo off
setlocal
echo ===========================================
echo  ORGANIZADO - lanzando Organize.ps1
echo ===========================================
echo.
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Organize.ps1"
echo.
echo Presiona Enter para cerrar.
pause >nul
