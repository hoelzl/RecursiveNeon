"""
LLM Controller using standalone llama.cpp server
This approach is more reliable for distribution as it uses pre-built binaries
"""

import asyncio
import logging
import subprocess
import platform
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import psutil
import httpx
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServerState(Enum):
    UNINITIALIZED = "uninitialized"
    STARTING = "starting"
    READY = "ready"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class ServerMetrics:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_tokens_per_sec: float = 0.0
    memory_mb: float = 0.0
    queue_depth: int = 0
    last_inference_time_ms: float = 0.0


class LLMServerController:
    """
    Controls standalone llama.cpp server process
    
    This approach is better for distribution because:
    - Uses pre-built binaries (no compilation needed)
    - Server handles GPU detection automatically
    - Easy to ship with game
    - Works on any Windows machine
    """
    
    def __init__(
        self,
        model_path: str,
        server_binary: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8080,
        n_ctx: int = 2048,
        n_gpu_layers: int = -1,  # -1 = auto-detect
        temperature: float = 0.7,
        max_tokens: int = 256
    ):
        self.model_path = Path(model_path)
        self.host = host
        self.port = port
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Locate server binary
        self.server_binary = self._locate_server_binary(server_binary)
        
        # Server process
        self.process: Optional[subprocess.Popen] = None
        self.state = ServerState.UNINITIALIZED
        self.metrics = ServerMetrics()
        
        # HTTP client for API calls
        self.client = httpx.AsyncClient(timeout=60.0)
        self.base_url = f"http://{host}:{port}"
        
        logger.info(f"Controller initialized with server: {self.server_binary}")
    
    def _locate_server_binary(self, provided_path: Optional[str]) -> Path:
        """
        Locate llama.cpp server binary
        Tries: provided path -> bundled with app -> system PATH
        """
        if provided_path:
            path = Path(provided_path)
            if path.exists():
                return path
        
        # Check for bundled binaries (distribution mode)
        app_dir = Path(__file__).parent
        
        # Try CUDA version first (if available)
        cuda_binary = app_dir / "libs" / "cuda" / "llama-server.exe"
        cpu_binary = app_dir / "libs" / "cpu" / "llama-server.exe"
        
        if self._has_cuda() and cuda_binary.exists():
            logger.info("Using CUDA-enabled server")
            return cuda_binary
        elif cpu_binary.exists():
            logger.info("Using CPU-only server")
            return cpu_binary
        
        # Try system PATH
        system = platform.system()
        binary_name = "llama-server.exe" if system == "Windows" else "llama-server"
        
        # Check if in PATH
        import shutil
        if shutil.which(binary_name):
            return Path(binary_name)
        
        raise FileNotFoundError(
            f"Could not locate llama.cpp server binary. "
            f"Please download from https://github.com/ggerganov/llama.cpp/releases "
            f"and place in libs/cuda/ or libs/cpu/"
        )
    
    def _has_cuda(self) -> bool:
        """Check if CUDA is available on the system"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            # No PyTorch, try nvidia-smi
            try:
                result = subprocess.run(
                    ["nvidia-smi"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            except:
                return False
    
    async def start(self) -> bool:
        """
        Start the llama.cpp server process
        Returns True if successful
        """
        if not self.model_path.exists():
            logger.error(f"Model file not found: {self.model_path}")
            self.state = ServerState.ERROR
            return False
        
        self.state = ServerState.STARTING
        logger.info("Starting llama.cpp server...")
        
        # Build command
        cmd = [
            str(self.server_binary),
            "--model", str(self.model_path),
            "--host", self.host,
            "--port", str(self.port),
            "--ctx-size", str(self.n_ctx),
            "--threads", str(psutil.cpu_count(logical=False)),
        ]
        
        # Add GPU layers if specified
        if self.n_gpu_layers >= 0:
            cmd.extend(["--n-gpu-layers", str(self.n_gpu_layers)])
        else:
            # Auto-detect mode
            cmd.append("--n-gpu-layers")
            cmd.append("999" if self._has_cuda() else "0")
        
        try:
            # Start server process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            # Wait for server to be ready
            logger.info("Waiting for server to start...")
            if await self._wait_for_ready(timeout=60):
                self.state = ServerState.READY
                logger.info(f"✅ Server ready at {self.base_url}")
                return True
            else:
                logger.error("Server failed to start within timeout")
                self.state = ServerState.ERROR
                return False
                
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self.state = ServerState.ERROR
            return False
    
    async def _wait_for_ready(self, timeout: int = 60) -> bool:
        """Wait for server to be ready by polling health endpoint"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = await self.client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return True
            except:
                pass
            
            # Check if process died
            if self.process and self.process.poll() is not None:
                stderr = self.process.stderr.read() if self.process.stderr else b""
                logger.error(f"Server process died: {stderr.decode()}")
                return False
            
            await asyncio.sleep(1)
        
        return False
    
    async def generate(
        self,
        prompt: str,
        npc_id: str = "default",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        priority: int = 0
    ) -> str:
        """
        Generate response using the server API
        
        Args:
            prompt: Input prompt
            npc_id: NPC identifier (for logging)
            max_tokens: Override default max_tokens
            temperature: Override default temperature
            priority: Priority (for future queuing - currently not used)
            
        Returns:
            Generated text
        """
        if self.state != ServerState.READY:
            raise RuntimeError(f"Server not ready (state: {self.state.value})")
        
        self.metrics.total_requests += 1
        start_time = time.time()
        
        try:
            # Call completion endpoint
            response = await self.client.post(
                f"{self.base_url}/completion",
                json={
                    "prompt": prompt,
                    "n_predict": max_tokens or self.max_tokens,
                    "temperature": temperature or self.temperature,
                    "stop": ["\n\n", "Human:", "Player:"],
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract generated text
            generated_text = data.get("content", "")
            
            # Update metrics
            elapsed_ms = (time.time() - start_time) * 1000
            self.metrics.last_inference_time_ms = elapsed_ms
            self.metrics.successful_requests += 1
            
            # Calculate tokens/sec (rough estimate)
            if "timings" in data:
                tokens = data["timings"].get("predicted_n", 0)
                duration_ms = data["timings"].get("predicted_ms", 1)
                tokens_per_sec = (tokens / duration_ms) * 1000 if duration_ms > 0 else 0
                
                # Exponential moving average
                alpha = 0.3
                self.metrics.avg_tokens_per_sec = (
                    alpha * tokens_per_sec +
                    (1 - alpha) * self.metrics.avg_tokens_per_sec
                )
            
            logger.info(
                f"✅ Generated response for {npc_id} in {elapsed_ms:.0f}ms "
                f"({self.metrics.avg_tokens_per_sec:.1f} tok/s)"
            )
            
            return generated_text.strip()
            
        except Exception as e:
            self.metrics.failed_requests += 1
            logger.error(f"❌ Generation failed for {npc_id}: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get current server status"""
        is_running = self.process is not None and self.process.poll() is None
        
        # Get memory usage
        memory_mb = 0
        if self.process:
            try:
                process = psutil.Process(self.process.pid)
                memory_mb = process.memory_info().rss / 1024 / 1024
            except:
                pass
        
        self.metrics.memory_mb = memory_mb
        
        return {
            "state": self.state.value,
            "is_running": is_running,
            "server_url": self.base_url,
            "model_path": str(self.model_path),
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "success_rate": (
                    self.metrics.successful_requests / max(self.metrics.total_requests, 1) * 100
                ),
                "avg_tokens_per_sec": self.metrics.avg_tokens_per_sec,
                "memory_mb": self.metrics.memory_mb,
                "last_inference_ms": self.metrics.last_inference_time_ms,
            },
            "config": {
                "host": self.host,
                "port": self.port,
                "n_ctx": self.n_ctx,
                "n_gpu_layers": self.n_gpu_layers,
            }
        }
    
    async def shutdown(self):
        """Stop the server process"""
        logger.info("Shutting down server...")
        self.state = ServerState.SHUTTING_DOWN
        
        # Close HTTP client
        await self.client.aclose()
        
        # Terminate process
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Server didn't stop gracefully, killing...")
                self.process.kill()
        
        self.process = None
        self.state = ServerState.UNINITIALIZED
        logger.info("✅ Server stopped")


# Compatibility wrapper for existing code
class LLMController(LLMServerController):
    """
    Wrapper to maintain API compatibility with the old in-process controller
    """
    
    async def initialize(self) -> bool:
        """Alias for start() to match old API"""
        return await self.start()


# Example usage
async def main():
    controller = LLMController(
        model_path="models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        port=8080,
        n_ctx=2048
    )
    
    if await controller.start():
        status = controller.get_status()
        print(f"Server status: {status}")
        
        response = await controller.generate(
            prompt="You are a friendly blacksmith. A customer asks: 'Do you have swords?'",
            npc_id="blacksmith_001"
        )
        
        print(f"\nResponse: {response}")
        
        await controller.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
