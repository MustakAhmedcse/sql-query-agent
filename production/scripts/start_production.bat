@echo off
REM Start SQL Query Agent in Production Mode

echo.
echo ========================================
echo Starting SQL Query Agent - Production
echo ========================================
echo.

REM Change to project root directory
cd /d "%~dp0..\.."

REM Check if virtual environment exists
if not exist ".venv" (
    echo Error: Virtual environment not found!
    echo Please run production\scripts\setup_production.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Set UTF-8 encoding for Python (fixes Unicode emoji logging issues)
set PYTHONIOENCODING=utf-8

REM Check if .env file exists
if not exist ".env" (
    echo Error: .env file not found!
    echo Please copy production\config\.env.production to .env and configure it
    pause
    exit /b 1
)

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Copy logging config if not exists
if not exist "logging.conf" (
    echo Copying logging configuration...
    copy production\config\logging.conf logging.conf
)

REM Start the application with Uvicorn (Windows compatible)
echo Starting application with Uvicorn...
echo Calculating optimal workers based on CPU cores...

REM Get worker count from Python config
for /f "tokens=*" %%i in ('python -c "import sys; sys.path.append('production/config'); from uvicorn_config import workers; print(workers)"') do set WORKER_COUNT=%%i

echo Using %WORKER_COUNT% workers for optimal performance
echo Server will be available at: http://localhost:8000
echo Logs will be written to: logs/app.log and logs/access.log
echo Press Ctrl+C to stop the server
echo.

uvicorn web.app:app --host 0.0.0.0 --port 8000 --workers %WORKER_COUNT% --log-config logging.conf

echo.
echo Application stopped.
pause
