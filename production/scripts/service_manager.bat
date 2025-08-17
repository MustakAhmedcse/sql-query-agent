@echo off
REM SQL Query Agent - Service Management Script

echo.
echo ========================================
echo SQL Query Agent - Service Management
echo ========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Error: This script must be run as Administrator!
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Change to project root directory
cd /d "%~dp0..\.."

REM Check command line argument
set "action=%1"
if "%action%"=="" set "action=help"

if /i "%action%"=="install" goto install
if /i "%action%"=="uninstall" goto uninstall
if /i "%action%"=="start" goto start
if /i "%action%"=="stop" goto stop
if /i "%action%"=="restart" goto restart
if /i "%action%"=="status" goto status
if /i "%action%"=="logs" goto logs
if /i "%action%"=="test" goto test
goto help

:install
echo Installing SQL Query Agent as Windows Service...

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo Error: Virtual environment Python not found at .venv\Scripts\python.exe
    echo Please run setup_production.bat first to create the virtual environment
    goto end
)

echo Using virtual environment Python: .venv\Scripts\python.exe
.venv\Scripts\python.exe production\service.py install
if %errorlevel% equ 0 (
    echo Service installed successfully!
    echo Use "service_manager.bat start" to start the service
) else (
    echo Failed to install service!
)
goto end

:uninstall
echo Removing SQL Query Agent Windows Service...

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo Error: Virtual environment Python not found at .venv\Scripts\python.exe
    echo Please run setup_production.bat first to create the virtual environment
    goto end
)

echo Using virtual environment Python: .venv\Scripts\python.exe
.venv\Scripts\python.exe production\service.py stop 2>nul
.venv\Scripts\python.exe production\service.py remove
if %errorlevel% equ 0 (
    echo Service removed successfully!
) else (
    echo Failed to remove service!
)
goto end

:start
echo Starting SQL Query Agent service...

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo Error: Virtual environment Python not found at .venv\Scripts\python.exe
    echo Please run setup_production.bat first to create the virtual environment
    goto end
)

echo Using virtual environment Python: .venv\Scripts\python.exe
.venv\Scripts\python.exe production\service.py start
if %errorlevel% equ 0 (
    echo Service started successfully!
    echo Application will be available at: http://localhost:8000
) else (
    echo Failed to start service!
    echo Check Windows Event Viewer for details
)
goto end

:stop
echo Stopping SQL Query Agent service...

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo Error: Virtual environment Python not found at .venv\Scripts\python.exe
    echo Please run setup_production.bat first to create the virtual environment
    goto end
)

echo Using virtual environment Python: .venv\Scripts\python.exe
.venv\Scripts\python.exe production\service.py stop
if %errorlevel% equ 0 (
    echo Service stopped successfully!
) else (
    echo Failed to stop service!
)
goto end

:restart
echo Restarting SQL Query Agent service...

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo Error: Virtual environment Python not found at .venv\Scripts\python.exe
    echo Please run setup_production.bat first to create the virtual environment
    goto end
)

echo Using virtual environment Python: .venv\Scripts\python.exe
.venv\Scripts\python.exe production\service.py restart
if %errorlevel% equ 0 (
    echo Service restarted successfully!
    echo Application will be available at: http://localhost:8000
) else (
    echo Failed to restart service!
)
goto end

:status
echo Checking SQL Query Agent service status...
sc query SQLQueryAgent
echo.
echo Checking if application is responding on port 8000...
powershell -Command "try { $result = Test-NetConnection -ComputerName localhost -Port 8000 -WarningAction SilentlyContinue; if ($result.TcpTestSucceeded) { Write-Host 'Application is accessible on http://localhost:8000' -ForegroundColor Green } else { Write-Host 'Application is not responding on port 8000' -ForegroundColor Red } } catch { Write-Host 'Unable to test port 8000' -ForegroundColor Yellow }"
goto end

:logs
echo Showing recent service logs...
echo.
echo === Service Wrapper Log (last 20 lines) ===
if exist "logs\service-wrapper.log" (
    powershell -Command "Get-Content 'logs\service-wrapper.log' -Tail 20"
) else (
    echo No service wrapper log found
)
echo.
echo === Uvicorn Application Log (last 20 lines) ===
if exist "logs\uvicorn-service.log" (
    powershell -Command "Get-Content 'logs\uvicorn-service.log' -Tail 20"
) else (
    echo No uvicorn log found
)
goto end

:test
echo Testing service configuration...
echo.
if not exist ".venv\Scripts\python.exe" (
    echo [FAIL] Virtual environment Python not found
    goto end
)
echo [PASS] Virtual environment Python found

.venv\Scripts\python.exe -c "import sys; print(f'[INFO] Python version: {sys.version}')"
.venv\Scripts\python.exe -c "try: import win32serviceutil, win32service, win32event, servicemanager; print('[PASS] Windows service modules available') except ImportError as e: print(f'[FAIL] Windows service modules missing: {e}')"
.venv\Scripts\python.exe -c "try: from production.service import SQLQueryAgentService; print('[PASS] Service class can be imported') except ImportError as e: print(f'[FAIL] Service import failed: {e}')"

echo.
echo Service configuration:
.venv\Scripts\python.exe -c "from production.service import SQLQueryAgentService; print(f'Service executable: {SQLQueryAgentService._exe_name_}'); print(f'Service script: {SQLQueryAgentService._exe_args_}')"
goto end

:help
echo.
echo USAGE:
echo   service_manager.bat [action]
echo.
echo ACTIONS:
echo   install    Install the service (requires Administrator)
echo   uninstall  Remove the service (requires Administrator)
echo   start      Start the service
echo   stop       Stop the service
echo   restart    Restart the service
echo   status     Show service status and check port 8000
echo   logs       Show recent service logs
echo   test       Test service configuration and dependencies
echo   help       Show this help
echo.
echo EXAMPLES:
echo   service_manager.bat install
echo   service_manager.bat start
echo   service_manager.bat status
echo   service_manager.bat logs
echo   service_manager.bat test
echo.
echo NOTE: This script must be run as Administrator
echo.

:end
echo.
pause
