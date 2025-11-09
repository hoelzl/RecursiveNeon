# Windows Build and Distribution Guide

This guide explains how to build a **distributable** NPC LLM system that works on any Windows machine, with or without CUDA.

## Overview

This setup uses:
- **Conda/Miniconda**: Provides all binary dependencies (no manual BLAS installation)
- **Pre-built llama.cpp binaries**: No compilation required
- **Runtime CUDA detection**: Automatically uses GPU if available, CPU otherwise
- **PyInstaller**: Creates a single distributable folder

## Build Machine Requirements

You need **ONE** machine with Visual Studio to build the distributable package:

- Windows 10/11 (64-bit)
- Visual Studio 2019 or newer (Community Edition is fine)
  - Download: https://visualstudio.microsoft.com/downloads/
  - Only need "Desktop development with C++"
- 10GB free disk space for build environment
- Internet connection (for downloading dependencies)

**Important**: After building, the output works on machines **WITHOUT** Visual Studio or other dependencies.

## Step 1: Install Miniconda (One-time)

If you don't have conda installed:

```bash
# Download Miniconda installer
# Visit: https://docs.conda.io/en/latest/miniconda.html
# Get: Miniconda3 Windows 64-bit installer

# Run the installer (Miniconda3-latest-Windows-x86_64.exe)
# Important: Check "Add Miniconda3 to PATH" during installation
```

Verify installation:
```bash
conda --version
# Should show: conda 23.x.x or similar
```

## Step 2: Download the Project

```bash
# Clone or download your project
cd C:\path\to\npc-llm-system
```

## Step 3: Run the Build Script

This is the **one command** that does everything:

```bash
build_windows.bat
```

This script:
1. ✅ Creates conda environment with all dependencies (including BLAS)
2. ✅ Downloads pre-built llama.cpp binaries (CPU and CUDA versions)
3. ✅ Installs Python packages
4. ✅ Builds distributable with PyInstaller

**Total time**: ~10-15 minutes (first time)

### What the Build Creates

```
dist/npc-llm-system/           # ← Distributable folder
├── npc-llm-system.exe         # Main executable
├── libs/
│   ├── cpu/                   # CPU-only llama.cpp server
│   │   └── llama-server.exe
│   └── cuda/                  # CUDA-enabled llama.cpp server
│       └── llama-server.exe
├── models/                    # Place .gguf models here
├── _internal/                 # Python runtime + dependencies
└── README.txt                 # User instructions
```

## Step 4: Add a Model

Download a GGUF model and place it in the `models/` directory:

```bash
# Example: Download Mistral 7B (4GB)
cd dist\npc-llm-system\models
curl -L -O https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf
```

Or download manually from HuggingFace and copy to `models/`.

## Step 5: Test Locally

```bash
cd dist\npc-llm-system
npc-llm-system.exe
```

The system will:
1. Detect if you have CUDA
2. Select the appropriate server binary (cuda/llama-server.exe or cpu/llama-server.exe)
3. Start the server
4. Load the model
5. Be ready for requests

## Step 6: Create Distribution Package

```bash
# Zip the entire folder
cd dist
powershell Compress-Archive -Path npc-llm-system -DestinationPath npc-llm-system-v1.0.zip
```

**This zip file is your distributable!** It includes:
- All binaries
- Python runtime
- Dependencies
- Both CPU and CUDA server versions

## Distribution to End Users

### User Requirements (Minimal!)

End users need **nothing** except:
- Windows 10/11 (64-bit)
- 8GB RAM (16GB recommended)
- Optional: NVIDIA GPU for better performance

**They do NOT need:**
- Python
- Visual Studio
- CUDA Toolkit
- Any development tools

### User Installation

1. Extract the zip file
2. Put a `.gguf` model in the `models/` folder
3. Run `npc-llm-system.exe`

Done!

### Runtime CUDA Detection

The system automatically detects at runtime:

```
User has NVIDIA GPU? 
├─ YES → Uses libs/cuda/llama-server.exe (fast)
└─ NO  → Uses libs/cpu/llama-server.exe (slower but works)
```

**No configuration needed** - it just works!

## Integration with Your Game

### Option 1: As a Subprocess (Recommended)

Your game starts/stops the server:

```python
from llm_controller_server import LLMController

# In your game initialization
controller = LLMController(
    model_path="models/mistral-7b-instruct.gguf",
    port=8080
)

await controller.start()  # Starts the server

# Use it
response = await controller.generate("Your prompt")

# On game exit
await controller.shutdown()  # Stops the server
```

### Option 2: Always Running

Start the server when the game launches, keep it running:

```python
# On game start
await controller.start()

# Server stays running
# Make requests as needed
response1 = await controller.generate("Prompt 1")
response2 = await controller.generate("Prompt 2")

# On game exit
await controller.shutdown()
```

## Troubleshooting Build Issues

### "conda: command not found"

**Problem**: Conda not in PATH

**Solution**:
```bash
# Option 1: Add conda to PATH manually
# Find conda installation (usually C:\Users\YourName\miniconda3)
# Add C:\Users\YourName\miniconda3\Scripts to System PATH

# Option 2: Use Anaconda Prompt (comes with Miniconda)
# Search for "Anaconda Prompt" in Start menu
# Run build_windows.bat from there
```

### "Failed to download llama.cpp binaries"

**Problem**: Network issue or GitHub rate limit

**Solution**:
```bash
# Manual download:
# Visit: https://github.com/ggerganov/llama.cpp/releases
# Download:
#   - llama-*-bin-win-cuda-cu12.2.0-x64.zip
#   - llama-*-bin-win-openblas-x64.zip
# 
# Extract to:
#   libs/cuda/
#   libs/cpu/
```

### "PyInstaller failed to build"

**Problem**: Missing dependencies

**Solution**:
```bash
# Activate environment and try manually
conda activate npc-llm-build
pip install pyinstaller --upgrade
python build_executable.py
```

### Build succeeds but executable crashes

**Problem**: Missing runtime dependencies

**Solution**:
```bash
# Rebuild with explicit includes
# Edit build_executable.py, add to hidden imports:
'--hidden-import=your_missing_module',
```

## Advanced Configuration

### Custom Server Port

```python
controller = LLMController(
    model_path="models/your-model.gguf",
    port=8081  # Use different port
)
```

### Force CPU or GPU Mode

```python
# Force CPU (even if CUDA available)
controller = LLMController(
    model_path="models/your-model.gguf",
    n_gpu_layers=0  # CPU only
)

# Force GPU (will fail if no CUDA)
controller = LLMController(
    model_path="models/your-model.gguf",
    n_gpu_layers=99  # All layers on GPU
)
```

### Reduce Memory Usage

```python
controller = LLMController(
    model_path="models/your-model.gguf",
    n_ctx=1024,  # Smaller context window
    max_tokens=128  # Shorter responses
)
```

## Performance Testing

Test on different hardware:

```python
# In your test script
import asyncio
from llm_controller_server import LLMController

async def benchmark():
    controller = LLMController(
        model_path="models/mistral-7b-instruct.gguf"
    )
    
    await controller.start()
    
    # Benchmark
    import time
    start = time.time()
    response = await controller.generate("Test prompt" * 10)
    duration = time.time() - start
    
    status = controller.get_status()
    print(f"Response time: {duration:.2f}s")
    print(f"Tokens/sec: {status['metrics']['avg_tokens_per_sec']:.1f}")
    
    await controller.shutdown()

asyncio.run(benchmark())
```

## Updating the Distribution

To update your distributed version:

```bash
# 1. Make code changes
# 2. Rebuild
build_windows.bat

# 3. Test
cd dist\npc-llm-system
npc-llm-system.exe

# 4. Create new distribution zip
cd dist
powershell Compress-Archive -Path npc-llm-system -DestinationPath npc-llm-system-v1.1.zip -Force
```

## File Size Expectations

Approximate sizes:

| Component | Size |
|-----------|------|
| Python runtime + deps | ~150 MB |
| llama.cpp CPU binary | ~50 MB |
| llama.cpp CUDA binary | ~150 MB |
| **Base package** | **~350 MB** |
| + Model (7B Q4) | +4 GB |
| + Model (3B Q4) | +2 GB |
| **Total distribution** | **2-4 GB** |

## Distribution Strategies

### Strategy 1: All-in-One (Recommended for testing)
- Include a small model (~2GB) in the distribution
- Users can immediately test it
- Larger models downloadable separately

### Strategy 2: Separate Downloads
- Base package: 350 MB
- Models: User downloads separately
- Smaller initial download

### Strategy 3: Model Manager
- Package includes downloader
- User selects model on first run
- Downloads and caches automatically

## Licensing Notes

When distributing, you're including:
- llama.cpp (MIT License) ✅
- Your code (your license)
- Python runtime (PSF License) ✅
- Model (check model card - usually MIT/Apache 2.0) ⚠️

**Always check the model license!** Most are permissive but some have restrictions.

## Next Steps

1. ✅ Build the distributable package
2. ✅ Test on your development machine
3. ✅ Test on a clean Windows machine (VM or friend's PC)
4. ✅ Test with and without NVIDIA GPU
5. ✅ Integrate with your game
6. ✅ Profile performance and memory usage
7. ✅ Create user documentation
8. ✅ Package for distribution

## Summary

**Build once** on a machine with Visual Studio and conda.

**Distribute everywhere** - works on any Windows 10/11 machine, automatically adapts to hardware (GPU or CPU).

**No end-user dependencies** required!

This approach solves the compilation/dependency problem by:
1. Using conda for build dependencies
2. Using pre-built binaries (no compilation)
3. Including both CPU and CUDA versions
4. Detecting at runtime which to use
5. Bundling everything in a single folder

Users just extract, add a model, and run. It's as close to "just works" as possible for LLM distribution.
