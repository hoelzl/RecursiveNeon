"""
Recursive://Neon Backend Server

FastAPI server that manages:
- WebSocket connections for real-time communication
- NPC conversations via LangChain
- Ollama process lifecycle
- Game state and virtual filesystem
"""

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from recursive_neon.config import settings
from recursive_neon.dependencies import (
    ServiceContainer,
    ServiceFactory,
    get_container,
    initialize_container,
)
from recursive_neon.models.game_state import StatusResponse, SystemStatus
from recursive_neon.models.npc import ChatRequest, ChatResponse, NPCListResponse
from recursive_neon.terminal import TerminalSessionManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with dependency injection."""
    logger.info("=" * 60)
    logger.info("Recursive://Neon Backend Starting")
    logger.info("=" * 60)

    container = None

    try:
        container = ServiceFactory.create_production_container()
        initialize_container(container)
        app.state.services = container

        # Terminal session manager for WebSocket-driven shells
        terminal_manager = TerminalSessionManager(
            container=container,
            data_dir=str(settings.data_dir),
        )
        app.state.terminal_manager = terminal_manager

        # Start ollama server
        logger.info("Starting ollama server...")
        if not await container.process_manager.start():
            raise Exception("Failed to start ollama server")

        # Wait for ollama to be ready
        logger.info("Waiting for ollama to be ready...")
        if not await container.ollama_client.wait_for_ready(max_wait=30):
            raise Exception("Ollama server did not become ready")

        container.system_state.ollama_running = True

        # List available models
        models = await container.ollama_client.list_models()
        logger.info(f"Available models: {models}")
        container.system_state.ollama_models_loaded = models

        # NPC state is already loaded by create_production_container()
        # (from disk if available, otherwise defaults are created there).
        npcs = container.npc_manager.list_npcs()
        container.system_state.npcs_loaded = len(npcs)
        logger.info(f"Loaded {len(npcs)} NPCs")

        # System ready
        container.system_state.status = SystemStatus.READY
        logger.info("=" * 60)
        logger.info("Recursive://Neon Backend Ready!")
        logger.info(f"WebSocket: ws://{settings.host}:{settings.port}/ws")
        logger.info(f"Terminal: ws://{settings.host}:{settings.port}/ws/terminal")
        logger.info(f"Health: http://{settings.host}:{settings.port}/health")
        logger.info("=" * 60)

        yield

    except Exception as e:
        logger.error(f"Startup error: {e}")
        if container:
            container.system_state.status = SystemStatus.ERROR
            container.system_state.last_error = str(e)
        raise

    finally:
        logger.info("Shutting down...")
        if container:
            container.system_state.status = SystemStatus.SHUTTING_DOWN

            # Save all game state
            logger.info("Saving game state...")
            try:
                data_dir = str(settings.data_dir)
                container.app_service.save_all_to_disk(data_dir)
                container.npc_manager.save_npcs_to_disk(data_dir)
                logger.info("Game state saved successfully")
            except Exception as e:
                logger.error(f"Failed to save game state: {e}")

            await container.ollama_client.close()
            await container.process_manager.stop()

        logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Recursive://Neon Backend",
    description="Backend server for Recursive://Neon RPG",
    version="0.2.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HTTP Endpoints
# ============================================================================


@app.get("/")
async def root(container: ServiceContainer = Depends(get_container)):
    return {
        "name": "Recursive://Neon",
        "version": "0.2.0",
        "status": container.system_state.status.value,
    }


@app.get("/health", response_model=StatusResponse)
async def health_check(container: ServiceContainer = Depends(get_container)):
    uptime = (datetime.now(tz=UTC) - container.start_time).total_seconds()
    container.system_state.uptime_seconds = uptime
    return StatusResponse(
        status="healthy"
        if container.system_state.status == SystemStatus.READY
        else "unhealthy",
        system=container.system_state,
    )


@app.get("/npcs", response_model=NPCListResponse)
async def list_npcs(container: ServiceContainer = Depends(get_container)):
    npcs = container.npc_manager.list_npcs()
    return NPCListResponse(npcs=npcs)


@app.get("/npcs/{npc_id}")
async def get_npc(npc_id: str, container: ServiceContainer = Depends(get_container)):
    npc = container.npc_manager.get_npc(npc_id)
    if not npc:
        raise HTTPException(status_code=404, detail=f"NPC not found: {npc_id}")
    return npc


@app.post("/chat", response_model=ChatResponse)
async def chat_with_npc(
    request: ChatRequest, container: ServiceContainer = Depends(get_container)
):
    try:
        response = await container.npc_manager.chat(
            npc_id=request.npc_id, message=request.message, player_id=request.player_id
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/stats")
async def get_stats(container: ServiceContainer = Depends(get_container)):
    return {
        "system": container.system_state.model_dump(),
        "ollama_process": container.process_manager.get_status(),
        "npc_manager": container.npc_manager.get_stats(),
    }


# ============================================================================
# WebSocket
# ============================================================================


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def send_personal(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")


ws_manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, container: ServiceContainer = Depends(get_container)
):
    """
    Main WebSocket endpoint for real-time communication.

    Message format:
    {
        "type": "chat" | "get_npcs" | "ping" | "app",
        "data": { ... }
    }
    """
    await ws_manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            msg_data = data.get("data", {})

            logger.debug(f"WebSocket message: {msg_type}")

            response = await handle_ws_message(container, msg_type, msg_data)
            await ws_manager.send_personal(response, websocket)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
        with contextlib.suppress(Exception):
            await websocket.close(code=1011, reason="Internal error")


async def handle_ws_message(
    container: ServiceContainer, msg_type: str, msg_data: dict
) -> dict:
    """Route WebSocket messages to appropriate handlers."""
    try:
        if msg_type == "ping":
            return {"type": "pong", "data": {}}

        elif msg_type == "get_npcs":
            npcs = container.npc_manager.list_npcs()
            return {
                "type": "npcs_list",
                "data": {"npcs": [npc.model_dump(mode="json") for npc in npcs]},
            }

        elif msg_type == "chat":
            npc_id = str(msg_data.get("npc_id", ""))
            message = str(msg_data.get("message", ""))
            response = await container.npc_manager.chat(npc_id, message)
            return {"type": "chat_response", "data": response.model_dump(mode="json")}

        elif msg_type == "app":
            return await handle_app_message(container, msg_data)

        else:
            return {
                "type": "error",
                "data": {"message": f"Unknown message type: {msg_type}"},
            }

    except Exception as e:
        logger.error(f"Error handling {msg_type}: {e}")
        return {"type": "error", "data": {"message": str(e)}}


async def handle_app_message(container: ServiceContainer, msg_data: dict) -> dict:
    """Handle app-related WebSocket messages (filesystem, notes, tasks)."""
    action = str(msg_data.get("action", ""))
    app_type = str(msg_data.get("app_type", ""))

    try:
        result = container.app_service.handle_action(app_type, action, msg_data)
        return {"type": "app_response", "data": result}
    except Exception as e:
        logger.error(f"App message error: {e}")
        return {"type": "error", "data": {"message": str(e)}}


# ============================================================================
# WebSocket Terminal
# ============================================================================


@app.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    """WebSocket endpoint for interactive terminal sessions.

    Protocol (JSON messages):
        Client → Server:
            {"type": "input", "line": "ls -la"}        # cooked mode
            {"type": "complete", "line": "ls Doc"}      # cooked mode
            {"type": "key", "key": "ArrowUp"}           # raw mode

        Server → Client:
            {"type": "output", "text": "..."}
            {"type": "prompt", "text": "user@neon:~$ "}
            {"type": "completions", "items": ["Documents/"]}
            {"type": "mode", "mode": "raw"|"cooked"}    # mode switch
            {"type": "screen", "lines": [...], ...}      # raw mode frame
            {"type": "exit"}
            {"type": "error", "message": "..."}
    """
    await websocket.accept()

    manager: TerminalSessionManager = app.state.terminal_manager
    session = manager.create_session()

    try:
        await session.start()
        logger.info("Terminal WS connected, session %s", session.session_id)

        # Run two concurrent tasks: read from WS, drain output to WS.
        # When either finishes (e.g. writer sees "exit", or reader gets
        # WebSocketDisconnect), cancel the other to avoid leaked tasks.
        reader = asyncio.create_task(_ws_reader(websocket, session))
        writer = asyncio.create_task(_ws_writer(websocket, session))
        done, pending = await asyncio.wait(
            [reader, writer], return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        # Re-raise exceptions from completed tasks (except disconnect)
        for task in done:
            if task.cancelled():
                continue
            exc = task.exception()
            if exc is not None and not isinstance(exc, WebSocketDisconnect):
                raise exc

    except WebSocketDisconnect:
        logger.info("Terminal WS disconnected, session %s", session.session_id)
    except Exception as e:
        logger.error("Terminal WS error for %s: %s", session.session_id, e)
    finally:
        await manager.remove_session(session.session_id)


async def _ws_reader(websocket: WebSocket, session) -> None:
    """Read messages from the WebSocket and feed them into the shell."""
    while True:
        data = await websocket.receive_json()
        msg_type = data.get("type")

        if msg_type == "input":
            if session.mode == "cooked":
                line = data.get("line", "")
                session.feed_line(line)
            # Ignore input messages in raw mode

        elif msg_type == "key":
            if session.mode == "raw":
                key = data.get("key", "")
                session.feed_key(key)
            # Ignore key messages in cooked mode

        elif msg_type == "complete":
            if session.mode == "cooked":
                line = data.get("line", "")
                items, replace = session.shell.get_completions_ext(line)
                await websocket.send_json(
                    {"type": "completions", "items": items, "replace": replace}
                )

        else:
            await websocket.send_json(
                {"type": "error", "message": f"Unknown message type: {msg_type}"}
            )


async def _ws_writer(websocket: WebSocket, session) -> None:
    """Drain the shell's output queue and send messages to the WebSocket."""
    while True:
        msg = await session.output_queue.get()
        await websocket.send_json(msg)

        if msg["type"] == "exit":
            break


def main():
    """Entry point for the Recursive://Neon backend server"""
    import uvicorn

    uvicorn.run(
        "recursive_neon.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )


if __name__ == "__main__":
    main()
