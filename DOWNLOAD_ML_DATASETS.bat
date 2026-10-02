@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo ThermoIntel - Download ML datasets
echo ============================================================
python scripts\download_ml_datasets.py
if errorlevel 1 (
  echo.
  echo Dataset download failed. Check internet access and try again.
  exit /b 1
)
echo.
echo Datasets downloaded successfully.
pause
