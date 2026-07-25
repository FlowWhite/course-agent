@echo off
cd /d "%~dp0"

powershell.exe ^
    -NoProfile ^
    -ExecutionPolicy Bypass ^
    -File "%~dp0start-docker-compose.ps1"

echo.
pause
