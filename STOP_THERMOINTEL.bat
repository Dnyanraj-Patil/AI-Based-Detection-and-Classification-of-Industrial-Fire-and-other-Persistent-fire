@echo off
cd /d "%~dp0"
echo Stopping ThermoIntel...
docker compose down --remove-orphans
echo.
echo ThermoIntel stopped.
pause
