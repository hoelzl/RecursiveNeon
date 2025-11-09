"""
Ollama HTTP Client - manages communication with local ollama server

Refactored to implement IOllamaClient interface for better testability.
"""
import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List, AsyncIterator
from dataclasses import dataclass

from .interfaces import IOllamaClient

logger = logging.getLogger(__name__)


@dataclass
class GenerationResponse:
    """Response from ollama generation"""
    text: str
    total_duration_ms: float
    prompt_eval_count: int
    eval_count: int

    @property
    def tokens_per_second(self) -> float:
        """Calculate tokens/second"""
        if self.total_duration_ms > 0:
            return (self.eval_count / self.total_duration_ms) * 1000
        return 0.0


class OllamaClient(IOllamaClient):
    """
    Client for communicating with ollama server

    Implements IOllamaClient interface for dependency injection support.

    Handles:
    - Health checking
    - Text generation (streaming and non-streaming)
    - Model management
    - Error handling and retries
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 11434,
        timeout: int = 60
    ):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def health_check(self) -> bool:
        """Check if ollama server is responding"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    async def wait_for_ready(self, max_wait: int = 30, check_interval: float = 0.5) -> bool:
        """
        Wait for ollama server to be ready

        Args:
            max_wait: Maximum seconds to wait
            check_interval: Seconds between checks

        Returns:
            True if server became ready, False if timeout
        """
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < max_wait:
            if await self.health_check():
                logger.info("Ollama server is ready")
                return True
            await asyncio.sleep(check_interval)

        logger.error(f"Ollama server did not become ready within {max_wait}s")
        return False

    async def list_models(self) -> List[str]:
        """Get list of available models"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def generate(
        self,
        prompt: str,
        model: str = "phi3:mini",
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 200,
        stream: bool = False
    ) -> GenerationResponse:
        """
        Generate text completion

        Args:
            prompt: User prompt
            model: Model name
            system: System prompt (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response

        Returns:
            GenerationResponse with generated text
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        if system:
            payload["system"] = system

        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            return GenerationResponse(
                text=data.get("response", ""),
                total_duration_ms=data.get("total_duration", 0) / 1_000_000,  # ns to ms
                prompt_eval_count=data.get("prompt_eval_count", 0),
                eval_count=data.get("eval_count", 0)
            )
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        model: str = "phi3:mini",
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 200
    ) -> AsyncIterator[str]:
        """
        Generate text completion with streaming

        Yields text chunks as they're generated
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        if system:
            payload["system"] = system

        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if chunk := data.get("response"):
                            yield chunk
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            raise

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "phi3:mini",
        temperature: float = 0.7,
        max_tokens: int = 200
    ) -> str:
        """
        Chat completion (multi-turn conversation)

        Args:
            messages: List of {role: str, content: str} dicts
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response text
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
