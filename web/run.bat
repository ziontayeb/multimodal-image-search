@echo off
REM Image Search Web UI Startup Script (Windows)

echo ================================
echo Image Search Web UI
echo ================================
echo.

REM Check if we're in the right directory
if not exist "app.py" (
    echo Error: app.py not found!
    echo Please run this script from the web\ directory
    pause
    exit /b 1
)

REM Check for .env file
if not exist "..\\.env" (
    echo Warning: .env file not found in project root!
    echo You'll need to configure API keys in the Settings page.
    echo.
)

REM Check if Flask is installed
python -c "import flask" 2>nul
if errorlevel 1 (
    echo Error: Flask not installed!
    echo Please run: pip install -r ..\requirements.txt
    pause
    exit /b 1
)

echo Starting server...
echo.
echo Web UI will be available at:
echo   http://localhost:5001
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start Flask app
python app.py
