# Architecture

## Why Ollama?

Recursive://Neon uses **Ollama** for local LLM inference instead of llama.cpp or other alternatives.

### The Problem

Initial designs considered using llama.cpp directly, but this approach had critical issues:

1. **Build Complexity**: Requires compilation with CUDA toolkit, specific compilers, and platform-specific toolchains
2. **Distribution Challenge**: Different binaries needed for CUDA vs CPU
3. **Dependency Hell**: Heavy build dependencies (Visual Studio tools, CMake, BLAS libraries, etc.)
4. **Portability Issues**: No guarantee of working on target machines with different GPU drivers

### The Solution

Ollama solves these problems:

- **Single binary distribution** — one executable for all platforms, automatic GPU detection with CPU fallback
- **Simple integration** — clean REST API (OpenAI-compatible), built-in model management, LangChain compatible
- **Robust hardware support** — works on any hardware, automatic quantization selection, built-in CUDA/ROCm/Metal
- **Better DX** — well-documented API, active development, easy to test

**Trade-offs**: Slightly higher memory overhead (~100MB), less fine-grained control, slightly slower cold start (~2-3s). For a game distribution scenario, these heavily favor Ollama.

## System Architecture

```
┌─────────────────────────────────────────────────┐
│  Layer 4: Desktop GUI (Browser, future)         │
│  Window manager, taskbar, desktop icons          │
├─────────────────────────────────────────────────┤
│  Layer 3: Terminal Emulator (Browser, future)   │
│  xterm.js, WebSocket transport                   │
├─────────────────────────────────────────────────┤
│  Layer 2: CLI Shell (Python)          ← current │
│  REPL, commands, pipes, globs, TUI apps, WS     │
├─────────────────────────────────────────────────┤
│  Layer 1: Application Core (Python)   ← exists  │
│  AppService, NPCManager, GameState, models       │
└───────────────┬─────────────────────────────────┘
                │ HTTP (localhost:11434)
┌───────────────▼─────────────────────────────────┐
│  Ollama Server                                   │
│  LLM inference (auto GPU/CPU), model management  │
└─────────────────────────────────────────────────┘
```

Every feature works in the CLI (Layer 2) before touching the browser (Layers 3-4). See `docs/V2_HANDOVER.md` for the rationale behind this approach.

## Key Components

### Application Core (Layer 1)

- **AppService** — virtual filesystem, notes, and tasks CRUD with JSON persistence. All files are UUID-based `FileNode` objects in memory (see `FILESYSTEM_SECURITY.md`).
- **NPCManager** — LangChain-based NPC conversation manager with persistent memory, relationship tracking, and think-tag stripping for qwen3 models.
- **OllamaClient** — async HTTP client for Ollama's REST API.
- **ProcessManager** — manages the Ollama binary lifecycle.
- **ServiceContainer** — dependency injection via `ServiceFactory` (see `docs/BACKEND_CONVENTIONS.md`).

### CLI Shell (Layer 2)

- **ShellSession** — session state (cwd, env vars, history) + path resolution between human-readable paths and UUID-based filesystem.
- **ProgramRegistry** — maps program names to async `Program` implementations with restricted `ProgramContext`.
- **Builtins** (`cd`, `exit`, `export`) — modify shell session state directly.
- **Programs** — filesystem ops (`ls`, `cat`, `grep`, `find`, `write`, ...), notes/tasks management, NPC chat, TUI minigames (`codebreaker`), utilities (`help`, `save`, `echo`, ...).
- **Shell features** — pipes (`|`), output redirection (`>`, `>>`), glob expansion (`*`, `?`, `[...]`), context-sensitive tab completion.
- **TUI framework** — raw-mode app support via `ScreenBuffer`, `TuiApp` protocol, and `run_tui_app()` lifecycle manager.
- **WebSocket transport** — `/ws/terminal` endpoint serves the same shell over WebSocket with JSON protocol. CLI client: `python -m recursive_neon.wsclient`.
- **Output** — abstracted output with ANSI colors, `CapturedOutput` for pipes, `QueueOutput` for WebSocket delivery.
- **Persistence** — game state (filesystem, notes, tasks, NPC conversations) saves to `game_data/` as JSON on exit and loads on startup. Auto-saves periodically during WebSocket sessions. Shell history persists via `FileHistory`.

See `docs/SHELL_DESIGN.md` for detailed shell architecture.

### Ollama

- Bundled with the game distribution
- Automatically started by backend
- Provides LLM inference for all NPCs
- No external API keys or network required
