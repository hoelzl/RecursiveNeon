# Quick Start Guide

Get Recursive://Neon up and running.

## Prerequisites

- Python 3.11+ (`python --version`)
- [uv](https://docs.astral.sh/uv/) for fast dependency management (`uv --version`)
- ~2GB free disk space (for Ollama model)

## Setup

```bash
git clone https://github.com/hoelzl/RecursiveNeon.git
cd RecursiveNeon

# Create virtual environment and install dependencies
uv venv --python 3.14 .venv
uv pip install -e "backend/.[dev]"
```

## Run Tests

```bash
cd backend
../.venv/Scripts/pytest           # Windows
# ../.venv/bin/pytest             # Linux/macOS

../.venv/Scripts/pytest --cov     # With coverage
../.venv/Scripts/pytest -m unit   # Unit tests only
```

## Run the Shell

> **Note**: The CLI shell is currently under development (Phase 1). Once complete:

```bash
# From repo root
.venv/Scripts/python -m recursive_neon.shell    # Windows
# .venv/bin/python -m recursive_neon.shell      # Linux/macOS
```

This drops you into an interactive terminal session with the virtual filesystem, NPC chat, and more. Type `help` for available commands.

## Set Up an LLM (for NPC Chat)

NPC conversations require a local LLM via Ollama:

```bash
# Install Ollama (https://ollama.com) or use the bundled downloader:
python scripts/download_ollama.py

# Pull a model
ollama pull qwen3:4b
```

### Model Recommendations

| Model | Size | RAM | Notes |
|-------|------|-----|-------|
| `qwen3:4b` | ~2GB | 4GB | Default, good for testing |
| `qwen2.5:3b` | ~2GB | 4GB | Great storytelling |
| `gemma2:9b` | ~5GB | 8GB | Better quality, needs more RAM |

## Code Quality

```bash
cd backend
../.venv/Scripts/ruff check .      # Lint
../.venv/Scripts/ruff format .     # Format
../.venv/Scripts/mypy              # Type check
```

## Project Structure

```
backend/src/recursive_neon/
  models/          Data models (FileNode, NPC, GameState, etc.)
  services/        Business logic (AppService, NPCManager, etc.)
  shell/           CLI shell (commands, session, REPL)
  config.py        Settings (Pydantic)
  dependencies.py  Dependency injection container
  main.py          FastAPI app (HTTP/WebSocket API)
```

## Further Reading

- [ARCHITECTURE.md](ARCHITECTURE.md) — system architecture, why Ollama
- [SHELL_DESIGN.md](SHELL_DESIGN.md) — CLI shell design
- [BACKEND_CONVENTIONS.md](BACKEND_CONVENTIONS.md) — code style, DI, testing
- [V2_HANDOVER.md](V2_HANDOVER.md) — V2 decisions, what was kept/removed, phases
- [backend/FILESYSTEM_SECURITY.md](../backend/FILESYSTEM_SECURITY.md) — virtual filesystem security
