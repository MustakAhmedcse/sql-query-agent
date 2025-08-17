@echo off
REM Backup Script for SQL Query Agent Data

echo.
echo ========================================
echo SQL Query Agent - Data Backup
echo ========================================
echo.

REM Change to project root directory
cd /d "%~dp0..\.."

REM Create backup directory with timestamp
REM Use PowerShell for timestamp (wmic is deprecated in newer Windows)
for /f "tokens=*" %%i in ('powershell -Command "Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'"') do set "timestamp=%%i"

set "backup_dir=production\backup\%timestamp%"
mkdir "%backup_dir%" 2>nul

echo Creating backup in: %backup_dir%
echo.

REM Backup data directory
if exist "data" (
    echo Backing up data directory...
    xcopy "data" "%backup_dir%\data" /E /I /Y
)

REM Backup configuration files
echo Backing up configuration files...
if exist ".env" copy ".env" "%backup_dir%\"
if exist "commission_mapping.json" copy "commission_mapping.json" "%backup_dir%\"
if exist "uvicorn_config.py" copy "uvicorn_config.py" "%backup_dir%\"

REM Backup logs (recent only)
if exist "logs" (
    echo Backing up recent logs...
    mkdir "%backup_dir%\logs" 2>nul
    forfiles /p logs /s /m *.log /d -7 /c "cmd /c copy @path %backup_dir%\logs\" 2>nul
)

REM Create backup info file
echo Creating backup info...
echo Backup created: %date% %time% > "%backup_dir%\backup_info.txt"
echo Computer: %COMPUTERNAME% >> "%backup_dir%\backup_info.txt"
echo User: %USERNAME% >> "%backup_dir%\backup_info.txt"

echo.
echo [SUCCESS] Backup completed successfully!
echo Location: %backup_dir%
echo.

REM Clean old backups (keep only last 10)
echo Cleaning old backups (keeping last 10)...
for /f "skip=10 delims=" %%d in ('dir production\backup /b /ad /o-d 2^>nul') do (
    rmdir "production\backup\%%d" /s /q 2>nul
    echo Removed old backup: %%d
)

echo.
pause
