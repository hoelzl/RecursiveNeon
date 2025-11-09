"""
Recursive://Neon Backend Server

FastAPI server that manages:
- WebSocket connections for real-time communication
- NPC conversations via LangChain
- Ollama process lifecycle
- Game state
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .services.process_manager import OllamaProcessManager
from .services.ollama_client import OllamaClient
from .services.npc_manager import NPCManager
from .models.npc import ChatRequest, ChatResponse, NPCListResponse
from .models.game_state import SystemState, SystemStatus, StatusResponse

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
process_manager: OllamaProcessManager = None
ollama_client: OllamaClient = None
npc_manager: NPCManager = None
system_state = SystemState()
start_time = datetime.now()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown
    """
    global process_manager, ollama_client, npc_manager, system_state

    logger.info("=" * 60)
    logger.info("Recursive://Neon Backend Starting")
    logger.info("=" * 60)

    try:
        # 1. Initialize process manager
        logger.info("Initializing ollama process manager...")
        process_manager = OllamaProcessManager(
            binary_path=settings.ollama_binary_path,
            host=settings.ollama_host,
            port=settings.ollama_port
        )

        # 2. Start ollama server
        logger.info("Starting ollama server...")
        if not await process_manager.start():
            raise Exception("Failed to start ollama server")

        # 3. Initialize ollama client
        logger.info("Initializing ollama client...")
        ollama_client = OllamaClient(
            host=settings.ollama_host,
            port=settings.ollama_port,
            timeout=settings.ollama_timeout
        )

        # 4. Wait for ollama to be ready
        logger.info("Waiting for ollama to be ready...")
        if not await ollama_client.wait_for_ready(max_wait=30):
            raise Exception("Ollama server did not become ready")

        system_state.ollama_running = True

        # 5. List available models
        models = await ollama_client.list_models()
        logger.info(f"Available models: {models}")
        system_state.ollama_models_loaded = models

        # 6. Initialize NPC manager
        logger.info("Initializing NPC manager...")
        npc_manager = NPCManager(
            ollama_host=settings.ollama_host,
            ollama_port=settings.ollama_port
        )

        # 7. Create default NPCs
        logger.info("Creating default NPCs...")
        npcs = npc_manager.create_default_npcs()
        system_state.npcs_loaded = len(npcs)
        logger.info(f"Loaded {len(npcs)} NPCs")

        # 8. System ready
        system_state.status = SystemStatus.READY
        logger.info("=" * 60)
        logger.info("Recursive://Neon Backend Ready!")
        logger.info(f"WebSocket: ws://{settings.host}:{settings.port}/ws")
        logger.info(f"Health: http://{settings.host}:{settings.port}/health")
        logger.info("=" * 60)

        yield  # Server runs here

    except Exception as e:
        logger.error(f"Startup error: {e}")
        system_state.status = SystemStatus.ERROR
        system_state.last_error = str(e)
        raise

    finally:
        # Shutdown
        logger.info("Shutting down...")
        system_state.status = SystemStatus.SHUTTING_DOWN

        if ollama_client:
            await ollama_client.close()

        if process_manager:
            await process_manager.stop()

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
async def root():
    """Root endpoint"""
    return {
        "name": "Recursive://Neon",
        "version": "0.1.0",
        "status": system_state.status.value
    }


@app.get("/health", response_model=StatusResponse)
async def health_check():
    """Health check endpoint"""
    uptime = (datetime.now() - start_time).total_seconds()
    system_state.uptime_seconds = uptime

    return StatusResponse(
        status="healthy" if system_state.status == SystemStatus.READY else "unhealthy",
        system=system_state
    )


@app.get("/npcs", response_model=NPCListResponse)
async def list_npcs():
    """Get list of all NPCs"""
    if not npc_manager:
        raise HTTPException(status_code=503, detail="NPC manager not initialized")

    npcs = npc_manager.list_npcs()
    return NPCListResponse(npcs=npcs)


@app.get("/npcs/{npc_id}")
async def get_npc(npc_id: str):
    """Get specific NPC details"""
    if not npc_manager:
        raise HTTPException(status_code=503, detail="NPC manager not initialized")

    npc = npc_manager.get_npc(npc_id)
    if not npc:
        raise HTTPException(status_code=404, detail=f"NPC not found: {npc_id}")

    return npc


@app.post("/chat", response_model=ChatResponse)
async def chat_with_npc(request: ChatRequest):
    """
    Chat with an NPC (HTTP endpoint)
    For simple request/response. Use WebSocket for streaming.
    """
    if not npc_manager:
        raise HTTPException(status_code=503, detail="NPC manager not initialized")

    try:
        response = await npc_manager.chat(
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
async def get_stats():
    """Get system statistics"""
    if not npc_manager or not process_manager:
        raise HTTPException(status_code=503, detail="System not initialized")

    return {
        "system": system_state.dict(),
        "ollama_process": process_manager.get_status(),
        "npc_manager": npc_manager.get_stats()
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
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time communication

    Message format:
    {
        "type": "chat" | "get_npcs" | "ping" | ...,
        "data": { ... }
    }
    """
    await manager.connect(websocket)

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            msg_type = data.get("type")
            msg_data = data.get("data", {})

            logger.debug(f"WebSocket message: {msg_type}")

            # Handle different message types
            if msg_type == "ping":
                await manager.send_personal({"type": "pong", "data": {}}, websocket)

            elif msg_type == "get_npcs":
                npcs = npc_manager.list_npcs()
                await manager.send_personal({
                    "type": "npcs_list",
                    "data": {
                        "npcs": [npc.dict() for npc in npcs]
                    }
                }, websocket)

            elif msg_type == "chat":
                npc_id = msg_data.get("npc_id")
                message = msg_data.get("message")
                player_id = msg_data.get("player_id", "player_1")

                if not npc_id or not message:
                    await manager.send_personal({
                        "type": "error",
                        "data": {"message": "Missing npc_id or message"}
                    }, websocket)
                    continue

                try:
                    # Send thinking indicator
                    await manager.send_personal({
                        "type": "chat_thinking",
                        "data": {"npc_id": npc_id}
                    }, websocket)

                    # Get response from NPC
                    response = await npc_manager.chat(npc_id, message, player_id)

                    # Send response
                    await manager.send_personal({
                        "type": "chat_response",
                        "data": response.dict()
                    }, websocket)

                except Exception as e:
                    logger.error(f"Chat error: {e}")
                    await manager.send_personal({
                        "type": "error",
                        "data": {"message": str(e)}
                    }, websocket)

            elif msg_type == "get_status":
                uptime = (datetime.now() - start_time).total_seconds()
                await manager.send_personal({
                    "type": "status",
                    "data": {
                        "system": system_state.dict(),
                        "uptime_seconds": uptime
                    }
                }, websocket)

            else:
                await manager.send_personal({
                    "type": "error",
                    "data": {"message": f"Unknown message type: {msg_type}"}
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )
