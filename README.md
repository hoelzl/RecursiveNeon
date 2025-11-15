# Recursive://Neon

A futuristic RPG powered by LLM-driven NPCs, featuring a unique desktop-like UI where you navigate a digital world and interact with AI characters that remember your conversations and develop relationships.

![Status](https://img.shields.io/badge/status-prototype-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Node](https://img.shields.io/badge/node-18+-green)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)

## Overview

Recursive://Neon is both a game and a demonstration of LLM-assisted development. It showcases:

- **LLM-Powered NPCs**: Characters with unique personalities, memories, and conversational abilities
- **Desktop UI**: A nostalgic yet futuristic interface inspired by classic operating systems
- **Local-First**: Everything runs on your machine - no cloud APIs needed
- **Modern Stack**: FastAPI backend, React frontend, Ollama for LLM inference

## Features

### 🎮 Game Features

- **Dynamic NPCs**: Each NPC has a unique personality, background, and conversational style
- **Persistent Memory**: NPCs remember past conversations and build relationships with you
- **Desktop Environment**: Navigate through a simulated computer interface with customizable themes
- **Real-Time Chat**: Instant messaging with NPCs using WebSocket communication
- **Game Time System**: Independent in-game time with time dilation support (pause, slow down, speed up)
- **Clock Widget**: Configurable clock display (analog, digital, or hidden) with customizable position
- **Settings App**: System-wide configuration for clock, themes, and more
- **Theme System**: 6 predefined themes (Classic, Dark, Light, Neon, Terminal, Cyberpunk)

### 🛠️ Technical Features

- **FastAPI Backend**: Modern Python async web framework
- **React + TypeScript Frontend**: Clean, type-safe UI code
- **LangChain Integration**: Sophisticated conversation management
- **Ollama LLM Server**: Local AI inference (no API keys needed)
- **WebSocket Communication**: Real-time bidirectional updates
- **Zustand State Management**: Simple and powerful React state
- **Time Service**: Backend-controlled game time with frontend synchronization and interpolation
- **Settings Service**: Persistent configuration with validation and change notifications
- **Dependency Injection**: Testable, modular architecture throughout the backend

## Architecture

```
┌─────────────────────────────────────────────┐
│     React Frontend (Desktop UI)             │
│     - Window Manager                        │
│     - Chat Interface                        │
│     - Clock Widget (Analog/Digital)         │
│     - Settings App                          │
│     - Time Service (Sync & Interpolation)   │
│     - Settings Service (Local Cache)        │
│     - WebSocket Client                      │
└───────────────┬─────────────────────────────┘
                │ WebSocket + HTTP
┌───────────────▼─────────────────────────────┐
│     FastAPI Backend                         │
│     - WebSocket Handler                     │
│     - NPC Manager (LangChain)               │
│     - Time Service (Game Clock)             │
│     - Settings Service (Persistence)        │
│     - Process Orchestrator                  │
└───────────────┬─────────────────────────────┘
                │ HTTP (localhost:11434)
┌───────────────▼─────────────────────────────┐
│     Ollama Server                           │
│     - LLM Inference (Qwen3, etc.)           │
│     - Auto GPU/CPU Detection                │
└─────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **~2GB free disk space** (for ollama + models)
- **(Optional) NVIDIA GPU** for faster inference

### Installation

#### Linux / macOS

```bash
# Clone the repository
git clone https://github.com/hoelzl/RecursiveNeon.git
cd RecursiveNeon

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# Pull a model for ollama
ollama pull qwen3:4b
```

#### Windows

```cmd
REM Clone the repository
git clone https://github.com/hoelzl/RecursiveNeon.git
cd RecursiveNeon

REM Run setup script
scripts\setup.bat

REM Pull a model for ollama
ollama pull qwen2.5:3b
```

### Running the Game

**IMPORTANT**: All commands must be run from the project root directory (`RecursiveNeon/`), not from subdirectories.

You need two terminal windows:

**Terminal 1 - Backend:**
```bash
# Install backend in development mode (from project root, one-time setup)
cd backend
uv pip install -e .

# Run backend using the entry point (can be run from any directory)
run-recursive-neon-backend

# Or alternatively, run directly with Python
python -m recursive_neon.main
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Then open your browser to: **http://localhost:5173**

## Usage

### First Steps

1. **Wait for initialization**: The backend starts ollama and loads NPCs (takes ~10-30 seconds)
2. **Check the status indicator**: Green dot in taskbar = ready to go
3. **Notice the clock**: The game clock displays in the corner (showing game time: Nov 13, 2048)
4. **Open the Chat app**: Double-click the Chat icon on the desktop
5. **Select an NPC**: Click on an NPC in the sidebar
6. **Start chatting**: Type your message and press Enter

### Customizing Your Experience

- **Settings App**: Open the Settings icon to customize:
  - **Clock Settings**: Choose analog/digital display, toggle seconds/date, adjust position
  - **Theme Settings**: Select from 6 themes (Classic, Dark, Light, Neon, Terminal, Cyberpunk)
- **Game Time**: The in-game time progresses independently (default: 2048-11-13 08:00 UTC)
  - Time can be controlled via the time service (future UI planned)
  - Supports time dilation (pause, speed up, slow down)

### Available NPCs

The game includes 5 default NPCs:

- **Aria** (👩‍💼) - Professional receptionist who knows everything about the building
- **Zero** (🕵️) - Mysterious hacker with secrets about the system
- **Kai** (🧙‍♂️) - Enthusiastic digital merchant selling rare items
- **Morgan** (👨‍🔧) - Grumpy but brilliant system engineer
- **Luna** (🤖) - Friendly AI guide who helps newcomers

Each has their own personality, conversation style, and secrets to discover!

## Development

### Project Structure

```
RecursiveNeon/
├── backend/                     # Python FastAPI backend
│   ├── src/
│   │   └── recursive_neon/     # Main Python package
│   │       ├── models/         # Data models (NPCs, game state)
│   │       ├── services/       # Business logic
│   │       │   ├── npc_manager.py    # NPC chat management
│   │       │   ├── time_service.py   # Game time with dilation
│   │       │   ├── settings_service.py # Configuration management
│   │       │   └── message_handler.py  # WebSocket routing
│   │       ├── main.py         # FastAPI app entry point
│   │       ├── dependencies.py # Dependency injection container
│   │       └── config.py       # Configuration
│   ├── tests/                  # Comprehensive test suite
│   │   ├── unit/              # Unit tests (time, settings, NPCs)
│   │   └── integration/       # Integration tests (WebSocket)
│   └── pyproject.toml          # Python project config (uv-compatible)
│
├── frontend/                    # React TypeScript frontend
│   ├── src/
│   │   ├── components/   # UI components
│   │   │   ├── Desktop.tsx      # Main desktop
│   │   │   ├── ClockWidget.tsx  # Clock widget
│   │   │   ├── AnalogClock.tsx  # Analog clock face
│   │   │   ├── DigitalClock.tsx # Digital clock display
│   │   │   └── apps/           # Desktop applications
│   │   │       ├── ChatApp.tsx     # NPC chat interface
│   │   │       ├── SettingsApp.tsx # Settings configuration
│   │   │       └── settings/       # Settings pages
│   │   ├── services/     # Frontend services
│   │   │   ├── websocket.ts     # WebSocket client
│   │   │   ├── timeService.ts   # Time sync & interpolation
│   │   │   └── settingsService.ts # Settings cache
│   │   ├── themes/       # Theme system
│   │   │   └── themes.ts        # 6 predefined themes
│   │   ├── stores/       # Zustand state management
│   │   └── styles/       # CSS styles
│   └── package.json
│
├── services/              # External services
│   └── ollama/           # Ollama binaries (downloaded by setup)
│
├── scripts/               # Setup and build scripts
│   ├── setup.sh          # Linux/Mac setup
│   ├── setup.bat         # Windows setup
│   └── download_ollama.py # Ollama downloader
│
└── docs/                  # Documentation
    ├── time-system-requirements.md  # Time system specs
    ├── time-system-design.md        # Time system architecture
    ├── settings-app-requirements.md # Settings specs
    └── settings-app-design.md       # Settings architecture
```

### Running Tests

The backend includes a comprehensive test suite using pytest.

**Basic testing (without coverage):**
```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

**With coverage reporting:**
```bash
pytest --cov=. --cov-report=term-missing --cov-report=html
```

This generates:
- Terminal output showing coverage percentages
- HTML report in `backend/htmlcov/` directory

**Test categories:**
- `pytest -m unit` - Run only unit tests (fast)
- `pytest -m integration` - Run integration tests
- `pytest -m "not slow"` - Skip slow tests

### Adding New NPCs

Edit `backend/services/npc_manager.py` and add to the `create_default_npcs()` method:

```python
NPC(
    id="my_npc",
    name="My NPC",
    personality=NPCPersonality.FRIENDLY,
    role=NPCRole.COMPANION,
    background="A cool character...",
    occupation="Explorer",
    location="The Lab",
    greeting="Hello there!",
    conversation_style="casual and friendly",
    topics_of_interest=["science", "adventure"],
    avatar="🧑‍🔬",
    theme_color="#ff6b6b"
)
```

### Environment Variables

Copy `.env.example` to `.env` in the backend directory and customize:

```bash
# Backend
HOST=127.0.0.1
PORT=8000

# Ollama
OLLAMA_HOST=127.0.0.1
OLLAMA_PORT=11434
DEFAULT_MODEL=qwen3:4b

# Game
MAX_NPCS=20
MAX_RESPONSE_TOKENS=200
```

## Why Ollama Instead of llama.cpp?

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a detailed technical analysis.

**TL;DR**: Building llama.cpp with CUDA support is complex and fragile. Ollama provides:

- ✅ Single binary (no compilation)
- ✅ Auto GPU/CPU detection
- ✅ Easy distribution
- ✅ Stable API
- ✅ Built-in model management

## Performance

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8GB | 16GB+ |
| Storage | 2GB free | 5GB+ free |
| CPU | 4 cores | 8+ cores |
| GPU | None (CPU works) | NVIDIA GPU with 4GB+ VRAM |

### Model Recommendations

#### General Purpose Models

| Model | Size | RAM | Speed | Quality | Notes |
|-------|------|-----|-------|---------|-------|
| qwen3:1.7b | ~1GB | 2GB | ⚡⚡⚡ Very Fast | ⭐⭐ Decent | Smallest Qwen3, great for low-resource systems |
| qwen3:4b | ~2.5GB | 4GB | ⚡⚡⚡ Fast | ⭐⭐⭐ Good | Recommended for most users, excellent balance |
| qwen3:8b | ~4.5GB | 8GB | ⚡⚡ Medium | ⭐⭐⭐⭐ Great | High quality, good for general use |
| qwen3:14b | ~8GB | 12GB | ⚡⚡ Medium | ⭐⭐⭐⭐ Great | Excellent quality, recommended for roleplay |
| qwen3:30b | ~17GB | 24GB | ⚡ Slow | ⭐⭐⭐⭐⭐ Excellent | High-end model for best results |
| gemma3:1b | ~1GB | 2GB | ⚡⚡⚡ Very Fast | ⭐⭐ Decent | Tiny but capable |
| gemma3:4b | ~2.5GB | 4GB | ⚡⚡⚡ Fast | ⭐⭐⭐ Good | Solid general purpose model |
| gemma3:12b | ~7GB | 12GB | ⚡⚡ Medium | ⭐⭐⭐⭐ Great | Strong performance |
| gemma3:27b | ~15GB | 20GB | ⚡ Slow | ⭐⭐⭐⭐⭐ Excellent | High-quality responses |
| nemotron-mini | ~2GB | 4GB | ⚡⚡⚡ Fast | ⭐⭐⭐ Good | Compact and efficient |

#### Specialized Role-Playing Models

| Model | Size | RAM | Speed | Quality | Notes |
|-------|------|-----|-------|---------|-------|
| HammerAI/mythomax-l2 | ~7GB | 12GB | ⚡⚡ Medium | ⭐⭐⭐⭐ Great | Excellent for creative storytelling |
| leeplenty/ellaria | ~7GB | 12GB | ⚡⚡ Medium | ⭐⭐⭐⭐ Great | Strong roleplay capabilities |

**Installation:**
```bash
# Lightweight option (recommended for testing)
ollama pull qwen3:4b

# Balanced option (recommended for production)
ollama pull qwen3:8b

# Specialized for roleplay
ollama pull HammerAI/mythomax-l2
ollama pull leeplenty/ellaria
```

**Recommendations:**
- **Getting started**: Use `qwen3:4b` (default) for fast responses and low resource usage
- **Best balance**: Use `qwen3:8b` for good quality with reasonable resource requirements
- **Best roleplay**: Use `qwen3:14b`, `HammerAI/mythomax-l2`, or `leeplenty/ellaria` for the most engaging NPC conversations
- **Maximum quality**: Use `qwen3:30b` or `gemma3:27b` if you have powerful hardware

## Troubleshooting

### "Failed to connect to server"

- Ensure backend is running: `python -m backend.main` (from project root)
- Check if port 8000 is free: `lsof -i :8000` (Mac/Linux)
- Check ollama is running in backend logs

### "Ollama server did not become ready"

- Verify ollama binary exists: `ls services/ollama/`
- Try running ollama manually: `./services/ollama/ollama serve`
- Check if port 11434 is free

### "NPCs not responding"

- Ensure you've pulled a model: `ollama pull qwen3:4b`
- Check backend logs for errors
- Verify ollama is using the correct model in `.env`

### Slow responses

- Use a smaller model (qwen3:4b or qwen3:1.7b)
- Reduce `MAX_RESPONSE_TOKENS` in `.env`
- Check GPU is being used (watch nvidia-smi)

## Contributing

This project is primarily a demonstration, but contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Ollama** - Making local LLM inference accessible
- **LangChain** - Powerful LLM application framework
- **FastAPI** - Modern Python web framework
- **React** - UI framework
- Design inspired by classic desktop operating systems

## Project Goals

This project demonstrates:

1. **LLM-assisted development**: The initial architecture was designed using Claude Sonnet 4.5
2. **Practical AI integration**: Real-world use of local LLMs in an application
3. **Modern web stack**: FastAPI + React + TypeScript
4. **Distribution challenges**: How to ship LLM-powered apps to end users

It's both a playable game and a learning resource for building LLM applications.

---

**Built with ⚡ by developers, for developers**

For questions or issues, please [open an issue](https://github.com/hoelzl/RecursiveNeon/issues).
