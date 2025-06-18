@echo off
echo ========================================
echo Commission AI Assistant - Quick Start
echo ========================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check Python version (must be 3.8+)
python -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3.8+ is required
    echo Please upgrade Python from https://python.org
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "commission_env" (
    echo Creating virtual environment...
    python -m venv commission_env
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call commission_env\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Upgrade pip first
echo Upgrading pip and setuptools...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo Warning: Failed to upgrade pip/setuptools, continuing...
)

REM Install dependencies step by step
echo Installing core dependencies...
python -m pip install fastapi uvicorn pydantic requests numpy pandas
if errorlevel 1 (
    echo Error: Failed to install core dependencies
    pause
    exit /b 1
)

echo Installing AI libraries...
python -m pip install torch transformers sentence-transformers
if errorlevel 1 (
    echo Error: Failed to install AI libraries
    echo Trying alternative installation...
    python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    python -m pip install transformers sentence-transformers
)

echo Installing remaining dependencies...
python -m pip install chromadb ollama openpyxl python-docx PyPDF2 python-multipart jinja2 python-dotenv
if errorlevel 1 (
    echo Warning: Some dependencies may have failed to install
    echo System may still work with basic functionality
)

REM Ask user what to do
echo.
echo Installation completed (with possible warnings)
echo.
echo Choose an option:
echo 1. Setup training data (first time only)
echo 2. Start web interface
echo 3. Start CLI interface  
echo 4. Run tests
echo 5. Exit
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" (
    echo Setting up training data...
    python run.py setup
    pause
) else if "%choice%"=="2" (
    echo Starting web interface...
    echo Open http://localhost:8000 in your browser
    python run.py web
) else if "%choice%"=="3" (
    echo Starting CLI interface...
    python run.py cli
    pause
) else if "%choice%"=="4" (
    echo Running tests...
    python test.py
    pause
) else if "%choice%"=="5" (
    echo Goodbye!
    exit /b 0
) else (
    echo Invalid choice!
    pause
)

deactivate
