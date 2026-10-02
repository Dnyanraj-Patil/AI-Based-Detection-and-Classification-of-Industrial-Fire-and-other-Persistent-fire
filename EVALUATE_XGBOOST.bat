@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo ThermoIntel - XGBoost Accuracy Evaluation
 echo ================================================
python scripts\evaluate_xgboost_reviewed.py
if errorlevel 2 (
  echo.
  echo No defensible ground-truth accuracy was produced.
  echo Add human-reviewed labels to data\ml_labels.csv and rerun.
  exit /b 2
)
pause
