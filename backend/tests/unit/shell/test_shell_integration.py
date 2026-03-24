"""Integration tests for the shell — full command flows."""

import pytest

from recursive_neon.shell.output import CapturedOutput
from recursive_neon.shell.shell import Shell


@pytest.mark.unit
class TestShellExecuteLine:
    """Test Shell.execute_line for command dispatch and state changes."""

    @pytest.fixture
    def shell(self, test_container):
        output = CapturedOutput()
        return Shell(container=test_container, output=output)

    async def test_command_not_found(self, shell):
        code = await shell.execute_line("nonexistent")
        assert code == 127
        assert "command not found" in shell.output.error_text

    async def test_empty_line(self, shell):
        code = await shell.execute_line("")
        assert code == 0

    async def test_pwd_at_root(self, shell):
        code = await shell.execute_line("pwd")
        assert code == 0
        assert shell.output.text.strip() == "/"

    async def test_cd_and_pwd(self, shell):
        code = await shell.execute_line("cd /Documents")
        assert code == 0
        shell.output.reset()
        code = await shell.execute_line("pwd")
        assert code == 0
        assert shell.output.text.strip() == "/Documents"

    async def test_mkdir_cd_touch_cat(self, shell):
        """Full flow: create dir, enter it, create file, read it."""
        assert await shell.execute_line("mkdir /test") == 0
        assert await shell.execute_line("cd /test") == 0
        shell.output.reset()
        assert await shell.execute_line("pwd") == 0
        assert shell.output.text.strip() == "/test"

        assert await shell.execute_line("touch hello.txt") == 0
        shell.output.reset()
        assert await shell.execute_line("ls") == 0
        assert "hello.txt" in shell.output.text

    async def test_exit_returns_sentinel(self, shell):
        code = await shell.execute_line("exit")
        assert code == -1

    async def test_export_and_echo(self, shell):
        assert await shell.execute_line("export MYVAR=hello") == 0
        shell.output.reset()
        assert await shell.execute_line("echo $MYVAR") == 0
        # Note: echo reads from ProgramContext.env which is a copy,
        # but the shell rebuilds it from session.env each time
        assert "hello" in shell.output.text

    async def test_cp_and_verify(self, shell):
        assert (
            await shell.execute_line("cp /welcome.txt /Documents/welcome_copy.txt") == 0
        )
        shell.output.reset()
        assert await shell.execute_line("ls /Documents") == 0
        assert "welcome_copy.txt" in shell.output.text

    async def test_parse_error(self, shell):
        code = await shell.execute_line('echo "unterminated')
        assert code == 1
        assert "Unterminated" in shell.output.error_text

    async def test_help_command(self, shell):
        code = await shell.execute_line("help")
        assert code == 0
        text = shell.output.text
        assert "cd" in text
        assert "ls" in text
        assert "cat" in text

    async def test_dash_h_for_program(self, shell):
        code = await shell.execute_line("ls -h")
        assert code == 0
        assert "ls:" in shell.output.text
        assert "List" in shell.output.text

    async def test_dash_dash_help_for_program(self, shell):
        code = await shell.execute_line("cat --help")
        assert code == 0
        assert "cat:" in shell.output.text

    async def test_dash_h_for_builtin(self, shell):
        code = await shell.execute_line("cd -h")
        assert code == 0
        assert "cd (builtin):" in shell.output.text

    async def test_dash_h_unknown_command(self, shell):
        code = await shell.execute_line("nonexistent -h")
        assert code == 127
        assert "command not found" in shell.output.error_text
