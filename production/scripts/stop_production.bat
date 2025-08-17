@echo off
REM Stop SQL Query Agent Production Server

echo.
echo ========================================
echo Stopping SQL Query Agent - Production
echo ========================================
echo.

REM Change to project root directory
cd /d "%~dp0..\.."

REM Check if any Uvicorn processes are running
echo Stopping Uvicorn processes...
taskkill /IM uvicorn.exe /F 2>nul
if errorlevel 1 (
    echo No Uvicorn processes found running.
    REM Also try to kill Python processes running uvicorn
    for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /fo csv ^| findstr uvicorn') do (
        echo Stopping Python uvicorn process...
        taskkill /PID %%i /F 2>nul
    )
    if errorlevel 1 (
        echo No Python uvicorn processes found.
    ) else (
        echo Python uvicorn processes stopped.
    )
) else (
    echo Uvicorn processes stopped successfully.
)

echo.
pause
