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
from recursive_neon.models.ws_messages import (
    CompleteMessage,
    InputMessage,
    KeyMessage,
    ResizeMessage,
    parse_client_message,
)
from recursive_neon.services.interfaces import (
    IConnectionManager,
    ITerminalSessionManager,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def get_terminal_manager(
    container: ServiceContainer = Depends(get_container),
) -> ITerminalSessionManager:
    return container.terminal_manager


async def get_connection_manager(
    container: ServiceContainer = Depends(get_container),
) -> IConnectionManager:
    return container.connection_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with dependency injection."""
    logger.info("=" * 60)
    logger.info("Recursive://Neon Backend Starting")
    logger.info("=" * 60)

    container = None

    try:
        container = await ServiceFactory.create_production_container()
        initialize_container(container)

        # Start ollama server. Failure is non-fatal: chat endpoints will
        # return a clear error, but the rest of the backend stays usable.
        logger.info("Starting ollama server...")
        try:
            ollama_started = await container.process_manager.start()
            if not ollama_started:
                raise Exception("process_manager.start() returned False")

            logger.info("Waiting for ollama to be ready...")
            if not await container.ollama_client.wait_for_ready(max_wait=30):
                raise Exception("Ollama server did not become ready")

            container.system_state.ollama_running = True

            # List available models
            models = await container.ollama_client.list_models()
            logger.info(f"Available models: {models}")
            container.system_state.ollama_models_loaded = models
        except Exception as e:
            logger.error(f"Ollama unavailable, continuing in degraded mode: {e}")
            container.system_state.status = SystemStatus.DEGRADED
            container.system_state.last_error = str(e)

        # NPC state is already loaded by create_production_container()
        # (from disk if available, otherwise defaults are created there).
        npcs = container.npc_manager.list_npcs()
        container.system_state.npcs_loaded = len(npcs)
        logger.info(f"Loaded {len(npcs)} NPCs")

        if container.system_state.status != SystemStatus.DEGRADED:
            container.system_state.status = SystemStatus.READY
            logger.info("=" * 60)
            logger.info("Recursive://Neon Backend Ready!")
        else:
            logger.info("=" * 60)
            logger.info("Recursive://Neon Backend Ready (degraded)")
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
                await container.app_service.save_all_to_disk(data_dir)
                await container.npc_manager.save_npcs_to_disk(data_dir)
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
    if not container.system_state.ollama_running:
        raise HTTPException(
            status_code=503,
            detail="Ollama service is unavailable; chat is disabled.",
        )
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
        "ollama_process": await container.process_manager.get_status(),
        "npc_manager": container.npc_manager.get_stats(),
    }


# ============================================================================
# WebSocket
# ============================================================================


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    container: ServiceContainer = Depends(get_container),
    manager: IConnectionManager = Depends(get_connection_manager),
):
    """
    Main WebSocket endpoint for real-time communication.

    Message format:
    {
        "type": "chat" | "get_npcs" | "ping" | "app",
        "data": { ... }
    }
    """
    if not await manager.connect(websocket):
        return

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            msg_data = data.get("data", {})

            logger.debug(f"WebSocket message: {msg_type}")

            response = await handle_ws_message(container, msg_type, msg_data)
            await manager.send_personal(response, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
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
            if not container.system_state.ollama_running:
                return {
                    "type": "error",
                    "data": {
                        "message": "Ollama service is unavailable; chat is disabled."
                    },
                }
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
        logger.error(f"Error handling {msg_type}: {e}", exc_info=True)
        return {"type": "error", "data": {"message": "Internal server error"}}


async def handle_app_message(container: ServiceContainer, msg_data: dict) -> dict:
    """Handle app-related WebSocket messages (filesystem, notes, tasks)."""
    action = str(msg_data.get("action", ""))
    app_type = str(msg_data.get("app_type", ""))

    try:
        result = container.app_service.handle_action(app_type, action, msg_data)
        return {"type": "app_response", "data": result}
    except ValueError as e:
        # Client errors (unknown action, missing fields) — safe to expose
        return {"type": "error", "data": {"message": str(e)}}
    except Exception as e:
        logger.error(f"App message error: {e}", exc_info=True)
        return {"type": "error", "data": {"message": "Internal server error"}}


# ============================================================================
# WebSocket Terminal
# ============================================================================


@app.websocket("/ws/terminal")
async def terminal_websocket(
    websocket: WebSocket,
    terminal_manager: ITerminalSessionManager = Depends(get_terminal_manager),
):
    """WebSocket endpoint for interactive terminal sessions.

    Protocol (JSON messages):
        Client → Server:
            {"type": "input", "line": "ls -la"}        # cooked mode
            {"type": "complete", "line": "ls Doc"}      # cooked mode
            {"type": "key", "key": "ArrowUp"}           # raw mode

        Server → Client:
            {"type": "output", "text": "..."}
            {"type": "prompt", "text": "user@neon:~$ "}
            {"type": "completions", "items": ["Documents/"], "replace": 0}
            {"type": "mode", "mode": "raw"|"cooked"}    # mode switch
            {"type": "screen", "lines": [...], ...}      # raw mode frame
            {"type": "exit"}
            {"type": "error", "message": "..."}
    """
    await websocket.accept()

    if terminal_manager.active_count >= terminal_manager.max_connections:
        await websocket.close(code=1013, reason="Server overloaded")
        return

    session = terminal_manager.create_session()

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
        await terminal_manager.remove_session(session.session_id)


async def _ws_reader(websocket: WebSocket, session) -> None:
    """Read messages from the WebSocket and feed them into the shell."""
    while True:
        try:
            msg = parse_client_message(await websocket.receive_json())
        except ValueError as e:
            await websocket.send_json({"type": "error", "message": str(e)})
            continue

        if isinstance(msg, InputMessage):
            if session.mode == "cooked":
                session.feed_line(msg.line)
        elif isinstance(msg, KeyMessage):
            if session.mode == "raw":
                session.feed_key(msg.key)
        elif isinstance(msg, ResizeMessage):
            session.feed_resize(msg.width, msg.height)
        elif isinstance(msg, CompleteMessage):
            if session.mode == "cooked":
                items, replace = await session.shell.get_completions_ext_async(msg.line)
                await websocket.send_json(
                    {"type": "completions", "items": items, "replace": replace}
                )
        else:
            await websocket.send_json(
                {"type": "error", "message": f"Unknown message type: {msg.type}"}
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
