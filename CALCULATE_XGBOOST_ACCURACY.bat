@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title ThermoIntel - Complete XGBoost Evaluation

echo ================================================================
echo   THERMOINTEL - COMPLETE XGBOOST MODEL EVALUATION
echo ================================================================
echo.
echo This single command calculates:
echo   Accuracy, Balanced Accuracy, Precision, Recall, F1, per-class metrics
echo   and the Confusion Matrix.
echo.
echo IMPORTANT: Human-reviewed labels are required for real accuracy.
echo The script will NEVER call model confidence or weak-label validation
 echo "ground-truth accuracy".
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python was not found on PATH.
  echo Install Python 3.10+ and run this file again.
  pause
  exit /b 1
)

python -c "import xgboost, sklearn, numpy, sqlalchemy, psycopg2" >nul 2>&1
if errorlevel 1 (
  echo Required Python packages are missing.
  echo Installing backend requirements...
  python -m pip install -r backend\requirements.txt
  if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
  )
)

echo.
echo Running complete evaluation...
echo.
python scripts\evaluate_xgboost_complete.py
set ERR=%ERRORLEVEL%

echo.
echo ================================================================
echo Reports are saved in:
echo   reports\xgboost_complete_evaluation.txt
echo   reports\xgboost_complete_evaluation.json
echo ================================================================
echo.
if not "%ERR%"=="0" (
  echo Evaluation did not complete. Read the error above.
)
pause
exit /b %ERR%
