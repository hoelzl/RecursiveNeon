"""
Process Manager - Controls the ollama server process

Refactored to implement IProcessManager interface for better testability.
"""
import subprocess
import platform
import logging
import asyncio
import os
import signal
from pathlib import Path
from typing import Optional
import psutil

from recursive_neon.services.interfaces import IProcessManager

logger = logging.getLogger(__name__)


class OllamaProcessManager(IProcessManager):
    """
    Manages the ollama server process lifecycle

    Implements IProcessManager interface for dependency injection support.

    Responsibilities:
    - Start/stop ollama server
    - Monitor process health
    - Handle graceful shutdown
    """

    def __init__(
        self,
        binary_path: str = "../services/ollama",
        host: str = "127.0.0.1",
        port: int = 11434
    ):
        self.binary_path = Path(binary_path)
        self.host = host
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self._monitor_task: Optional[asyncio.Task] = None

    def _get_ollama_binary(self) -> Path:
        """Locate the ollama binary for the current platform"""
        system = platform.system()

        if system == "Windows":
            binary = self.binary_path / "ollama.exe"
        else:  # Linux, macOS
            binary = self.binary_path / "ollama"

        if not binary.exists():
            # Try to find in system PATH
            import shutil
            if system_binary := shutil.which("ollama"):
                return Path(system_binary)

            raise FileNotFoundError(
                f"Ollama binary not found at {binary}. "
                "Please run scripts/download_ollama.py or install ollama system-wide."
            )

        return binary

    async def start(self) -> bool:
        """
        Start the ollama server

        Returns:
            True if started successfully
        """
        if self.is_running():
            logger.info("Ollama server is already running")
            return True

        try:
            binary = self._get_ollama_binary()
            logger.info(f"Starting ollama server: {binary}")

            # Set environment variables
            env = os.environ.copy()
            env["OLLAMA_HOST"] = f"{self.host}:{self.port}"

            # Start the process
            self.process = subprocess.Popen(
                [str(binary), "serve"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )

            # Start monitoring
            self._monitor_task = asyncio.create_task(self._monitor_process())

            logger.info(f"Ollama server started (PID: {self.process.pid})")
            return True

        except Exception as e:
            logger.error(f"Failed to start ollama server: {e}")
            return False

    async def _monitor_process(self):
        """Monitor the ollama process and log output"""
        if not self.process:
            return

        try:
            # Read stderr in background (ollama logs to stderr)
            while self.process.poll() is None:
                if self.process.stderr:
                    line = self.process.stderr.readline()
                    if line:
                        logger.debug(f"Ollama: {line.decode().strip()}")
                await asyncio.sleep(0.1)

            # Process ended
            logger.warning(f"Ollama process ended with code {self.process.returncode}")
        except Exception as e:
            logger.error(f"Error monitoring ollama process: {e}")

    def is_running(self) -> bool:
        """Check if the ollama process is running"""
        if self.process is None:
            return False

        # Check if our process is still alive
        if self.process.poll() is not None:
            return False

        # Verify it's actually running
        try:
            proc = psutil.Process(self.process.pid)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    async def stop(self, timeout: int = 10) -> bool:
        """
        Stop the ollama server gracefully

        Args:
            timeout: Maximum seconds to wait for shutdown

        Returns:
            True if stopped successfully
        """
        if not self.is_running():
            logger.info("Ollama server is not running")
            return True

        try:
            logger.info("Stopping ollama server...")

            # Cancel monitor task
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass

            # Try graceful shutdown
            if self.process:
                self.process.terminate()

                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=timeout)
                    logger.info("Ollama server stopped gracefully")
                    return True
                except subprocess.TimeoutExpired:
                    logger.warning("Graceful shutdown timed out, forcing kill")
                    self.process.kill()
                    self.process.wait(timeout=5)
                    logger.info("Ollama server killed")
                    return True

        except Exception as e:
            logger.error(f"Error stopping ollama server: {e}")
            return False

        return True

    def get_status(self) -> dict:
        """Get current status of the ollama process"""
        if not self.is_running():
            return {
                "running": False,
                "pid": None,
                "memory_mb": 0,
                "cpu_percent": 0
            }

        try:
            proc = psutil.Process(self.process.pid)
            return {
                "running": True,
                "pid": self.process.pid,
                "memory_mb": proc.memory_info().rss / 1024 / 1024,
                "cpu_percent": proc.cpu_percent(interval=0.1)
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"Error getting process status: {e}")
            return {
                "running": False,
                "pid": None,
                "memory_mb": 0,
                "cpu_percent": 0
            }
