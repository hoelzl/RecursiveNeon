@echo off
REM Build script for Windows - Creates redistributable NPC LLM system
REM Requirements: Miniconda or Anaconda installed

echo ========================================
echo NPC LLM System - Windows Build Script
echo ========================================
echo.

REM Check if conda is available
where conda >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Conda not found. Please install Miniconda from:
    echo https://docs.conda.io/en/latest/miniconda.html
    exit /b 1
)

echo [1/6] Creating conda environment...
call conda env create -f environment.yml -y
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Environment already exists, updating instead...
    call conda env update -f environment.yml
)

echo.
echo [2/6] Activating environment...
call conda activate npc-llm-build

echo.
echo [3/6] Downloading pre-built llama.cpp binaries...
mkdir libs 2>nul
cd libs

REM Download latest llama.cpp release for Windows
REM Using PowerShell to download
powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/ggerganov/llama.cpp/releases/latest/download/llama-b4330-bin-win-cuda-cu12.2.0-x64.zip' -OutFile 'llama-cpp-cuda.zip'}"
powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/ggerganov/llama.cpp/releases/latest/download/llama-b4330-bin-win-openblas-x64.zip' -OutFile 'llama-cpp-cpu.zip'}"

REM Extract binaries
powershell -Command "& {Expand-Archive -Path 'llama-cpp-cuda.zip' -DestinationPath 'cuda' -Force}"
powershell -Command "& {Expand-Archive -Path 'llama-cpp-cpu.zip' -DestinationPath 'cpu' -Force}"

cd ..

echo.
echo [4/6] Installing Python dependencies with pre-built wheels...

REM Use pre-built llama-cpp-python wheel (CPU version for compatibility)
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

REM Install remaining dependencies
pip install -r requirements.txt

echo.
echo [5/6] Building distributable package with PyInstaller...
python build_executable.py

echo.
echo [6/6] Build complete!
echo.
echo Output location: dist\npc-llm-system\
echo.
echo To test: cd dist\npc-llm-system ^&^& npc-llm-system.exe
echo.
echo To distribute: Copy the entire dist\npc-llm-system folder
echo                (includes models, configs, and all dependencies)

call conda deactivate
