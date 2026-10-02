@echo off
setlocal
cd /d "%~dp0"
echo ========================================
echo ThermoIntel - COMPLETE HEALTH CHECK
echo ========================================
echo.
echo [1] Docker services
docker compose ps
echo.
echo [2] Backend health
curl.exe -fsS http://127.0.0.1:8000/health
echo.
echo [3] Database / pipeline status
curl.exe -fsS http://127.0.0.1:8000/api/v1/system/status
echo.
echo [4] Thermal events
curl.exe -fsS "http://127.0.0.1:8000/api/v1/events?limit=5"
echo.
echo [5] Industrial facilities
curl.exe -fsS "http://127.0.0.1:8000/api/v1/facilities?limit=5"
echo.
echo [6] Risk intelligence
curl.exe -fsS "http://127.0.0.1:8000/api/v1/risk/summary"
echo.
pause
endlocal
