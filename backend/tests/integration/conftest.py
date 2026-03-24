"""Shared fixtures for integration tests."""

from __future__ import annotations

import pytest

from recursive_neon.config import settings
from recursive_neon.dependencies import ServiceFactory
from recursive_neon.shell.output import CapturedOutput
from recursive_neon.shell.shell import Shell

_INITIAL_FS = str(settings.initial_fs_path)


@pytest.fixture
def shell(mock_llm):
    """A fully wired Shell with CapturedOutput for integration testing."""
    container = ServiceFactory.create_test_container(
        mock_npc_manager=ServiceFactory.create_npc_manager(llm=mock_llm),
    )
    container.app_service.load_initial_filesystem(initial_fs_dir=_INITIAL_FS)
    container.npc_manager.create_default_npcs()
    output = CapturedOutput()
    return Shell(container=container, output=output)


@pytest.fixture
def shell_with_data_dir(mock_llm, tmp_path):
    """A Shell with data_dir set for persistence testing."""
    container = ServiceFactory.create_test_container(
        mock_npc_manager=ServiceFactory.create_npc_manager(llm=mock_llm),
    )
    container.app_service.load_initial_filesystem(initial_fs_dir=_INITIAL_FS)
    container.npc_manager.create_default_npcs()
    output = CapturedOutput()
    return Shell(
        container=container, output=output, data_dir=str(tmp_path)
    ), str(tmp_path)
