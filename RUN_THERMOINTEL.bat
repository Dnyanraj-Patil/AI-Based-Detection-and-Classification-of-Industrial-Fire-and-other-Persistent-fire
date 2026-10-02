@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ========================================
echo ThermoIntel - START
echo ========================================
echo.

echo [1/6] Stopping previous ThermoIntel containers...
docker compose down --remove-orphans >nul 2>&1
if errorlevel 1 echo [WARN] Previous stack could not be stopped cleanly. Continuing...

echo.
echo [2/6] Building ThermoIntel images...
echo       Using Docker cache for faster normal startup.

docker compose build backend osm-ingest dashboard

if errorlevel 1 (
  echo.
  echo BUILD FAILED - Docker image build failed.
  docker compose ps
  pause
  exit /b 1
)

echo [OK] ThermoIntel images are ready.

docker compose up -d postgres redis backend dashboard

if errorlevel 1 (
  echo.
  echo START FAILED - Docker Compose could not start the stack.
  docker compose ps
  echo.
  echo ---- Backend logs ----
  docker compose logs --tail=150 backend
  pause
  exit /b 1
)

echo.
echo [3/6] Waiting for backend and database health...
set READY=0

for /L %%I in (1,1,90) do (
  curl.exe -fsS http://127.0.0.1:8000/health >nul 2>&1

  if not errorlevel 1 (
    set READY=1
    goto :backend_ready
  )

  timeout /t 2 /nobreak >nul
)

:backend_ready

if "%READY%"=="0" (
  echo [FAIL] Backend did not become healthy within 180 seconds.
  docker compose ps
  echo.
  echo ---- Backend logs ----
  docker compose logs --tail=200 backend
  pause
  exit /b 1
)

echo [OK] Backend and PostGIS are healthy.

echo.
echo [4/6] Waiting for NASA FIRMS thermal data...
set DATA_READY=0

for /L %%I in (1,1,120) do (

  powershell -NoProfile -Command "$s=Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/system/status' -ErrorAction Stop; if ([int]$s.counts.thermal_events -gt 0) { exit 0 } else { exit 1 }" >nul 2>&1

  if not errorlevel 1 (
    set DATA_READY=1
    goto :data_ready
  )

  timeout /t 2 /nobreak >nul
)

:data_ready

if "%DATA_READY%"=="0" (
  echo [WARN] No thermal events are available yet.
  echo       FIRMS may be temporarily unavailable.
  echo       The backend will retry automatically.
) else (
  echo [OK] Thermal event data is available.
)

echo.
echo [5/6] Ensuring industrial facilities are available...

set FAC_READY=0

powershell -NoProfile -Command "$s=Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/system/status' -ErrorAction Stop; if ([int]$s.counts.facilities -gt 0) { exit 0 } else { exit 1 }" >nul 2>&1

if not errorlevel 1 (

  set FAC_READY=1
  echo [OK] Industrial facilities already present.

) else (

  echo [INFO] Facility database is empty.
  echo [INFO] Running India-wide OSM ingestion...
  echo.

  docker compose run --rm osm-ingest

  if errorlevel 1 (
    echo.
    echo [WARN] OSM ingestion failed.
    echo       The dashboard will remain usable.
    echo       You can retry later with:
    echo       docker compose run --rm osm-ingest
  ) else (
    set FAC_READY=1
    echo [OK] Industrial facility ingestion completed.
  )
)

echo.
echo [6/6] Running intelligence pipeline...
echo       Processing industrial context, classification,
echo       probable cause and risk intelligence.
echo.

docker compose exec -T backend python process_intelligence_pipeline.py

if errorlevel 1 (
  echo.
  echo [WARN] Intelligence pipeline failed.
  echo       Showing backend diagnostics...
  echo.
  docker compose logs --tail=120 backend
) else (
  echo.
  echo [OK] Industrial context completed.
  echo [OK] Event classification completed.
  echo [OK] Probable-cause assessment completed.
  echo [OK] Risk scoring completed.
)

echo.
echo ========================================
echo THERMOINTEL IS READY
echo ========================================
echo.
echo Dashboard: http://localhost:5173
echo Backend:   http://localhost:8000/health
echo Status:    http://localhost:8000/api/v1/system/status
echo.
echo Data:      NASA FIRMS near-real-time thermal detections
echo Context:   OpenStreetMap + PostGIS industrial infrastructure
echo AI:        XGBoost source classification + explainable evidence guardrails
echo Risk:      Thermal + persistence + industrial evidence fusion
echo.
echo Keep Docker Desktop running while demonstrating ThermoIntel.
echo Press any key to close this window (containers remain running).
pause >nul

endlocal