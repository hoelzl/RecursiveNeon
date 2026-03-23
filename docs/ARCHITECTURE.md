# Architecture Decision: Why Ollama?

## Summary

Recursive://Neon uses **Ollama** for local LLM inference instead of llama.cpp or other alternatives. This document explains why.

## The Problem

Initial designs considered using llama.cpp directly, but this approach had critical issues:

1. **Build Complexity**: Requires compilation with CUDA toolkit, specific compilers, and platform-specific toolchains
2. **Distribution Challenge**: Different binaries needed for CUDA vs CPU, making end-user distribution fragile
3. **Dependency Hell**: Heavy build dependencies (Visual Studio tools, CMake, BLAS libraries, etc.)
4. **Portability Issues**: No guarantee of working on target machines with different GPU drivers

## The Solution: Ollama

Ollama solves these problems elegantly:

### Advantages

1. **Single Binary Distribution**
   - One executable for all platforms (Windows, Linux, macOS)
   - Automatic GPU detection with graceful CPU fallback
   - No compilation required
   - Self-contained (~500MB)

2. **Simple Integration**
   - Clean REST API (OpenAI-compatible)
   - Built-in model management
   - Easy process lifecycle management
   - LangChain compatible

3. **Robust Hardware Support**
   - Works on any hardware (CPU-only to high-end GPUs)
   - Automatic quantization selection
   - Graceful degradation under memory pressure
   - Built-in CUDA/ROCm/Metal support (auto-detected)

4. **Better Developer Experience**
   - Well-documented API
   - Active development and community
   - Easy to test and debug
   - Stable API surface

### Trade-offs

**What we lose:**
- Slightly higher memory overhead (~100MB more)
- Less fine-grained control over inference parameters
- Slightly slower cold start (~2-3 seconds more)

**What we gain:**
- Vastly simpler distribution (critical for a game!)
- No build complexity
- Better cross-platform support
- Easier to test and debug
- More reliable for end users

**Verdict**: For a game distribution scenario, these trade-offs heavily favor Ollama.

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│     React Frontend (Desktop UI)             │
│     - Window Manager                        │
│     - Chat Interface                        │
│     - WebSocket Client                      │
└───────────────┬─────────────────────────────┘
                │ WebSocket + HTTP
┌───────────────▼─────────────────────────────┐
│     FastAPI Backend                         │
│     - WebSocket Handler                     │
│     - NPC Manager (LangChain)               │
│     - Process Orchestrator                  │
└───────────────┬─────────────────────────────┘
                │ HTTP (localhost:11434)
┌───────────────▼─────────────────────────────┐
│     Ollama Server                           │
│     - LLM Inference (auto GPU/CPU)          │
│     - Model Loading                         │
│     - OpenAI-compatible API                 │
└─────────────────────────────────────────────┘
```

## Key Components

### Backend (Python + FastAPI)
- Manages game state and NPC orchestration
- Uses LangChain for conversation management
- Spawns and monitors Ollama process
- Provides WebSocket API for frontend

### Frontend (React + TypeScript)
- Desktop-like UI with window management
- Real-time chat interface
- WebSocket connection to backend

### Ollama
- Bundled with the game distribution
- Automatically started by backend
- Provides LLM inference for all NPCs
- No external API keys or network required

## Development Setup

The simplified architecture means setup is straightforward:

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install Node dependencies
cd frontend && npm install

# 3. Download Ollama (handled by setup script)
# No compilation needed!

# 4. Pull a model
ollama pull phi3:mini

# 5. Run backend + frontend
# That's it!
```

## Conclusion

By choosing Ollama over llama.cpp, we traded minor performance overhead for massive gains in simplicity, reliability, and distribution ease. This makes Recursive://Neon actually feasible to ship as a game that runs on end-user machines without requiring them to install CUDA toolkits or deal with compilation errors.
