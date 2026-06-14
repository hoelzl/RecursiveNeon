"""Tests for OllamaClient."""

from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from recursive_neon.services.interfaces import IOllamaClient
from recursive_neon.services.ollama_client import OllamaClient, OllamaLangChainAdapter


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


@pytest.mark.unit
class TestOllamaLangChainAdapter:
    """Test the IOllamaClient -> LLMInterface adapter."""

    async def test_adapter_converts_messages_and_calls_chat(self):
        client = AsyncMock(spec=IOllamaClient)
        client.chat = AsyncMock(return_value="hello")
        adapter = OllamaLangChainAdapter(client, model="m")

        result = await adapter.ainvoke(
            [SystemMessage(content="sys"), HumanMessage(content="hi")]
        )

        assert isinstance(result, AIMessage)
        assert result.content == "hello"
        client.chat.assert_awaited_once()
        call_kwargs = client.chat.call_args[1]
        assert call_kwargs["model"] == "m"
        assert call_kwargs["messages"] == [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ]

    async def test_adapter_maps_ai_message(self):
        client = AsyncMock(spec=IOllamaClient)
        client.chat = AsyncMock(return_value="reply")
        adapter = OllamaLangChainAdapter(client, model="m")

        result = await adapter.ainvoke([AIMessage(content="previous")])
        assert result.content == "reply"
        assert client.chat.call_args[1]["messages"] == [
            {"role": "assistant", "content": "previous"}
        ]

    def test_adapter_invoke_raises(self):
        client = AsyncMock(spec=IOllamaClient)
        adapter = OllamaLangChainAdapter(client, model="m")
        with pytest.raises(NotImplementedError):
            adapter.invoke([])
