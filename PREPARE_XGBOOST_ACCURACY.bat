@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo ThermoIntel - Prepare XGBoost Accuracy Dataset
echo ================================================
echo.
python scripts\export_xgboost_training_candidates.py
if errorlevel 1 (
  echo.
  echo Failed to export candidates. Make sure the backend/database is running.
  exit /b 1
)
echo.
echo Candidate file created:
echo data\xgboost_training_candidates.csv
echo.
echo Open that CSV and fill the reviewed_label column using ONLY human-reviewed evidence.
echo Copy the reviewed rows into data\ml_labels.csv using:
echo event_id,label,reviewer,notes
pause
