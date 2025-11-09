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
    Fixture providing a mock LLM instance.

    Returns a mock object that implements the LLM interface with ainvoke method.
    """
    mock = AsyncMock()
    mock.ainvoke = AsyncMock(return_value="Mock response from LLM")
    return mock


@pytest.fixture
def sample_npc():
    """
    Fixture providing a sample NPC for testing.

    Returns a basic NPC instance with default values.
    """
    return NPC(
        id="test_npc_1",
        name="Test NPC",
        description="A test NPC for unit testing",
        personality="Friendly and helpful",
        knowledge_base="General knowledge",
        initial_message="Hello! I'm a test NPC.",
        model_name="llama3.2:3b"
    )


@pytest.fixture
def multiple_npcs(sample_npc):
    """
    Fixture providing multiple NPCs for testing.

    Returns a list of NPC instances.
    """
    npc2 = NPC(
        id="test_npc_2",
        name="Second NPC",
        description="Another test NPC",
        personality="Professional and concise",
        knowledge_base="Technical knowledge",
        initial_message="Greetings.",
        model_name="llama3.2:3b"
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
