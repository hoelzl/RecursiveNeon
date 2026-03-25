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
user@neon-proxy:/Documents$ write notes/todo.txt Buy groceries
```

**Search files:**

```
user@neon-proxy:/$ grep -i secret /Documents
/Documents/readme.txt:3:This file contains a secret code
user@neon-proxy:/$ find / -name *.txt
/welcome.txt
/Documents/readme.txt
...
```

**Manage notes and tasks:**

```
user@neon-proxy:/$ note create "Investigation Log" -c "Found suspicious files in /Projects"
Created note: Investigation Log
user@neon-proxy:/$ task add Check server logs
Added to default: Check server logs
user@neon-proxy:/$ task done 1
[x] Check server logs
```

**Chat with NPCs** (requires Ollama + a model):

```
user@neon-proxy:/$ chat hacker_zero
Connecting to Zero...
[Zero]: ...You found me. Interesting.

hacker_zero> What do you know about the breach?
[Zero]: The breach wasn't from the outside. Someone on the inside
left the door wide open.

hacker_zero> /relationship
Relationship with Zero: 0

hacker_zero> /exit
Connection closed.
```

**Save your progress:**

```
user@neon-proxy:/$ save
Game state saved.
```

Game state (filesystem, notes, tasks, NPC conversations) persists across sessions automatically on exit, or manually with `save`.

**All commands:** `ls`, `cd`, `pwd`, `cat`, `mkdir`, `touch`, `rm`, `cp`, `mv`, `grep`, `find`, `write`, `note`, `task`, `chat`, `save`, `help`, `clear`, `echo`, `env`, `whoami`, `hostname`, `date`, `export`, `exit`

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

## WebSocket Terminal

The shell also runs over WebSocket, enabling remote connections via the same protocol the browser will use:

```bash
# Start the backend server (requires Ollama for NPC chat)
.venv/Scripts/python -m recursive_neon.main

# In another terminal, connect via WebSocket
.venv/Scripts/python -m recursive_neon.wsclient
```

## Architecture

```
Layer 1: Application Core     AppService, NPCManager, GameState
Layer 2: CLI Shell             prompt_toolkit REPL, commands, path resolver
Layer 3: WebSocket Terminal    /ws/terminal endpoint + CLI client (complete)
Layer 4: Browser Terminal      (planned) xterm.js over WebSocket
Layer 5: Desktop GUI           (planned) window manager, taskbar
```

Every feature works in the CLI before touching the browser. See [docs/](docs/) for detailed design documents.

## License

Apache 2.0
