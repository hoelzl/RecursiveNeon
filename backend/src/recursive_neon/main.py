"""
Recursive://Neon Backend Server

FastAPI server that manages:
- WebSocket connections for real-time communication
- NPC conversations via LangChain
- Ollama process lifecycle
- Game state

Refactored to use dependency injection for improved testability.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from recursive_neon.config import settings
from recursive_neon.models.npc import ChatRequest, ChatResponse, NPCListResponse
from recursive_neon.models.game_state import SystemStatus, StatusResponse
from recursive_neon.dependencies import ServiceContainer, ServiceFactory, get_container, initialize_container

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager - refactored with dependency injection

    Creates and initializes the service container, then stores it in app.state
    for use throughout the application.
    """
    logger.info("=" * 60)
    logger.info("Recursive://Neon Backend Starting")
    logger.info("=" * 60)

    container = None

    try:
        # Create service container with all dependencies
        logger.info("Creating service container...")
        container = ServiceFactory.create_production_container()

        # Initialize global container for dependency injection
        initialize_container(container)

        # Store in app state for access in endpoints
        app.state.services = container

        # 1. Start ollama server
        logger.info("Starting ollama server...")
        if not await container.process_manager.start():
            raise Exception("Failed to start ollama server")

        # 2. Wait for ollama to be ready
        logger.info("Waiting for ollama to be ready...")
        if not await container.ollama_client.wait_for_ready(max_wait=30):
            raise Exception("Ollama server did not become ready")

        container.system_state.ollama_running = True

        # 3. List available models
        models = await container.ollama_client.list_models()
        logger.info(f"Available models: {models}")
        container.system_state.ollama_models_loaded = models

        # 4. Create default NPCs
        logger.info("Creating default NPCs...")
        npcs = container.npc_manager.create_default_npcs()
        container.system_state.npcs_loaded = len(npcs)
        logger.info(f"Loaded {len(npcs)} NPCs")

        # 5. System ready
        container.system_state.status = SystemStatus.READY
        logger.info("=" * 60)
        logger.info("Recursive://Neon Backend Ready!")
        logger.info(f"WebSocket: ws://{settings.host}:{settings.port}/ws")
        logger.info(f"Health: http://{settings.host}:{settings.port}/health")
        logger.info("=" * 60)

        yield  # Server runs here

    except Exception as e:
        logger.error(f"Startup error: {e}")
        if container:
            container.system_state.status = SystemStatus.ERROR
            container.system_state.last_error = str(e)
        raise

    finally:
        # Shutdown
        logger.info("Shutting down...")
        if container:
            container.system_state.status = SystemStatus.SHUTTING_DOWN

            # Save filesystem state before shutdown
            logger.info("Saving in-game filesystem state...")
            try:
                container.app_service.save_filesystem_to_disk()
                logger.info("Filesystem state saved successfully")
            except Exception as e:
                logger.error(f"Failed to save filesystem state: {e}")

            # Save calendar data before shutdown
            logger.info("Saving calendar data...")
            try:
                calendar_data_path = settings.game_data_path / "calendar.json"
                container.calendar_service.save_to_disk(str(calendar_data_path))
                logger.info("Calendar data saved successfully")
            except Exception as e:
                logger.error(f"Failed to save calendar data: {e}")

            await container.ollama_client.close()
            await container.process_manager.stop()

        logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Recursive://Neon Backend",
    description="Backend server for Recursive://Neon RPG",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HTTP Endpoints
# ============================================================================

@app.get("/")
async def root(container: ServiceContainer = Depends(get_container)):
    """Root endpoint - now uses dependency injection"""
    return {
        "name": "Recursive://Neon",
        "version": "0.1.0",
        "status": container.system_state.status.value
    }


@app.get("/health", response_model=StatusResponse)
async def health_check(container: ServiceContainer = Depends(get_container)):
    """Health check endpoint - now uses dependency injection"""
    uptime = (datetime.now() - container.start_time).total_seconds()
    container.system_state.uptime_seconds = uptime

    return StatusResponse(
        status="healthy" if container.system_state.status == SystemStatus.READY else "unhealthy",
        system=container.system_state
    )


@app.get("/npcs", response_model=NPCListResponse)
async def list_npcs(container: ServiceContainer = Depends(get_container)):
    """Get list of all NPCs - now uses dependency injection"""
    npcs = container.npc_manager.list_npcs()
    return NPCListResponse(npcs=npcs)


@app.get("/npcs/{npc_id}")
async def get_npc(npc_id: str, container: ServiceContainer = Depends(get_container)):
    """Get specific NPC details - now uses dependency injection"""
    npc = container.npc_manager.get_npc(npc_id)
    if not npc:
        raise HTTPException(status_code=404, detail=f"NPC not found: {npc_id}")

    return npc


@app.post("/chat", response_model=ChatResponse)
async def chat_with_npc(
    request: ChatRequest,
    container: ServiceContainer = Depends(get_container)
):
    """
    Chat with an NPC (HTTP endpoint) - now uses dependency injection
    For simple request/response. Use WebSocket for streaming.
    """
    try:
        response = await container.npc_manager.chat(
            npc_id=request.npc_id,
            message=request.message,
            player_id=request.player_id
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/stats")
async def get_stats(container: ServiceContainer = Depends(get_container)):
    """Get system statistics - now uses dependency injection"""
    return {
        "system": container.system_state.dict(),
        "ollama_process": container.process_manager.get_status(),
        "npc_manager": container.npc_manager.get_stats()
    }


# ============================================================================
# WebSocket Endpoint
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


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    container: ServiceContainer = Depends(get_container)
):
    """
    Main WebSocket endpoint for real-time communication - refactored with DI

    Now uses dependency injection to access services, making it testable
    without a running server.

    Message format:
    {
        "type": "chat" | "get_npcs" | "ping" | ...,
        "data": { ... }
    }
    """
    await manager.connect(websocket)

    # Get message handler from container
    message_handler = container.message_handler

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            msg_type = data.get("type")
            msg_data = data.get("data", {})

            logger.debug(f"WebSocket message: {msg_type}")

            # Special handling for chat to send thinking indicator
            if msg_type == "chat":
                npc_id = msg_data.get("npc_id")
                if npc_id:
                    # Send thinking indicator before processing
                    thinking = await message_handler.create_thinking_indicator(npc_id)
                    await manager.send_personal(thinking, websocket)

            # Handle message using message handler service
            response = await message_handler.handle_message(msg_type, msg_data)

            # Send response
            await manager.send_personal(response, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


def main():
    """Entry point for the Recursive://Neon backend server"""
    import uvicorn
    uvicorn.run(
        "recursive_neon.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )


if __name__ == "__main__":
    main()
