# Quick Start Guide

Get Recursive://Neon up and running in 5 minutes!

## Prerequisites Check

Before starting, verify you have:

```bash
# Check Python (need 3.11+)
python3 --version

# Check Node.js (need 18+)
node --version

# Check disk space (need ~2GB free)
df -h .
```

## Step 1: Clone and Setup

### Linux/macOS:

```bash
git clone https://github.com/hoelzl/RecursiveNeon.git
cd RecursiveNeon
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### Windows:

```cmd
git clone https://github.com/hoelzl/RecursiveNeon.git
cd RecursiveNeon
scripts\setup.bat
```

This will:
- Create Python virtual environment
- Install Python dependencies
- Install Node.js dependencies
- Download ollama binary

## Step 2: Get a Model

```bash
# Pull the recommended lightweight model
ollama pull qwen2.5:3b
```

**Note**: This downloads ~2GB. For other options, see [Model Selection](#model-selection).

## Step 3: Run the Game

Open **two terminal windows**:

### Terminal 1 - Backend:

```bash
# Activate virtual environment (from project root)
source backend/venv/bin/activate  # Windows: backend\venv\Scripts\activate

# Run backend (must be from project root)
python -m backend.main
```

Wait for: `Recursive://Neon Backend Ready!`

### Terminal 2 - Frontend:

```bash
cd frontend
npm run dev
```

Open browser to: `http://localhost:5173`

## Step 4: Play!

1. Wait for status indicator to turn **green** (backend ready)
2. Double-click **Chat** icon on desktop
3. Select an NPC from the sidebar
4. Start chatting!

## Troubleshooting

### Backend won't start

```bash
# IMPORTANT: Run from project root, not from backend/ directory
# Make sure you're in RecursiveNeon/ directory
pwd  # Should show .../RecursiveNeon

# Activate venv
source backend/venv/bin/activate  # Windows: backend\venv\Scripts\activate

# Run backend
python -m backend.main

# If still issues, check if ports are free
lsof -i :8000   # Backend (Mac/Linux)
lsof -i :11434  # Ollama

# If busy, kill the process or change ports in .env
```

### Frontend shows connection error

1. Verify backend is running (check terminal 1)
2. Check browser console for errors (F12)
3. Try refreshing the page

### NPCs don't respond

```bash
# Verify model is installed
ollama list

# If empty, pull a model
ollama pull qwen2.5:3b
```

### Out of memory

Use a smaller model:

```bash
ollama pull qwen2.5:3b  # ~2GB RAM
# Instead of larger models like:
# ollama pull gemma2:9b  # ~5GB RAM
```

## Model Selection

### General Purpose Models

| Model | Size | RAM Needed | Speed | Quality | Notes |
|-------|------|------------|-------|---------|-------|
| qwen2.5:3b | ~2GB | 4GB | ⚡⚡⚡ | ⭐⭐⭐ | Great storytelling |
| gemma2:9b | ~5GB | 8GB | ⚡⚡ | ⭐⭐⭐⭐ | Balanced performance |
| llama3.3:70b | ~40GB | 64GB+ | ⚡ | ⭐⭐⭐⭐⭐ | Requires powerful hardware |

### Specialized Role-Playing Models

| Model | Size | RAM Needed | Speed | Quality | Notes |
|-------|------|------------|-------|---------|-------|
| nous-hermes:13b | ~7GB | 12GB | ⚡⚡ | ⭐⭐⭐⭐ | Purpose-built for NPCs |
| mythomax-l2:13b | ~7GB | 12GB | ⚡⚡ | ⭐⭐⭐⭐ | Excellent storytelling |

**Recommendation**: Start with `qwen2.5:3b` for testing, upgrade to `nous-hermes:13b` for better roleplay quality.

## Next Steps

- Read the full [README.md](../README.md)
- Check out [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Explore the code in `backend/` and `frontend/`
- Add your own NPCs (see README for examples)

## Getting Help

- 📖 [Full Documentation](../README.md)
- 🐛 [Report Issues](https://github.com/hoelzl/RecursiveNeon/issues)
- 💬 Read the design documents in `design-documents/`

---

**Happy exploring in Recursive://Neon! ⚡**
