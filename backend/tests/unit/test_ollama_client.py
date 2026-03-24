"""Tests for OllamaClient."""

import pytest

from recursive_neon.services.ollama_client import OllamaClient


@pytest.mark.unit
class TestOllamaClientContextManager:
    """Test async context manager support."""

    async def test_async_context_manager_calls_close(self):
        client = OllamaClient(host="127.0.0.1", port=99999)
        async with client as c:
            assert c is client
        # After exiting, the httpx client should be closed
        assert client.client.is_closed

    async def test_close_is_idempotent(self):
        client = OllamaClient(host="127.0.0.1", port=99999)
        await client.close()
        await client.close()  # Should not raise
