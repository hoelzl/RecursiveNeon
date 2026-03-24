"""Tests for shell builtins."""

import pytest

from recursive_neon.shell.builtins import builtin_cd, builtin_exit, builtin_export


@pytest.mark.unit
class TestCd:
    async def test_cd_to_directory(self, session, output):
        result = await builtin_cd(session, ["cd", "/Documents"], output)
        assert result == 0
        assert session.get_cwd_path() == "/Documents"

    async def test_cd_no_args_goes_home(self, session, output):
        # First cd somewhere else
        await builtin_cd(session, ["cd", "/Documents"], output)
        # Then cd with no args
        result = await builtin_cd(session, ["cd"], output)
        assert result == 0
        assert session.get_cwd_path() == "/"

    async def test_cd_relative_path(self, session, output):
        result = await builtin_cd(session, ["cd", "Documents"], output)
        assert result == 0
        assert session.get_cwd_path() == "/Documents"

    async def test_cd_dotdot(self, session, output):
        await builtin_cd(session, ["cd", "/Documents"], output)
        result = await builtin_cd(session, ["cd", ".."], output)
        assert result == 0
        assert session.get_cwd_path() == "/"

    async def test_cd_nonexistent(self, session, output):
        result = await builtin_cd(session, ["cd", "/nonexistent"], output)
        assert result == 1
        assert "No such file or directory" in output.error_text

    async def test_cd_to_file(self, session, output):
        result = await builtin_cd(session, ["cd", "/welcome.txt"], output)
        assert result == 1
        assert "not a directory" in output.error_text


@pytest.mark.unit
class TestExit:
    async def test_exit_returns_sentinel(self, session, output):
        result = await builtin_exit(session, ["exit"], output)
        assert result == -1
        assert session.last_exit_code == 0

    async def test_exit_with_code(self, session, output):
        result = await builtin_exit(session, ["exit", "42"], output)
        assert result == -1
        assert session.last_exit_code == 42

    async def test_exit_invalid_code(self, session, output):
        result = await builtin_exit(session, ["exit", "abc"], output)
        assert result == 1
        assert "numeric argument required" in output.error_text


@pytest.mark.unit
class TestExport:
    async def test_export_set_variable(self, session, output):
        result = await builtin_export(session, ["export", "FOO=bar"], output)
        assert result == 0
        assert session.env["FOO"] == "bar"

    async def test_export_no_args_lists_vars(self, session, output):
        result = await builtin_export(session, ["export"], output)
        assert result == 0
        assert "USER=" in output.text

    async def test_export_empty_value(self, session, output):
        result = await builtin_export(session, ["export", "FOO="], output)
        assert result == 0
        assert session.env["FOO"] == ""

    async def test_export_name_only(self, session, output):
        result = await builtin_export(session, ["export", "NEWVAR"], output)
        assert result == 0
        assert session.env["NEWVAR"] == ""
