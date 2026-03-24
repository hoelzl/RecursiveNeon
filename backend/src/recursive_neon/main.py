"""
Recursive://Neon Backend Server

FastAPI server that manages:
- WebSocket connections for real-time communication
- NPC conversations via LangChain
- Ollama process lifecycle
- Game state and virtual filesystem
"""

import logging
import warnings
from contextlib import asynccontextmanager
from datetime import datetime

# Suppress pydantic.v1 warning on Python 3.14+ (langchain-core imports it internally).
# TECH-DEBT: Remove once langchain-core drops the pydantic.v1 import.
# Track: docs/TECH_DEBT.md #TD-001
warnings.filterwarnings(
    "ignore",
    message=r"Core Pydantic V1 functionality isn't compatible with Python 3\.14",
    category=UserWarning,
)

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

            # Save filesystem state
            logger.info("Saving in-game filesystem state...")
            try:
                container.app_service.save_filesystem_to_disk()
                logger.info("Filesystem state saved successfully")
            except Exception as e:
                logger.error(f"Failed to save filesystem state: {e}")

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
    uptime = (datetime.now() - container.start_time).total_seconds()
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
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def send_personal(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
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
