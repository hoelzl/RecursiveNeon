"""
Integration tests for OllamaClient

Tests the OllamaClient's integration with Ollama HTTP API endpoints.
Uses pytest-httpx to mock HTTP responses without running a real server.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, Mock, patch
import json

from recursive_neon.services.ollama_client import OllamaClient, GenerationResponse


@pytest.mark.integration
class TestOllamaClientHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, httpx_mock):
        """Test successful health check when Ollama is running."""
        # Mock successful health check
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/tags",
            method="GET",
            json={"models": []},
            status_code=200
        )

        client = OllamaClient()
        is_healthy = await client.health_check()

        assert is_healthy is True
        await client.close()

    @pytest.mark.asyncio
    async def test_health_check_failure_server_down(self, httpx_mock):
        """Test health check when server is not responding."""
        # Mock connection error
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://127.0.0.1:11434/api/tags"
        )

        client = OllamaClient()
        is_healthy = await client.health_check()

        assert is_healthy is False
        await client.close()

    @pytest.mark.asyncio
    async def test_health_check_failure_bad_status(self, httpx_mock):
        """Test health check with non-200 status code."""
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/tags",
            method="GET",
            status_code=500
        )

        client = OllamaClient()
        is_healthy = await client.health_check()

        assert is_healthy is False
        await client.close()


@pytest.mark.integration
class TestOllamaClientWaitForReady:
    """Test wait_for_ready functionality."""

    @pytest.mark.asyncio
    async def test_wait_for_ready_immediate(self, httpx_mock):
        """Test wait_for_ready when server is immediately available."""
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/tags",
            method="GET",
            json={"models": []},
            status_code=200
        )

        client = OllamaClient()
        is_ready = await client.wait_for_ready(max_wait=5)

        assert is_ready is True
        await client.close()

    @pytest.mark.asyncio
    async def test_wait_for_ready_after_delay(self, httpx_mock):
        """Test wait_for_ready when server becomes available after delay."""
        # First two calls fail, third succeeds
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://127.0.0.1:11434/api/tags"
        )
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://127.0.0.1:11434/api/tags"
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/tags",
            method="GET",
            json={"models": []},
            status_code=200
        )

        client = OllamaClient()
        is_ready = await client.wait_for_ready(max_wait=5, check_interval=0.1)

        assert is_ready is True
        await client.close()

    @pytest.mark.asyncio
    async def test_wait_for_ready_timeout(self):
        """Test wait_for_ready timeout when server never becomes ready."""
        client = OllamaClient()

        # Mock health_check to always return False
        with patch.object(client, 'health_check', return_value=False):
            is_ready = await client.wait_for_ready(max_wait=1, check_interval=0.2)

        assert is_ready is False
        await client.close()


@pytest.mark.integration
class TestOllamaClientListModels:
    """Test list_models functionality."""

    @pytest.mark.asyncio
    async def test_list_models_success(self, httpx_mock):
        """Test successful model listing."""
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/tags",
            method="GET",
            json={
                "models": [
                    {"name": "llama3.2:3b"},
                    {"name": "qwen3:4b"},
                    {"name": "phi3:mini"}
                ]
            },
            status_code=200
        )

        client = OllamaClient()
        models = await client.list_models()

        assert len(models) == 3
        assert "llama3.2:3b" in models
        assert "qwen3:4b" in models
        assert "phi3:mini" in models
        await client.close()

    @pytest.mark.asyncio
    async def test_list_models_empty(self, httpx_mock):
        """Test listing models when no models are available."""
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/tags",
            method="GET",
            json={"models": []},
            status_code=200
        )

        client = OllamaClient()
        models = await client.list_models()

        assert len(models) == 0
        await client.close()

    @pytest.mark.asyncio
    async def test_list_models_error(self, httpx_mock):
        """Test list_models when request fails."""
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://127.0.0.1:11434/api/tags"
        )

        client = OllamaClient()
        models = await client.list_models()

        assert models == []  # Returns empty list on error
        await client.close()


@pytest.mark.integration
class TestOllamaClientGenerate:
    """Test generate functionality."""

    @pytest.mark.asyncio
    async def test_generate_success(self, httpx_mock):
        """Test successful text generation."""
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/generate",
            method="POST",
            json={
                "response": "Hello! How can I help you today?",
                "total_duration": 1500000000,  # 1.5 seconds in nanoseconds
                "prompt_eval_count": 10,
                "eval_count": 20
            },
            status_code=200
        )

        client = OllamaClient()
        result = await client.generate(
            prompt="Hello!",
            model="phi3:mini"
        )

        assert isinstance(result, GenerationResponse)
        assert result.text == "Hello! How can I help you today?"
        assert result.total_duration_ms == 1500.0  # Converted to ms
        assert result.prompt_eval_count == 10
        assert result.eval_count == 20
        assert result.tokens_per_second > 0  # Should calculate tokens/sec
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, httpx_mock):
        """Test generation with system prompt."""
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/generate",
            method="POST",
            json={
                "response": "I am a helpful assistant.",
                "total_duration": 1000000000,
                "prompt_eval_count": 15,
                "eval_count": 10
            },
            status_code=200
        )

        client = OllamaClient()
        result = await client.generate(
            prompt="Who are you?",
            model="phi3:mini",
            system="You are a helpful assistant."
        )

        assert result.text == "I am a helpful assistant."
        assert result.prompt_eval_count == 15
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_error(self, httpx_mock):
        """Test generation when request fails."""
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://127.0.0.1:11434/api/generate"
        )

        client = OllamaClient()

        with pytest.raises(httpx.ConnectError):
            await client.generate(prompt="Test", model="phi3:mini")

        await client.close()

    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(self, httpx_mock):
        """Test generation with custom temperature and max_tokens."""
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/generate",
            method="POST",
            json={
                "response": "Creative response",
                "total_duration": 2000000000,
                "prompt_eval_count": 5,
                "eval_count": 50
            },
            status_code=200
        )

        client = OllamaClient()
        result = await client.generate(
            prompt="Tell me a story",
            model="phi3:mini",
            temperature=0.9,
            max_tokens=500
        )

        assert result.text == "Creative response"
        assert result.eval_count == 50
        await client.close()


@pytest.mark.integration
class TestOllamaClientChat:
    """Test chat functionality."""

    @pytest.mark.asyncio
    async def test_chat_success(self, httpx_mock):
        """Test successful chat completion."""
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/chat",
            method="POST",
            json={
                "message": {
                    "role": "assistant",
                    "content": "I'm doing well, thank you!"
                }
            },
            status_code=200
        )

        client = OllamaClient()
        messages = [
            {"role": "user", "content": "How are you?"}
        ]
        response = await client.chat(messages, model="phi3:mini")

        assert response == "I'm doing well, thank you!"
        await client.close()

    @pytest.mark.asyncio
    async def test_chat_multi_turn(self, httpx_mock):
        """Test multi-turn conversation."""
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/chat",
            method="POST",
            json={
                "message": {
                    "role": "assistant",
                    "content": "That's correct! Python is great."
                }
            },
            status_code=200
        )

        client = OllamaClient()
        messages = [
            {"role": "user", "content": "What's your favorite language?"},
            {"role": "assistant", "content": "I like Python."},
            {"role": "user", "content": "Is Python easy to learn?"}
        ]
        response = await client.chat(messages, model="phi3:mini")

        assert "Python" in response
        await client.close()

    @pytest.mark.asyncio
    async def test_chat_error(self, httpx_mock):
        """Test chat when request fails."""
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://127.0.0.1:11434/api/chat"
        )

        client = OllamaClient()
        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(httpx.ConnectError):
            await client.chat(messages, model="phi3:mini")

        await client.close()


@pytest.mark.integration
class TestOllamaClientStreamingGeneration:
    """Test streaming generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_stream_success(self, httpx_mock):
        """Test successful streaming generation."""
        # Mock streaming response
        stream_data = [
            {"response": "Hello", "done": False},
            {"response": " ", "done": False},
            {"response": "world", "done": False},
            {"response": "!", "done": True}
        ]

        # Convert to newline-delimited JSON
        stream_content = "\n".join(json.dumps(item) for item in stream_data)

        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/generate",
            method="POST",
            content=stream_content.encode(),
            status_code=200
        )

        client = OllamaClient()
        chunks = []

        async for chunk in client.generate_stream(
            prompt="Say hello",
            model="phi3:mini"
        ):
            chunks.append(chunk)

        # Should have collected all non-empty chunks
        assert len(chunks) > 0
        assert "".join(chunks) == "Hello world!"
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_stream_error(self, httpx_mock):
        """Test streaming generation when request fails."""
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://127.0.0.1:11434/api/generate"
        )

        client = OllamaClient()

        with pytest.raises(httpx.ConnectError):
            async for chunk in client.generate_stream(
                prompt="Test",
                model="phi3:mini"
            ):
                pass  # Should not reach here

        await client.close()


@pytest.mark.integration
class TestOllamaClientConfiguration:
    """Test client configuration and custom settings."""

    @pytest.mark.asyncio
    async def test_custom_host_port(self, httpx_mock):
        """Test client with custom host and port."""
        httpx_mock.add_response(
            url="http://192.168.1.100:8080/api/tags",
            method="GET",
            json={"models": []},
            status_code=200
        )

        client = OllamaClient(host="192.168.1.100", port=8080)
        is_healthy = await client.health_check()

        assert is_healthy is True
        assert client.base_url == "http://192.168.1.100:8080"
        await client.close()

    @pytest.mark.asyncio
    async def test_custom_timeout(self, httpx_mock):
        """Test client with custom timeout."""
        client = OllamaClient(timeout=120)

        assert client.timeout == 120
        await client.close()

    @pytest.mark.asyncio
    async def test_client_cleanup(self, httpx_mock):
        """Test that client cleanup closes HTTP client properly."""
        client = OllamaClient()

        # Verify client is created
        assert client.client is not None

        # Close client
        await client.close()

        # HTTP client should be closed (checking internal state)
        assert client.client.is_closed


@pytest.mark.integration
class TestOllamaClientTokenCalculation:
    """Test token calculation and performance metrics."""

    @pytest.mark.asyncio
    async def test_tokens_per_second_calculation(self, httpx_mock):
        """Test tokens/second calculation from response."""
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/generate",
            method="POST",
            json={
                "response": "Test response",
                "total_duration": 1000000000,  # 1 second
                "prompt_eval_count": 10,
                "eval_count": 100  # 100 tokens in 1 second = 100 tok/s
            },
            status_code=200
        )

        client = OllamaClient()
        result = await client.generate(prompt="Test", model="phi3:mini")

        # Should calculate ~100 tokens/second
        assert 99 < result.tokens_per_second < 101
        await client.close()

    @pytest.mark.asyncio
    async def test_tokens_per_second_zero_duration(self, httpx_mock):
        """Test tokens/second calculation with zero duration."""
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/generate",
            method="POST",
            json={
                "response": "Test",
                "total_duration": 0,
                "prompt_eval_count": 5,
                "eval_count": 10
            },
            status_code=200
        )

        client = OllamaClient()
        result = await client.generate(prompt="Test", model="phi3:mini")

        # Should return 0 when duration is 0
        assert result.tokens_per_second == 0.0
        await client.close()


@pytest.mark.integration
class TestOllamaClientErrorRecovery:
    """Test error recovery and edge cases."""

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self, httpx_mock):
        """Test handling of malformed JSON response."""
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/generate",
            method="POST",
            json={
                # Missing required fields
                "wrong_field": "value"
            },
            status_code=200
        )

        client = OllamaClient()
        result = await client.generate(prompt="Test", model="phi3:mini")

        # Should handle missing fields gracefully with defaults
        assert result.text == ""  # Default empty string
        assert result.total_duration_ms == 0.0
        assert result.prompt_eval_count == 0
        assert result.eval_count == 0
        await client.close()

    @pytest.mark.asyncio
    async def test_http_error_status(self, httpx_mock):
        """Test handling of HTTP error status codes."""
        httpx_mock.add_response(
            url="http://127.0.0.1:11434/api/generate",
            method="POST",
            status_code=500,
            json={"error": "Internal server error"}
        )

        client = OllamaClient()

        with pytest.raises(httpx.HTTPStatusError):
            await client.generate(prompt="Test", model="phi3:mini")

        await client.close()
