"""Shared fixtures for shell tests."""

from __future__ import annotations

import pytest

from recursive_neon.config import settings
from recursive_neon.dependencies import ServiceFactory
from recursive_neon.shell.output import CapturedOutput
from recursive_neon.shell.programs import ProgramContext
from recursive_neon.shell.session import ShellSession


@pytest.fixture
def test_container(mock_llm):
    """A test ServiceContainer with initialized filesystem."""
    container = ServiceFactory.create_test_container(
        mock_npc_manager=ServiceFactory.create_npc_manager(llm=mock_llm),
    )
    container.app_service.load_initial_filesystem(
        initial_fs_dir=str(settings.initial_fs_path)
    )
    return container


@pytest.fixture
def session(test_container):
    """A ShellSession with initialized filesystem."""
    return ShellSession(container=test_container)


@pytest.fixture
def output():
    """A CapturedOutput for testing."""
    return CapturedOutput()


@pytest.fixture
def make_ctx(test_container, output):
    """Factory for ProgramContext with given args."""

    def _make(args: list[str], cwd_id: str | None = None) -> ProgramContext:
        root_id = test_container.game_state.filesystem.root_id
        return ProgramContext(
            args=args,
            stdout=output,
            stderr=output,
            env={"USER": "test", "HOME": "/", "HOSTNAME": "test-host"},
            services=test_container,
            cwd_id=cwd_id or root_id,
        )

    return _make
