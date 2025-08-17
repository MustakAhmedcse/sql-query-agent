@echo off
REM Update SQL Query Agent Application

echo.
echo ========================================
echo SQL Query Agent - Application Update
echo ========================================
echo.

REM Change to project root directory
cd /d "%~dp0..\.."

REM Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo Error: Virtual environment not found!
    pause
    exit /b 1
)

REM Create backup before update
echo Creating backup before update...
call production\scripts\backup_data.bat

REM Update dependencies
echo.
echo Updating Python packages...
pip install --upgrade pip
pip install -r requirements.txt --upgrade
pip install -r production\requirements-prod.txt --upgrade

REM Update training data if needed
if exist "data\srf_sql_pairs.jsonl" (
    echo.
    echo Updating training data...
    python run.py setup
)

echo.
echo ========================================
echo Update completed successfully!
echo ========================================
echo.
echo Please restart the application:
echo production\scripts\stop_production.bat
echo production\scripts\start_production.bat
echo.
pause
