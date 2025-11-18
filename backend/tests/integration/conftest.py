# Integration tests conftest
# Shared fixtures for integration tests

import pytest
import asyncio


@pytest.fixture(autouse=True)
async def cleanup_tasks():
    """Ensure all async tasks are cleaned up after each test."""
    yield
    # Cancel all pending tasks created during the test
    tasks = [t for t in asyncio.all_tasks() if not t.done() and not t.get_coro().__name__.startswith('test_')]
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
