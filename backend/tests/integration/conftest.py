"""
Integration tests conftest
Shared fixtures and configuration for integration tests
"""

import pytest
import asyncio
import gc
from unittest.mock import Mock


@pytest.fixture(scope="function", autouse=True)
async def cleanup_async_resources():
    """Clean up async resources after each test to prevent leakage."""
    # Store initial tasks
    initial_tasks = set(asyncio.all_tasks())

    yield

    # Cancel any new tasks created during the test
    current_tasks = set(asyncio.all_tasks())
    new_tasks = current_tasks - initial_tasks

    for task in new_tasks:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass  # Ignore other exceptions during cleanup

    # Force garbage collection to clean up any lingering references
    gc.collect()


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks between tests to prevent pollution."""
    yield
    # Mock.reset_mock() is called automatically by pytest-mock
    # But we ensure cleanup happens
    gc.collect()


@pytest.fixture(scope="function")
def isolated_event_loop():
    """Provide a fresh event loop for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop

    # Clean up the loop
    try:
        # Cancel all tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # Run until all tasks are cancelled
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        # Shutdown async generators
        loop.run_until_complete(loop.shutdown_asyncgens())

        # Shutdown default executor
        loop.run_until_complete(loop.shutdown_default_executor())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture
def cleanup_tasks_list():
    """Track and cleanup async tasks created during a test."""
    tasks = []

    def register_task(task):
        """Register a task for cleanup."""
        tasks.append(task)
        return task

    yield register_task

    # Cleanup all registered tasks
    for task in tasks:
        if not task.done():
            task.cancel()
            try:
                # Try to await task cancellation
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Can't await in running loop, just cancel
                    pass
                else:
                    loop.run_until_complete(task)
            except (asyncio.CancelledError, RuntimeError):
                pass


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset any global state that might leak between tests."""
    yield

    # Clean up any imported modules' state if needed
    # This helps with FastAPI app state and dependency injection
    import sys
    if 'recursive_neon.dependencies' in sys.modules:
        deps = sys.modules['recursive_neon.dependencies']
        if hasattr(deps, '_container'):
            deps._container = None

    gc.collect()
