@echo off
setlocal
cd /d "%~dp0"
echo ========================================
echo ThermoIntel - FRESH DATABASE RESET
echo ========================================
echo.
echo WARNING: This removes the ThermoIntel PostgreSQL Docker volume.
choice /M "Continue"
if errorlevel 2 exit /b 0

docker compose down -v --remove-orphans
if errorlevel 1 (
  echo Reset failed while stopping Docker services.
  pause
  exit /b 1
)

echo Fresh database removed. Starting complete initialization...
echo OSM facilities and the intelligence pipeline will be processed automatically.
call RUN_THERMOINTEL.bat
endlocal
