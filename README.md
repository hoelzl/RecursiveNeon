# Recursive://Neon

A futuristic RPG prototype where the player interacts with a simulated computer through a terminal shell. Chat with LLM-powered NPCs, explore a virtual filesystem, and uncover secrets — all from the command line.

The game uses a Python backend with a virtual filesystem, NPC conversation engine (via [Ollama](https://ollama.com) for local LLM inference), and an interactive CLI shell that feels like SSHing into a remote system.

## Quick Start

```bash
# Prerequisites: Python 3.11+, uv (https://docs.astral.sh/uv/)

git clone https://github.com/hoelzl/RecursiveNeon.git
cd RecursiveNeon

# Set up environment
uv venv --python 3.14 .venv
uv pip install -e "backend/.[dev]"

# Run the shell
.venv/Scripts/python -m recursive_neon.shell    # Windows
.venv/bin/python -m recursive_neon.shell        # Linux/macOS
```

You'll see:

```
╔══════════════════════════════════════════════════╗
║  Recursive://Neon                                ║
║  Connection established to neon-proxy            ║
║  Type 'help' for available commands              ║
╚══════════════════════════════════════════════════╝
user@neon-proxy:/$ _
```

## What You Can Do

**Explore the virtual filesystem:**

```
user@neon-proxy:/$ ls
Documents/  My Folder/  Pictures/  Projects/  welcome.txt
user@neon-proxy:/$ cat welcome.txt
user@neon-proxy:/$ cd Documents
user@neon-proxy:/Documents$ mkdir notes
user@neon-proxy:/Documents$ touch notes/todo.txt
```

**Chat with NPCs** (requires Ollama + a model):

```
user@neon-proxy:/$ chat cipher
Connecting to cipher...
[cipher]: Ah, a new face on the network...

cipher> What happened to this system?
[cipher]: You really want to know? Let's just say the breach
wasn't from the outside...

cipher> exit
Connection closed.
```

**Standard shell utilities:** `pwd`, `echo`, `env`, `whoami`, `hostname`, `date`, `help`

## Setting Up NPC Chat

NPC conversations require a local LLM via Ollama:

```bash
# Install Ollama from https://ollama.com, then:
ollama pull qwen3:4b
```

## Running Tests

```bash
cd backend
../.venv/Scripts/pytest              # All tests
../.venv/Scripts/pytest -m unit      # Unit tests only
../.venv/Scripts/pytest --cov        # With coverage
```

## Architecture

```
Layer 1: Application Core     AppService, NPCManager, GameState
Layer 2: CLI Shell             prompt_toolkit REPL, commands, path resolver
Layer 3: Browser Terminal      (planned) xterm.js over WebSocket
Layer 4: Desktop GUI           (planned) window manager, taskbar
```

Every feature works in the CLI before touching the browser. See [docs/](docs/) for detailed design documents.

## License

Apache 2.0
