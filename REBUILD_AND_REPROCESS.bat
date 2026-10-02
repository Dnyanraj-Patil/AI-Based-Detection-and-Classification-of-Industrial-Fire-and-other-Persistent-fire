@echo off
setlocal
cd /d "%~dp0"
echo ========================================
echo ThermoIntel - REBUILD + REPROCESS
echo ========================================
echo.
echo This keeps the existing database volume.
echo It rebuilds the backend/dashboard images and then
echo asks the backend to reprocess recent classifications.
echo.

docker compose down --remove-orphans
if errorlevel 1 (
  echo Failed to stop Docker services.
  pause
  exit /b 1
)

docker compose up -d --build
if errorlevel 1 (
  echo Build/start failed. Run: docker compose logs --tail=150
  pause
  exit /b 1
)

echo Waiting for backend health...
set /a tries=0
:waitloop
set /a tries+=1
curl -fsS http://127.0.0.1:8000/health >nul 2>&1
if not errorlevel 1 goto healthy
if %tries% GEQ 60 goto timeout
timeout /t 2 /nobreak >nul
goto waitloop

:healthy
echo Backend is healthy.
echo.
echo Requesting recent-event reprocessing...
curl -s -X POST http://127.0.0.1:8000/api/v1/system/reprocess
echo.
echo.
echo ========================================
echo ThermoIntel rebuilt successfully
echo Dashboard: http://localhost:5173
echo API:       http://localhost:8000/health
echo ========================================
echo.
pause
exit /b 0

:timeout
echo Backend did not become healthy within 120 seconds.
echo Run: docker compose logs --tail=150 backend
pause
exit /b 1
