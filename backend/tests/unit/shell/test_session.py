"""Tests for ShellSession state management."""

from __future__ import annotations

import pytest

from recursive_neon.shell.output import CapturedOutput
from recursive_neon.shell.session import ShellSession
from recursive_neon.shell.shell import Shell


@pytest.fixture
def shell(test_container):
    return Shell(container=test_container, output=CapturedOutput())


@pytest.mark.unit
class TestHistory:
    def test_history_capped_at_limit(self, test_container):
        session = ShellSession(container=test_container)
        for i in range(1005):
            session.add_history(f"line_{i}")
        assert len(session.history) == 1000
        assert session.history[0] == "line_5"
        assert session.history[-1] == "line_1004"

    def test_add_history_keeps_order(self, test_container):
        session = ShellSession(container=test_container)
        session.add_history("first")
        session.add_history("second")
        assert session.history == ["first", "second"]


@pytest.mark.unit
class TestPrompt:
    def test_build_prompt_uses_ps1_env_var(self, shell):
        shell.session.env["PS1"] = r"[\u@\h \w]\$ "
        prompt = shell._build_prompt()
        assert shell.session.username in prompt
        assert shell.session.hostname in prompt
        assert shell.session.get_cwd_path() in prompt
        assert "$" in prompt

    def test_build_prompt_falls_back_when_ps1_missing(self, shell):
        shell.session.env.pop("PS1", None)
        prompt = shell._build_prompt()
        assert shell.session.username in prompt
        assert shell.session.get_cwd_path() in prompt
