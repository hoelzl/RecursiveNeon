@echo off
REM Setup script for Recursive://Neon (Windows)

echo ==========================================
echo Recursive://Neon - Setup Script
echo ==========================================
echo.

REM Check Python
echo [1/6] Checking Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python 3 is required but not installed.
    echo Please install Python from https://www.python.org/
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo √ Python %PYTHON_VERSION% found
echo.

REM Setup Python backend
echo [2/6] Setting up Python backend...
cd backend

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

cd ..
echo √ Backend setup complete
echo.

REM Setup Node.js frontend
echo [3/6] Checking Node.js...
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Node.js is required but not installed.
    echo Please install Node.js from https://nodejs.org/
    exit /b 1
)

for /f "tokens=1" %%i in ('node --version') do set NODE_VERSION=%%i
echo √ Node.js %NODE_VERSION% found
echo.

echo [4/6] Setting up frontend...
cd frontend
call npm install
cd ..
echo √ Frontend setup complete
echo.

REM Download ollama
echo [5/6] Downloading ollama...
python scripts\download_ollama.py
echo √ Ollama downloaded
echo.

echo [6/6] Setup complete!
echo.

echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo To run the game:
echo   1. Start backend:  cd backend ^&^& venv\Scripts\activate ^&^& python main.py
echo   2. Start frontend: cd frontend ^&^& npm run dev
echo   3. Open browser:   http://localhost:5173
echo.
echo Note: You need to have a compatible model in ollama.
echo Run: ollama pull phi3:mini
echo.

pause
