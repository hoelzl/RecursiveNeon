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
ollama pull phi3:mini
```

**Note**: This downloads ~2.3GB. For other options, see [Model Selection](#model-selection).

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
ollama pull phi3:mini
```

### Out of memory

Use a smaller model:

```bash
ollama pull phi3:mini  # 2.3GB RAM
# Instead of:
# ollama pull mistral:7b  # 7.1GB RAM
```

## Model Selection

| Model | Size | RAM Needed | Speed | Quality |
|-------|------|------------|-------|---------|
| phi3:mini | 2.3GB | 4GB | ⚡⚡⚡ | ⭐⭐⭐ |
| mistral:7b | 4.1GB | 8GB | ⚡⚡ | ⭐⭐⭐⭐ |
| llama3:8b | 4.7GB | 8GB | ⚡⚡ | ⭐⭐⭐⭐⭐ |

**Recommendation**: Start with `phi3:mini` for testing, upgrade later if needed.

## Next Steps

- Read the full [README.md](../README.md)
- Check out [ASSESSMENT.md](../ASSESSMENT.md) for technical details
- Explore the code in `backend/` and `frontend/`
- Add your own NPCs (see README for examples)

## Getting Help

- 📖 [Full Documentation](../README.md)
- 🐛 [Report Issues](https://github.com/hoelzl/RecursiveNeon/issues)
- 💬 Read the design documents in `design-documents/`

---

**Happy exploring in Recursive://Neon! ⚡**
