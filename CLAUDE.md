# CLAUDE.md - AI Assistant Guide for RecursiveNeon

> **Last Updated**: 2025-11-13
> **Project**: Recursive://Neon - LLM-Powered RPG
> **Purpose**: Comprehensive guide for AI assistants working on this codebase

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Quick Reference](#quick-reference)
3. [Repository Structure](#repository-structure)
4. [Technology Stack](#technology-stack)
5. [Architectural Patterns](#architectural-patterns)
6. [Development Workflows](#development-workflows)
7. [Code Conventions](#code-conventions)
8. [Testing Guidelines](#testing-guidelines)
9. [Security Principles](#security-principles)
10. [Common Tasks](#common-tasks)
11. [Git Workflow](#git-workflow)
12. [Key Files Reference](#key-files-reference)

---

## Project Overview

**Recursive://Neon** is a futuristic RPG prototype that demonstrates LLM-assisted development through:

- **LLM-Powered NPCs**: Characters with unique personalities, memories, and conversational abilities using local LLMs
- **Desktop UI**: Nostalgic yet futuristic interface inspired by classic operating systems
- **Local-First Architecture**: Everything runs on the user's machine - no cloud APIs needed
- **Modern Full-Stack**: FastAPI (Python) backend, React (TypeScript) frontend, Ollama for LLM inference

### Key Characteristics

- **Security-First**: Virtual filesystem with complete isolation from the host system
- **Dependency Injection**: Testable, modular architecture throughout
- **Type-Safe**: Pydantic (Python) and strict TypeScript
- **Well-Tested**: Comprehensive pytest and Vitest test suites
- **Extensible**: Easy to add NPCs, terminal commands, and desktop apps

---

## Quick Reference

### Essential Commands

```bash
# Backend (from project root)
cd backend
uv pip install -e .                # Install in development mode
run-recursive-neon-backend          # Run backend server
pytest                              # Run tests
pytest --cov                        # Run tests with coverage

# Frontend (from project root)
cd frontend
npm install                         # Install dependencies
npm run dev                         # Development server
npm test                            # Run tests
npm run lint                        # Lint code
```

### Critical Rules for AI Assistants

1. **NEVER use real file paths** - Always use FileNode UUIDs for in-game files
2. **ALWAYS use dependency injection** - Never create services directly, inject them
3. **ALWAYS write tests** - Especially for new features and security-critical code
4. **FOLLOW existing patterns** - Study similar code before implementing new features
5. **UPDATE documentation** - Keep docs in sync with code changes

### Important File Paths

- Backend entry: `backend/src/recursive_neon/main.py`
- Backend DI: `backend/src/recursive_neon/dependencies.py`
- Frontend entry: `frontend/src/App.tsx`
- Frontend store: `frontend/src/stores/gameStore.ts`
- Security docs: `backend/FILESYSTEM_SECURITY.md`

---

## Repository Structure

```
RecursiveNeon/
├── backend/                          # Python FastAPI backend
│   ├── src/recursive_neon/          # Main Python package
│   │   ├── models/                  # Pydantic data models
│   │   │   ├── npc.py              # NPC, ChatRequest/Response
│   │   │   ├── game_state.py       # SystemState, GameState
│   │   │   └── app_models.py       # Notes, Tasks, FileSystem
│   │   ├── services/                # Business logic layer
│   │   │   ├── npc_manager.py      # NPC conversation management
│   │   │   ├── ollama_client.py    # Ollama HTTP client
│   │   │   ├── process_manager.py  # Ollama process lifecycle
│   │   │   ├── message_handler.py  # WebSocket message routing
│   │   │   ├── app_service.py      # Desktop apps backend
│   │   │   └── interfaces.py       # ABC interfaces for DI
│   │   ├── main.py                  # FastAPI app + lifespan
│   │   ├── config.py                # Pydantic settings
│   │   └── dependencies.py          # DI container & factory
│   ├── tests/                       # Pytest test suite
│   │   ├── conftest.py             # Shared fixtures
│   │   ├── unit/                    # Unit tests
│   │   └── integration/             # Integration tests
│   ├── pyproject.toml               # Python package config
│   ├── pytest.ini                   # Pytest configuration
│   ├── initial_fs/                  # Initial in-game filesystem
│   ├── game_data/                   # Runtime state (gitignored)
│   └── FILESYSTEM_SECURITY.md       # Security documentation
│
├── frontend/                         # React TypeScript frontend
│   ├── src/
│   │   ├── components/              # React components
│   │   │   ├── Desktop.tsx         # Main desktop UI
│   │   │   ├── Window.tsx          # Window manager
│   │   │   ├── Taskbar.tsx         # Bottom taskbar
│   │   │   ├── apps/               # Desktop applications
│   │   │   │   ├── ChatApp.tsx     # NPC chat interface
│   │   │   │   ├── TerminalApp.tsx # Terminal emulator
│   │   │   │   ├── NotesApp.tsx    # Note-taking app
│   │   │   │   ├── TaskListApp.tsx # Task management
│   │   │   │   └── FileBrowserApp.tsx # File browser
│   │   │   └── terminal/           # Terminal components
│   │   ├── terminal/                # Terminal system core
│   │   │   ├── core/               # Core terminal logic
│   │   │   │   ├── TerminalSession.ts
│   │   │   │   ├── CommandRegistry.ts
│   │   │   │   ├── CompletionEngine.ts
│   │   │   │   └── FileSystemAdapter.ts
│   │   │   ├── commands/           # Built-in commands
│   │   │   └── themes/             # Terminal themes
│   │   ├── services/                # Frontend services
│   │   │   └── websocket.ts        # WebSocket client
│   │   ├── stores/                  # Zustand state
│   │   │   └── gameStore.ts        # Global game state
│   │   ├── contexts/                # React contexts
│   │   │   ├── GameStoreContext.tsx
│   │   │   └── WebSocketContext.tsx
│   │   ├── types/                   # TypeScript types
│   │   ├── utils/                   # Utilities
│   │   │   └── appApi.ts           # Backend API client
│   │   ├── styles/                  # CSS styles
│   │   ├── main.tsx                 # React entry point
│   │   └── App.tsx                  # Root component
│   ├── package.json                 # NPM dependencies
│   ├── tsconfig.json                # TypeScript config
│   ├── vite.config.ts               # Vite build config
│   └── vitest.config.ts             # Vitest test config
│
├── scripts/                          # Setup scripts
│   ├── setup.sh                     # Linux/Mac setup
│   ├── setup.bat                    # Windows setup
│   └── download_ollama.py           # Ollama downloader
│
├── docs/                             # Documentation
│   ├── ARCHITECTURE.md              # Why Ollama
│   ├── QUICKSTART.md                # Quick start guide
│   ├── terminal-design.md           # Terminal design
│   └── terminal-api-guide.md        # Terminal API docs
│
├── services/ollama/                  # Ollama binaries (gitignored)
├── README.md                         # Main documentation
├── LICENSE                           # Apache 2.0 license
└── .gitignore                        # Git ignore rules
```

---

## Technology Stack

### Backend (Python 3.11+)

**Core Framework**
- FastAPI 0.115.5 - Modern async web framework
- Uvicorn 0.32.1 - ASGI server with standard extras
- WebSockets 14.1 - WebSocket support
- Pydantic 2.10.3 - Data validation and settings
- python-dotenv 1.0.1 - Environment configuration

**LLM Integration**
- LangChain 0.3.13 - Conversation management
- LangChain-Ollama 0.2.2 - Ollama integration
- LangGraph 0.2.59 - Stateful agents
- ChromaDB 0.5.23 - Vector database for NPC memory

**Utilities**
- httpx 0.28.1 - HTTP client for Ollama
- psutil 6.1.0 - System utilities

**Testing**
- pytest 8.3.4 - Test framework
- pytest-asyncio 0.24.0 - Async test support
- pytest-mock 3.14.0 - Mocking utilities
- pytest-cov 5.0.0 - Coverage reporting

**Package Management**
- Compatible with `uv` (modern Python package manager)
- Build system: Hatchling

### Frontend (Node.js 18+)

**Core Framework**
- React 18.3.1 - UI framework
- TypeScript 5.6.3 - Type-safe JavaScript (strict mode)
- Vite 6.0.1 - Build tool and dev server

**State Management & UI**
- Zustand 5.0.2 - Lightweight state management
- react-draggable 4.4.6 - Draggable components
- react-rnd 10.5.2 - Resizable and draggable windows

**Testing**
- Vitest 1.0.4 - Test framework
- @testing-library/react 14.1.2 - React testing utilities
- @testing-library/jest-dom 6.1.5 - DOM matchers
- @vitest/ui 1.0.4 - Test UI
- @vitest/coverage-v8 1.0.4 - Coverage reporting
- jsdom 23.0.1 - DOM implementation

**Linting**
- ESLint 9.15.0 - Code linting with TypeScript plugins

### Infrastructure

- **LLM Server**: Ollama (local inference, auto GPU/CPU detection)
- **Communication**: WebSocket (real-time) + HTTP (REST)
- **Default Model**: qwen3:4b (lightweight, balanced performance)

---

## Architectural Patterns

### Backend: Dependency Injection Pattern

The backend uses a sophisticated DI container pattern for testability and modularity.

#### Service Container

```python
# dependencies.py
@dataclass
class ServiceContainer:
    """Container holding all application dependencies"""
    process_manager: IProcessManager
    ollama_client: IOllamaClient
    npc_manager: INPCManager
    message_handler: MessageHandler
    system_state: SystemState
    game_state: GameState
    app_service: AppService
    start_time: datetime
```

#### Service Factory

```python
class ServiceFactory:
    """Creates production or test containers"""

    @staticmethod
    def create_production_container() -> ServiceContainer:
        """Create container with real implementations"""
        # Creates all services with proper dependencies
        # Returns fully configured container

    @staticmethod
    def create_test_container(
        process_manager: Optional[IProcessManager] = None,
        ollama_client: Optional[IOllamaClient] = None,
        # ... other mocks
    ) -> ServiceContainer:
        """Create container with mocks for testing"""
```

#### FastAPI Integration

```python
# main.py
_container: ServiceContainer = None

def get_container() -> ServiceContainer:
    """FastAPI dependency injection"""
    return _container

@app.get("/health")
async def health_check(
    container: ServiceContainer = Depends(get_container)
) -> SystemState:
    return container.system_state
```

**Benefits**:
- Testable without running servers
- Clear dependency relationships
- Easy to mock in tests
- Centralized service management

### Backend: Interface-Based Design

All services implement abstract interfaces for testability:

```python
# services/interfaces.py
class INPCManager(ABC):
    @abstractmethod
    def register_npc(self, npc: NPC) -> None: ...

    @abstractmethod
    async def chat(self, npc_id: str, message: str) -> ChatResponse: ...

    @abstractmethod
    def list_npcs(self) -> List[NPC]: ...
```

**Usage in Tests**:
```python
# Easy to mock
mock_npc_manager = Mock(spec=INPCManager)
mock_npc_manager.chat.return_value = ChatResponse(...)
```

### Backend: Lifecycle Management

FastAPI's lifespan context manager handles startup/shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global _container

    # Startup
    _container = ServiceFactory.create_production_container()
    await _container.process_manager.start()
    await _container.ollama_client.wait_for_ready(timeout=60)
    _container.npc_manager.create_default_npcs()
    _container.app_service.load_or_initialize_filesystem()

    yield  # Application runs here

    # Shutdown
    _container.app_service.save_filesystem_to_disk()
    await _container.ollama_client.close()
    await _container.process_manager.stop()
```

### Backend: Message Handler Pattern

WebSocket messages are routed through a central handler:

```python
# Client sends:
{
    "type": "chat" | "get_npcs" | "app" | "ping",
    "data": { ... }
}

# MessageHandler dispatches:
class MessageHandler:
    async def handle_message(
        self,
        msg_type: str,
        msg_data: dict
    ) -> Dict[str, Any]:
        if msg_type == "chat":
            return await self._handle_chat(msg_data)
        elif msg_type == "app":
            return await self._handle_app_message(msg_data)
        # ...
```

### Frontend: Context-Based Dependency Injection

React Context provides DI for frontend services:

```typescript
// AppProviders.tsx
export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <GameStoreProvider>
      <WebSocketProvider>
        {children}
      </WebSocketProvider>
    </GameStoreProvider>
  );
}

// Components access via hooks
function ChatApp() {
  const { npcs, setNPCs } = useGameStoreContext();
  const wsClient = useWebSocket();
  // ...
}
```

### Frontend: Zustand State Management

Clean, hooks-based state without Redux boilerplate:

```typescript
export const useGameStore = create<IGameStore>((set, get) => ({
  // State
  npcs: [],
  windows: [],
  nextZIndex: 100,

  // Actions
  setNPCs: (npcs) => set({ npcs }),

  openWindow: (windowData) => {
    const id = `window-${Date.now()}`;
    const newWindow = {
      ...windowData,
      id,
      zIndex: get().nextZIndex,
      minimized: false,
    };
    set({
      windows: [...get().windows, newWindow],
      nextZIndex: get().nextZIndex + 1,
    });
  },

  closeWindow: (id) => {
    set({ windows: get().windows.filter(w => w.id !== id) });
  },
  // ...
}));
```

### Frontend: Window Management System

Desktop windows are managed centrally in the store:

```typescript
interface WindowState {
  id: string;
  title: string;
  type: string;
  content: ReactNode;
  position: { x: number; y: number };
  size: { width: number; height: number };
  zIndex: number;
  minimized: boolean;
}

// Operations: open, close, minimize, restore, focus, update
```

### Frontend: Terminal Architecture

Sophisticated terminal system with modular components:

- **TerminalSession**: Manages state, history, working directory
- **CommandRegistry**: Registers and executes commands
- **CompletionEngine**: Tab completion for commands and paths
- **OutputRenderer**: Parses ANSI codes, renders styled output
- **FileSystemAdapter**: Integrates with backend virtual filesystem

---

## Development Workflows

### Setting Up Development Environment

#### Backend Setup

```bash
# From project root
cd backend

# Install dependencies (using uv - recommended)
uv pip install -e .

# Or with pip
pip install -e .

# Install dev dependencies
uv pip install -e ".[dev]"
# Or: pip install -e ".[dev]"

# Run backend
run-recursive-neon-backend

# Or run directly
python -m recursive_neon.main
```

#### Frontend Setup

```bash
# From project root
cd frontend

# Install dependencies
npm install

# Run development server (port 5173)
npm run dev

# Production build
npm run build

# Preview production build
npm preview
```

#### Running Tests

**Backend**:
```bash
cd backend

# Run all tests
pytest

# Run specific test types
pytest -m unit                    # Unit tests only
pytest -m integration             # Integration tests
pytest -m "not slow"              # Skip slow tests

# With coverage
pytest --cov
pytest --cov-report=html          # HTML coverage report
pytest --cov-report=term-missing  # Show missing lines
```

**Frontend**:
```bash
cd frontend

# Run tests
npm test

# Run tests with UI
npm run test:ui

# Run with coverage
npm run test:coverage
```

### Development Workflow

1. **Start Backend** (Terminal 1):
   ```bash
   cd backend
   run-recursive-neon-backend
   ```

2. **Start Frontend** (Terminal 2):
   ```bash
   cd frontend
   npm run dev
   ```

3. **Open Browser**: Navigate to http://localhost:5173

4. **Make Changes**: Edit code with hot reload enabled

5. **Run Tests**: Verify changes with test suite

6. **Commit**: Follow git workflow (see Git Workflow section)

### Environment Configuration

Create `.env` file in backend directory (copy from `.env.example`):

```bash
# Backend Server
HOST=127.0.0.1
PORT=8000

# Ollama Configuration
OLLAMA_HOST=127.0.0.1
OLLAMA_PORT=11434
DEFAULT_MODEL=qwen3:4b

# Game Configuration
MAX_NPCS=20
MAX_RESPONSE_TOKENS=200

# File paths (relative to backend/)
INITIAL_FS_PATH=initial_fs
GAME_DATA_PATH=game_data
```

---

## Code Conventions

### Backend (Python) Conventions

#### Code Organization

- **Models**: `models/` - Pydantic BaseModel classes with validation
- **Services**: `services/` - Business logic implementing abstract interfaces
- **Dependencies**: Injected via constructor or function parameters
- **Configuration**: Pydantic Settings class with .env support

#### Import Style

```python
# Standard library (alphabetical)
import asyncio
import logging
from datetime import datetime
from typing import List, Optional

# Third-party (alphabetical)
from fastapi import FastAPI, WebSocket, Depends
from pydantic import BaseModel, Field

# Local (relative imports, alphabetical)
from recursive_neon.models.npc import NPC
from recursive_neon.services.interfaces import INPCManager
from recursive_neon.config import Settings
```

#### Naming Conventions

```python
# Classes: PascalCase
class NPCManager:
    pass

class OllamaClient:
    pass

# Functions/Methods: snake_case
def register_npc(npc: NPC) -> None:
    pass

async def chat_with_npc(npc_id: str, message: str) -> ChatResponse:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_NPCS = 20
DEFAULT_MODEL = "qwen3:4b"

# Private: Leading underscore
def _internal_helper():
    pass

# Interfaces: Prefix with 'I'
class INPCManager(ABC):
    pass
```

#### Type Hints

Always use type hints for function parameters and return values:

```python
def register_npc(self, npc: NPC) -> None:
    """Register an NPC with the manager."""
    self.npcs[npc.id] = npc

async def chat(
    self,
    npc_id: str,
    message: str
) -> ChatResponse:
    """Send a chat message to an NPC."""
    # ...
    return ChatResponse(...)

def list_npcs(self) -> List[NPC]:
    """Get all registered NPCs."""
    return list(self.npcs.values())
```

#### Docstrings

Use Google-style docstrings:

```python
def chat(self, npc_id: str, message: str) -> ChatResponse:
    """Send a chat message to an NPC.

    Args:
        npc_id: Unique identifier of the NPC
        message: User's message to send

    Returns:
        ChatResponse containing NPC's reply

    Raises:
        ValueError: If NPC ID is not found
    """
    pass
```

#### Async Patterns

- All I/O operations should be async
- Use `asyncio.to_thread()` for blocking operations
- WebSocket handlers should be async generators

```python
# Good: Async I/O
async def fetch_data(self) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# Good: Blocking operation in thread
async def process_heavy_computation(data: bytes) -> Result:
    result = await asyncio.to_thread(heavy_function, data)
    return result

# Good: WebSocket handler
async def websocket_handler(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            response = await process_message(data)
            await websocket.send_text(response)
    except WebSocketDisconnect:
        pass
```

### Frontend (TypeScript) Conventions

#### Code Organization

- **Components**: `components/` - React functional components with hooks
- **Hooks**: Custom hooks prefixed with `use`
- **Contexts**: Context providers for dependency injection
- **Types**: Centralized in `types/index.ts`
- **Services**: Client-side services (WebSocket, API)

#### Import Style

```typescript
// React (first)
import { useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';

// Third-party libraries
import { create } from 'zustand';

// Components
import { Desktop } from './components/Desktop';
import { Window } from './components/Window';

// Hooks/Contexts
import { useGameStore } from './stores/gameStore';
import { useWebSocket } from './contexts/WebSocketContext';

// Types
import type { NPC, WindowState } from './types';

// Utilities
import { appApi } from './utils/appApi';

// Styles (last)
import './styles/desktop.css';
```

#### Component Structure

```typescript
// Props interface
interface ChatAppProps {
  initialNpcId?: string;
  onClose?: () => void;
}

// Functional component with TypeScript
export function ChatApp({ initialNpcId, onClose }: ChatAppProps) {
  // Hooks first (state, context, etc.)
  const [selectedNpc, setSelectedNpc] = useState<NPC | null>(null);
  const [message, setMessage] = useState('');
  const { npcs } = useGameStore();
  const wsClient = useWebSocket();

  // Effects
  useEffect(() => {
    if (initialNpcId) {
      const npc = npcs.find(n => n.id === initialNpcId);
      setSelectedNpc(npc || null);
    }
  }, [initialNpcId, npcs]);

  // Event handlers (useCallback for optimization)
  const handleSendMessage = useCallback(() => {
    if (!selectedNpc || !message.trim()) return;

    wsClient.sendMessage({
      type: 'chat',
      data: {
        npc_id: selectedNpc.id,
        message: message.trim(),
      },
    });

    setMessage('');
  }, [selectedNpc, message, wsClient]);

  // Render
  return (
    <div className="chat-app">
      {/* JSX */}
    </div>
  );
}
```

#### TypeScript Conventions

```typescript
// Use interfaces for object shapes
interface NPC {
  id: string;
  name: string;
  avatar: string;
  personality: NPCPersonality;
}

// Use type for unions, intersections, primitives
type NPCPersonality = 'FRIENDLY' | 'MYSTERIOUS' | 'GRUMPY';
type Status = 'idle' | 'loading' | 'error';

// Use strict mode (enabled in tsconfig.json)
// - No implicit any
// - Strict null checks
// - No unused locals/parameters

// Always annotate function parameters and returns
function processNPC(npc: NPC): string {
  return `${npc.name} (${npc.id})`;
}

// Use optional chaining and nullish coalescing
const npcName = npc?.name ?? 'Unknown';

// Avoid 'any' - use 'unknown' if type is truly unknown
function parseJSON(input: string): unknown {
  return JSON.parse(input);
}
```

#### React Patterns

```typescript
// Use functional components (not class components)
export function MyComponent() { /* ... */ }

// Use hooks (not HOCs or render props)
const [state, setState] = useState<Type>(initial);
const value = useContext(MyContext);
const ref = useRef<HTMLDivElement>(null);

// Use TypeScript for props
interface Props {
  required: string;
  optional?: number;
  children?: ReactNode;
}

// Use memo for expensive computations
const expensiveValue = useMemo(() => {
  return computeExpensiveValue(data);
}, [data]);

// Use callback for event handlers passed to children
const handleClick = useCallback(() => {
  // handler logic
}, [dependencies]);
```

---

## Testing Guidelines

### Backend Testing Patterns

#### Fixture-Based Testing

Use pytest fixtures for setup and teardown:

```python
# conftest.py - Shared fixtures
@pytest.fixture
def mock_llm():
    """Mock LLM compatible with LangChain."""
    mock = Mock(spec=BaseChatModel)
    mock.invoke.return_value = AIMessage(content="Test response")
    return mock

@pytest.fixture
def npc_manager(mock_llm):
    """NPCManager with injected mock LLM."""
    return NPCManager(llm=mock_llm)

@pytest.fixture
def sample_npc():
    """Sample NPC for testing."""
    return NPC(
        id="test_npc",
        name="Test NPC",
        personality=NPCPersonality.FRIENDLY,
        role=NPCRole.COMPANION,
        # ...
    )
```

#### Test Organization

Group related tests in classes:

```python
class TestNPCManager:
    """Tests for NPCManager with dependency injection."""

    def test_initialization_with_injected_llm(
        self,
        npc_manager,
        mock_llm
    ):
        """Verify NPCManager uses injected LLM."""
        assert npc_manager.llm is mock_llm

    @pytest.mark.asyncio
    async def test_chat_success(
        self,
        npc_manager,
        sample_npc
    ):
        """Test successful chat interaction."""
        npc_manager.register_npc(sample_npc)

        response = await npc_manager.chat(
            sample_npc.id,
            "Hello!"
        )

        assert response.npc_id == sample_npc.id
        assert response.message
        assert response.timestamp

    def test_chat_nonexistent_npc(self, npc_manager):
        """Test chat with non-existent NPC raises error."""
        with pytest.raises(ValueError, match="not found"):
            await npc_manager.chat("invalid_id", "Hello")
```

#### Testing Async Code

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async functions with pytest-asyncio."""
    result = await some_async_function()
    assert result == expected_value

@pytest.mark.asyncio
async def test_websocket_handler(mock_websocket):
    """Test WebSocket handler."""
    mock_websocket.receive_text.return_value = '{"type": "ping"}'

    await websocket_handler(mock_websocket)

    mock_websocket.send_text.assert_called_once()
```

#### Mocking External Dependencies

```python
def test_ollama_client_with_mock_httpx(mocker):
    """Test OllamaClient with mocked HTTP client."""
    # Mock httpx.AsyncClient
    mock_client = mocker.patch('httpx.AsyncClient')
    mock_client.return_value.__aenter__.return_value.post.return_value = \
        Mock(status_code=200, json=lambda: {"response": "OK"})

    client = OllamaClient()
    response = await client.generate("test prompt")

    assert response == "OK"
```

#### Test Markers

```python
# pytest.ini defines markers
# Use them to categorize tests

@pytest.mark.unit
def test_fast_unit_test():
    """Quick unit test."""
    pass

@pytest.mark.integration
def test_integration_with_database():
    """Integration test (slower)."""
    pass

@pytest.mark.slow
def test_expensive_operation():
    """Slow test (e.g., model loading)."""
    pass

# Run specific tests:
# pytest -m unit              # Only unit tests
# pytest -m "not slow"        # Skip slow tests
# pytest -m integration       # Only integration tests
```

#### Coverage Configuration

Coverage is configured in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src/recursive_neon"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
```

### Frontend Testing Patterns

#### Vitest Configuration

```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    environment: 'jsdom',           // DOM environment
    setupFiles: ['./src/test/setup.ts'],
    globals: true,                  // No need to import describe/it
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.ts', 'src/**/*.tsx'],
      exclude: ['src/test/**', '**/*.test.ts*'],
    },
  },
});
```

#### Test Utilities

```typescript
// src/test/utils/test-utils.tsx
import { render } from '@testing-library/react';
import { AppProviders } from '../../contexts/AppProviders';

export function renderWithProviders(ui: ReactElement) {
  return render(
    <AppProviders>
      {ui}
    </AppProviders>
  );
}
```

#### Component Testing

```typescript
import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test/utils/test-utils';
import { ChatApp } from './ChatApp';

describe('ChatApp', () => {
  it('renders without crashing', () => {
    renderWithProviders(<ChatApp />);
    expect(screen.getByText(/chat/i)).toBeInTheDocument();
  });

  it('sends message when button clicked', async () => {
    const user = userEvent.setup();
    const mockSend = vi.fn();

    renderWithProviders(<ChatApp onSend={mockSend} />);

    const input = screen.getByRole('textbox');
    const button = screen.getByRole('button', { name: /send/i });

    await user.type(input, 'Hello!');
    await user.click(button);

    expect(mockSend).toHaveBeenCalledWith('Hello!');
  });
});
```

---

## Security Principles

### Critical: Virtual Filesystem Isolation

**The most important security principle in this codebase is filesystem isolation.**

#### Overview

The in-game filesystem is **completely isolated** from the player's real filesystem. All file operations work with virtual `FileNode` objects stored in memory.

#### FileNode Structure

```python
class FileNode(BaseModel):
    id: str                    # UUID (NOT a real file path)
    name: str                  # Just a name (NOT a path)
    type: str                  # "file" or "directory"
    parent_id: Optional[str]   # Reference to parent (UUID)
    content: Optional[str]     # File content (in memory)
    mime_type: Optional[str]   # MIME type
```

#### Key Security Features

1. **UUID-Based Identification**: All nodes identified by UUID, not file paths
2. **No Path Traversal**: Names are just strings, not paths
3. **In-Memory Storage**: All content stored in memory as Python objects
4. **UUID References**: Parent-child relationships via UUID references

#### Controlled Real Filesystem Access

The system **only** accesses the real filesystem in three specific ways:

##### 1. Initial State Loading (Read-Only)
```python
# Source: backend/initial_fs/ (read-only)
app_service.load_initial_filesystem("backend/initial_fs")
```

##### 2. Persistence (Save)
```python
# Destination: backend/game_data/filesystem.json
app_service.save_filesystem_to_disk("backend/game_data")
```

##### 3. Persistence (Load)
```python
# Source: backend/game_data/filesystem.json
app_service.load_filesystem_from_disk("backend/game_data")
```

#### Why Path Traversal is Impossible

```python
# Player tries to create file with suspicious name
api.createFile(
    name="../../../etc/passwd",
    parent_id="some-uuid",
    content="malicious",
    mime_type="text/plain"
)

# What happens:
# 1. Creates FileNode with name="../../../etc/passwd" (just a string)
# 2. Stores in memory with UUID: "550e8400-..."
# 3. parent_id references another UUID, not a real path
# 4. Content stored in memory
# 5. NO interaction with real file system
```

#### File Operations Safety

| Operation | Real FS Access? |
|-----------|-----------------|
| `create_file()` | ❌ No - Creates virtual FileNode in memory |
| `create_directory()` | ❌ No - Creates virtual directory node |
| `update_file()` | ❌ No - Updates FileNode in memory |
| `delete_file()` | ❌ No - Removes FileNode from memory |
| `copy_file()` | ❌ No - Duplicates FileNode with new UUID |
| `move_file()` | ❌ No - Changes parent_id reference |
| `list_directory()` | ❌ No - Filters nodes by parent_id |

#### Rules for AI Assistants

**NEVER:**
- Use real file paths in game logic
- Create path-based file operations
- Bypass the FileNode system
- Expose host filesystem to game code

**ALWAYS:**
- Use FileNode UUIDs for file references
- Store content in FileNode.content (in-memory)
- Use AppService methods for file operations
- Validate that new code maintains isolation

**See**: `backend/FILESYSTEM_SECURITY.md` for complete details

### Other Security Considerations

1. **Input Validation**: All user inputs validated with Pydantic
2. **Type Safety**: Pydantic (backend) and TypeScript (frontend) prevent type errors
3. **Dependency Injection**: Prevents globals and hard-to-test code
4. **No Arbitrary Code Execution**: Terminal commands are registered, not eval'd
5. **WebSocket Security**: Messages validated before processing

---

## Common Tasks

### Adding a New NPC

**File**: `backend/src/recursive_neon/services/npc_manager.py`

```python
def create_default_npcs(self) -> List[NPC]:
    """Create default NPCs for the game."""
    default_npcs = [
        # ... existing NPCs

        # Add new NPC here
        NPC(
            id="engineer_nova",           # Unique ID
            name="Nova",                  # Display name
            personality=NPCPersonality.PROFESSIONAL,
            role=NPCRole.MERCHANT,
            background="A skilled engineer who maintains the city's infrastructure.",
            occupation="Systems Engineer",
            location="Engineering Bay",
            greeting="Hey there! Need something fixed?",
            conversation_style="Technical but friendly, uses engineering jargon",
            topics_of_interest=[
                "infrastructure",
                "technology",
                "problem-solving"
            ],
            avatar="👷‍♀️",
            theme_color="#FFA500"
        ),
    ]
    # ...
    return default_npcs
```

**Test your NPC**:
1. Restart backend
2. Open Chat app
3. Look for new NPC in sidebar
4. Start a conversation

### Adding a Terminal Command

**File**: `frontend/src/terminal/commands/mycommand.ts`

```typescript
import type { Command, CommandContext } from '../core/CommandRegistry';

export const myCommand: Command = {
  name: 'mycommand',
  description: 'Does something useful',
  usage: 'mycommand [OPTIONS] ARGS',

  async execute(context: CommandContext): Promise<number> {
    const { session, args, api } = context;

    // Parse arguments
    if (args.length === 0) {
      session.writeLine('Usage: mycommand <arg>');
      return 1;
    }

    // Do something
    const result = await doSomething(args[0]);

    // Write output
    session.writeLine(result);

    return 0; // Success
  },

  async complete(context: CompletionContext): Promise<string[]> {
    // Provide tab completion suggestions
    return ['option1', 'option2', 'option3'];
  },
};
```

**Register command**:
```typescript
// frontend/src/terminal/commands/builtins.ts
import { myCommand } from './mycommand';

export function registerBuiltinCommands(registry: CommandRegistry) {
  // ... existing commands
  registry.register(myCommand);
}
```

### Adding a Backend Service

1. **Define interface** (`services/interfaces.py`):
```python
class IMyService(ABC):
    @abstractmethod
    async def do_something(self, param: str) -> Result:
        """Do something useful."""
        pass
```

2. **Implement service** (`services/my_service.py`):
```python
class MyService(IMyService):
    def __init__(self, dependency: ISomeDependency):
        self.dependency = dependency

    async def do_something(self, param: str) -> Result:
        # Implementation
        pass
```

3. **Add to ServiceContainer** (`dependencies.py`):
```python
@dataclass
class ServiceContainer:
    # ... existing services
    my_service: IMyService
```

4. **Update ServiceFactory** (`dependencies.py`):
```python
@staticmethod
def create_production_container() -> ServiceContainer:
    # ... create other services
    my_service = MyService(dependency=some_dependency)

    return ServiceContainer(
        # ... existing services
        my_service=my_service,
    )
```

5. **Write tests** (`tests/unit/test_my_service.py`):
```python
class TestMyService:
    @pytest.fixture
    def mock_dependency(self):
        return Mock(spec=ISomeDependency)

    @pytest.fixture
    def my_service(self, mock_dependency):
        return MyService(dependency=mock_dependency)

    @pytest.mark.asyncio
    async def test_do_something(self, my_service):
        result = await my_service.do_something("test")
        assert result.success
```

### Adding a Desktop App

1. **Create component** (`frontend/src/components/apps/MyApp.tsx`):
```typescript
export function MyApp() {
  const [data, setData] = useState<Data | null>(null);
  const wsClient = useWebSocket();

  // Implementation

  return (
    <div className="my-app">
      {/* UI */}
    </div>
  );
}
```

2. **Add icon to Desktop** (`frontend/src/components/Desktop.tsx`):
```typescript
const desktopIcons = [
  // ... existing icons
  {
    id: 'my-app',
    name: 'My App',
    icon: '🎯',
    onClick: () => {
      openWindow({
        title: 'My App',
        type: 'my-app',
        content: <MyApp />,
        size: { width: 600, height: 400 },
        position: { x: 100, y: 100 },
      });
    },
  },
];
```

3. **Add styling** (`frontend/src/styles/desktop.css`):
```css
.my-app {
  padding: 1rem;
  height: 100%;
  /* styles */
}
```

### Adding a WebSocket Message Type

1. **Define message type** (backend):
```python
# services/message_handler.py
async def handle_message(
    self,
    msg_type: str,
    msg_data: dict
) -> Dict[str, Any]:
    if msg_type == "my_message":
        return await self._handle_my_message(msg_data)
    # ...

async def _handle_my_message(
    self,
    data: dict
) -> Dict[str, Any]:
    # Handle message
    return {"status": "success", "data": result}
```

2. **Send from frontend**:
```typescript
wsClient.sendMessage({
  type: 'my_message',
  data: {
    param1: 'value1',
    param2: 'value2',
  },
});
```

3. **Handle response**:
```typescript
useEffect(() => {
  const handleMessage = (event: MessageEvent) => {
    const message = JSON.parse(event.data);

    if (message.type === 'my_message_response') {
      // Handle response
      console.log(message.data);
    }
  };

  // Add listener
  wsClient.addEventListener('message', handleMessage);

  return () => {
    wsClient.removeEventListener('message', handleMessage);
  };
}, [wsClient]);
```

---

## Git Workflow

### Branch Naming

- Main branch: `main` (or as specified in project)
- Feature branches: `feature/description`
- Bug fixes: `fix/description`
- For Claude Code tasks: `claude/claude-md-{session-id}`

### Commit Messages

Follow conventional commit format:

```
<type>: <short description>

<optional longer description>

<optional footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `style`: Code style changes (formatting, etc.)

**Examples**:
```bash
git commit -m "feat: add new NPC engineer Nova"

git commit -m "fix: terminal scrolling bug on long output"

git commit -m "docs: update CLAUDE.md with testing guidelines"

git commit -m "refactor: extract FileNode validation to helper function"

git commit -m "test: add integration tests for app_service"
```

### Push Workflow

```bash
# Always push to feature branch
git push -u origin feature/my-feature

# For Claude Code tasks, use the specified branch
git push -u origin claude/claude-md-{session-id}
```

### Pull Request Workflow

1. **Create PR** from feature branch to main
2. **Add description**:
   - What changed
   - Why it changed
   - How to test
3. **Link issues** if applicable
4. **Request review** if working with a team
5. **Ensure tests pass**
6. **Merge** when approved

---

## Key Files Reference

### Backend Entry Points

- **Main Application**: `backend/src/recursive_neon/main.py`
  - FastAPI app definition
  - Lifespan management
  - Route definitions

- **Dependency Injection**: `backend/src/recursive_neon/dependencies.py`
  - ServiceContainer definition
  - ServiceFactory for creating containers
  - get_container() for FastAPI DI

- **Configuration**: `backend/src/recursive_neon/config.py`
  - Pydantic Settings class
  - Environment variable loading

### Backend Core Services

- **NPC Manager**: `backend/src/recursive_neon/services/npc_manager.py`
  - NPC registration and management
  - Chat handling with LangChain
  - Default NPC creation

- **Ollama Client**: `backend/src/recursive_neon/services/ollama_client.py`
  - HTTP client for Ollama API
  - Health checking
  - Request/response handling

- **Process Manager**: `backend/src/recursive_neon/services/process_manager.py`
  - Ollama process lifecycle
  - Startup/shutdown handling

- **App Service**: `backend/src/recursive_neon/services/app_service.py`
  - Virtual filesystem operations
  - Notes and tasks management
  - Persistence handling

- **Message Handler**: `backend/src/recursive_neon/services/message_handler.py`
  - WebSocket message routing
  - Message type dispatching

### Backend Models

- **NPC Models**: `backend/src/recursive_neon/models/npc.py`
  - NPC class
  - ChatRequest/ChatResponse
  - NPCPersonality, NPCRole enums

- **Game State**: `backend/src/recursive_neon/models/game_state.py`
  - SystemState
  - GameState

- **App Models**: `backend/src/recursive_neon/models/app_models.py`
  - FileNode
  - Note
  - Task

### Frontend Entry Points

- **Main Entry**: `frontend/src/main.tsx`
  - React root rendering
  - App providers setup

- **Root Component**: `frontend/src/App.tsx`
  - Top-level component
  - Provider composition

- **Desktop**: `frontend/src/components/Desktop.tsx`
  - Main desktop UI
  - Window management
  - Desktop icons

### Frontend Core Components

- **Window Manager**: `frontend/src/components/Window.tsx`
  - Window rendering
  - Drag and resize
  - Focus management

- **Taskbar**: `frontend/src/components/Taskbar.tsx`
  - Bottom taskbar
  - Window switching
  - System status

### Frontend Apps

- **Chat App**: `frontend/src/components/apps/ChatApp.tsx`
  - NPC chat interface
  - Message history
  - NPC selection

- **Terminal App**: `frontend/src/components/apps/TerminalApp.tsx`
  - Terminal emulator UI
  - Command execution

- **File Browser**: `frontend/src/components/apps/FileBrowserApp.tsx`
  - Virtual filesystem navigation
  - File operations

### Frontend Services

- **WebSocket Client**: `frontend/src/services/websocket.ts`
  - WebSocket connection management
  - Message sending/receiving
  - Reconnection logic

- **App API**: `frontend/src/utils/appApi.ts`
  - Backend API client
  - Filesystem operations
  - Notes/tasks operations

### Frontend State

- **Game Store**: `frontend/src/stores/gameStore.ts`
  - Zustand store
  - NPCs state
  - Windows management
  - Global game state

### Frontend Contexts

- **Game Store Context**: `frontend/src/contexts/GameStoreContext.tsx`
  - GameStore provider
  - useGameStoreContext hook

- **WebSocket Context**: `frontend/src/contexts/WebSocketContext.tsx`
  - WebSocket provider
  - useWebSocket hook

### Terminal System

- **Terminal Session**: `frontend/src/terminal/core/TerminalSession.ts`
  - Session state management
  - Command history
  - Working directory

- **Command Registry**: `frontend/src/terminal/core/CommandRegistry.ts`
  - Command registration
  - Command execution

- **Completion Engine**: `frontend/src/terminal/core/CompletionEngine.ts`
  - Tab completion
  - Path completion

- **Output Renderer**: `frontend/src/terminal/core/OutputRenderer.ts`
  - ANSI parsing
  - Styled output

- **Builtin Commands**: `frontend/src/terminal/commands/builtins.ts`
  - Standard commands (ls, cd, cat, etc.)

### Configuration Files

- **Backend Package**: `backend/pyproject.toml`
  - Python dependencies
  - Build configuration
  - Pytest settings
  - Coverage settings

- **Frontend Package**: `frontend/package.json`
  - NPM dependencies
  - Scripts
  - Project metadata

- **TypeScript Config**: `frontend/tsconfig.json`
  - Compiler options (strict mode)
  - Module resolution

- **Vite Config**: `frontend/vite.config.ts`
  - Build configuration
  - Dev server settings

- **Vitest Config**: `frontend/vitest.config.ts`
  - Test environment
  - Coverage settings

### Testing Files

- **Backend Fixtures**: `backend/tests/conftest.py`
  - Shared pytest fixtures
  - Mock objects

- **Frontend Setup**: `frontend/src/test/setup.ts`
  - Vitest setup
  - Global test configuration

### Documentation

- **Main README**: `README.md`
  - Project overview
  - Setup instructions
  - Usage guide

- **Architecture**: `docs/ARCHITECTURE.md`
  - Why Ollama
  - System architecture

- **Filesystem Security**: `backend/FILESYSTEM_SECURITY.md`
  - Security design
  - Isolation guarantees

- **Terminal Design**: `docs/terminal-design.md`
  - Terminal architecture
  - Design decisions

- **Terminal API**: `docs/terminal-api-guide.md`
  - Terminal API reference

- **Quick Start**: `docs/QUICKSTART.md`
  - Quick setup guide

---

## Summary

This guide provides comprehensive information for AI assistants working on the RecursiveNeon codebase. Key principles:

1. **Security First**: Maintain virtual filesystem isolation at all costs
2. **Dependency Injection**: Use DI for testability and modularity
3. **Type Safety**: Leverage Pydantic and TypeScript for correctness
4. **Testing**: Write tests for all new features
5. **Documentation**: Keep docs in sync with code

**Always refer to existing code** for patterns and conventions. When in doubt, ask for clarification before making changes.

**For updates to this guide**: Edit this file and keep it in sync with the actual codebase state.

---

*Generated by AI Assistant on 2025-11-13*
