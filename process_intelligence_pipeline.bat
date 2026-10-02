@echo off
setlocal
cd /d "%~dp0"
echo ========================================
echo ThermoIntel - INTELLIGENCE REPROCESS
 echo ========================================
echo.
docker compose exec -T backend python process_intelligence_pipeline.py
if errorlevel 1 (
  echo.
  echo PIPELINE FAILED. Backend logs:
  docker compose logs --tail=150 backend
  pause
  exit /b 1
)
echo.
echo Pipeline completed successfully.
echo Current database state:
curl.exe -fsS http://127.0.0.1:8000/api/v1/system/status
echo.
pause
endlocal
