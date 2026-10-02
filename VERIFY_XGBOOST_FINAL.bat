@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo ThermoIntel XGBoost Release Verification
echo ================================================

where python >nul 2>&1 || (echo ERROR: Python is not installed.& exit /b 1)

set PYTHONPATH=backend
python -m compileall -q backend scripts
if errorlevel 1 (echo ERROR: Python compilation failed.& exit /b 1)

echo [OK] Python source compilation

python -c "import xgboost; print('[OK] XGBoost', xgboost.__version__)"
if errorlevel 1 (echo ERROR: XGBoost is not installed.& exit /b 1)

python -c "from pathlib import Path; p=Path('backend/app/services/xgboost_classifier_service.py').read_text(encoding='utf-8'); assert 'XGBClassifier' in p and 'IsolationForest' not in p; print('[OK] XGBoost classifier active; Isolation Forest removed')"
if errorlevel 1 (echo ERROR: ML classifier verification failed.& exit /b 1)

if not exist .env (
  echo WARNING: .env not found. Copy .env.example to .env and set FIRMS_MAP_KEY.
) else (
  echo [OK] .env present
)

echo.
echo Verification complete.
echo NOTE: A real XGBoost model is trained automatically after the database has at least 40 usable thermal events and at least two classes with five examples each.
endlocal
