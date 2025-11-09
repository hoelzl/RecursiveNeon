@echo off
REM Enhanced build script that bundles micromamba for completely portable distribution
REM This creates a distribution where users can optionally use conda features

echo ========================================
echo NPC LLM System - Portable Build with Micromamba
echo ========================================
echo.

REM Check if conda is available for building
where conda >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Conda not found. You still need conda for building!
    echo Install Miniconda from: https://docs.conda.io/en/latest/miniconda.html
    exit /b 1
)

echo [1/7] Creating conda environment for building...
call conda env create -f environment.yml -y
if %ERRORLEVEL% NEQ 0 (
    echo Environment already exists, updating...
    call conda env update -f environment.yml
)

echo.
echo [2/7] Activating environment...
call conda activate npc-llm-build

echo.
echo [3/7] Downloading micromamba for portable distribution...
mkdir portable_conda 2>nul
cd portable_conda

REM Download micromamba (standalone, ~20MB)
echo Downloading micromamba...
powershell -Command "& {Invoke-WebRequest -Uri 'https://micro.mamba.pm/api/micromamba/win-64/latest' -OutFile 'micromamba.tar.bz2'}"

REM Extract micromamba
echo Extracting micromamba...
powershell -Command "& {tar -xf micromamba.tar.bz2}"

REM Verify
if not exist "Library\bin\micromamba.exe" (
    echo ERROR: Failed to extract micromamba
    exit /b 1
)

cd ..

echo.
echo [4/7] Downloading pre-built llama.cpp binaries...
mkdir libs 2>nul
cd libs

powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/ggerganov/llama.cpp/releases/latest/download/llama-b4330-bin-win-cuda-cu12.2.0-x64.zip' -OutFile 'llama-cpp-cuda.zip'}"
powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/ggerganov/llama.cpp/releases/latest/download/llama-b4330-bin-win-openblas-x64.zip' -OutFile 'llama-cpp-cpu.zip'}"

powershell -Command "& {Expand-Archive -Path 'llama-cpp-cuda.zip' -DestinationPath 'cuda' -Force}"
powershell -Command "& {Expand-Archive -Path 'llama-cpp-cpu.zip' -DestinationPath 'cpu' -Force}"

cd ..

echo.
echo [5/7] Installing Python dependencies...
pip install -r requirements.txt

echo.
echo [6/7] Building distributable package with PyInstaller...
python build_executable_with_micromamba.py

echo.
echo [7/7] Finalizing portable distribution...
REM Copy micromamba to distribution
xcopy /E /I /Y portable_conda dist\npc-llm-system\portable_conda

echo.
echo ========================================
echo Build complete!
echo ========================================
echo.
echo Distribution location: dist\npc-llm-system\
echo.
echo This distribution now includes:
echo   - All Python dependencies (bundled)
echo   - llama.cpp binaries (CPU and CUDA)
echo   - Micromamba (optional advanced features)
echo   - Your application
echo.
echo Users can run without any installation!
echo For advanced features, they can use the bundled micromamba.
echo.

call conda deactivate
