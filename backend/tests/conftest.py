"""
Shared test fixtures and configuration for pytest.

This module provides common fixtures used across all test modules.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from typing import AsyncGenerator

# Import models for test fixtures
from backend.models.npc import NPC


@pytest.fixture
def mock_llm():
    """
    Fixture providing a mock LLM instance compatible with LangChain.

    Returns a mock object that satisfies LangChain's Runnable interface requirements.
    The mock is configured with spec to avoid strict type checking while maintaining
    the necessary methods for ConversationChain.
    """
    from langchain_core.runnables import Runnable
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import LLMResult, Generation

    # Create a more sophisticated mock that inherits from a base class
    # This avoids Pydantic validation issues with ConversationChain
    mock = Mock(spec=BaseChatModel)

    # Create a proper LLMResult object
    default_response = "Mock response from LLM"
    llm_result = LLMResult(
        generations=[[Generation(text=default_response)]],
        llm_output={}
    )

    # Return AIMessage objects for message-based methods
    mock.invoke = Mock(return_value=AIMessage(content=default_response))
    mock.ainvoke = AsyncMock(return_value=AIMessage(content=default_response))

    # Add additional methods that ConversationChain might use
    mock.generate_prompt = Mock(return_value=llm_result)
    mock.predict = Mock(return_value=default_response)
    mock.predict_messages = Mock(return_value=AIMessage(content=default_response))
    mock.__call__ = Mock(return_value=default_response)

    # Make the mock iterable (return empty list) to avoid "not iterable" errors
    mock.__iter__ = Mock(return_value=iter([]))

    # Add necessary attributes for LangChain compatibility
    mock._is_runnable = True

    return mock


@pytest.fixture
def sample_npc():
    """
    Fixture providing a sample NPC for testing.

    Returns a fully configured NPC instance with all required fields.
    """
    from backend.models.npc import NPCPersonality, NPCRole

    return NPC(
        id="test_npc_1",
        name="Test NPC",
        personality=NPCPersonality.FRIENDLY,
        role=NPCRole.INFORMANT,
        background="A test NPC created for unit testing purposes",
        occupation="Tester",
        location="Test Suite",
        greeting="Hello! I'm a test NPC.",
        conversation_style="friendly and helpful"
    )


@pytest.fixture
def multiple_npcs(sample_npc):
    """
    Fixture providing multiple NPCs for testing.

    Returns a list of NPC instances.
    """
    from backend.models.npc import NPCPersonality, NPCRole

    npc2 = NPC(
        id="test_npc_2",
        name="Second NPC",
        personality=NPCPersonality.PROFESSIONAL,
        role=NPCRole.MERCHANT,
        background="Another test NPC for testing purposes",
        occupation="Professional Tester",
        location="Test Lab",
        greeting="Greetings.",
        conversation_style="professional and concise"
    )
    return [sample_npc, npc2]


@pytest.fixture
def mock_ollama_client():
    """
    Fixture providing a mock Ollama client.

    Returns a mock OllamaClient with common methods mocked.
    """
    mock = AsyncMock()
    mock.list_models = AsyncMock(return_value=[
        {"name": "llama3.2:3b"},
        {"name": "llama3.2:1b"}
    ])
    mock.check_health = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_process_manager():
    """
    Fixture providing a mock Ollama process manager.

    Returns a mock OllamaProcessManager with common methods mocked.
    """
    mock = Mock()
    mock.start = Mock(return_value=True)
    mock.stop = Mock()
    mock.is_running = Mock(return_value=True)
    mock.get_port = Mock(return_value=11434)
    return mock


@pytest.fixture
async def mock_websocket():
    """
    Fixture providing a mock WebSocket connection.

    Returns a mock WebSocket with send/receive methods.
    """
    mock = AsyncMock()
    mock.accept = AsyncMock()
    mock.send_json = AsyncMock()
    mock.send_text = AsyncMock()
    mock.receive_json = AsyncMock()
    mock.receive_text = AsyncMock()
    mock.close = AsyncMock()
    return mock


# Add custom pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
