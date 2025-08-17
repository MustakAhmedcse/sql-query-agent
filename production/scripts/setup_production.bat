@echo off
REM Production Deployment Script for Windows
REM SQL Query Agent - Production Setup

echo.
echo ========================================
echo SQL Query Agent - Production Setup
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install production requirements
echo Installing production requirements...
pip install -r requirements.txt
pip install -r production\requirements-prod.txt

REM Create necessary directories
echo Creating directories...
if not exist "logs" mkdir logs
if not exist "data\training_data" mkdir data\training_data
if not exist "data\embeddings" mkdir data\embeddings

REM Copy environment file
if not exist ".env" (
    echo Creating .env file from template...
    copy production\config\.env.production .env
    echo.
    echo IMPORTANT: Edit .env file with your production settings!
    echo.
)

REM Copy uvicorn config to root
if not exist "uvicorn_config.py" (
    echo Copying Uvicorn configuration...
    copy production\config\uvicorn_config.py uvicorn_config.py
)

REM Copy logging config to root
if not exist "logging.conf" (
    echo Copying logging configuration...
    copy production\config\logging.conf logging.conf
)

REM Setup training data if source exists
if exist "data\srf_sql_pairs.jsonl" (
    echo Setting up training data...
    python run.py setup
) else (
    echo Warning: Training data file not found at data\srf_sql_pairs.jsonl
    echo Please add your training data before starting the application.
)

echo.
echo ========================================
echo Production Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit .env file with your production settings
echo 2. Add your training data to data\srf_sql_pairs.jsonl
echo 3. Run: production\scripts\start_production.bat
echo.
pause
