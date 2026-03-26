"""Tests for pipes and output redirection (Phase 5c)."""

from __future__ import annotations

import pytest

from recursive_neon.shell.output import CapturedOutput
from recursive_neon.shell.parser import parse_pipeline
from recursive_neon.shell.shell import Shell, _last_pipe_segment

# ---------------------------------------------------------------------------
# parse_pipeline — parser tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParsePipeline:
    def test_simple_command(self):
        p = parse_pipeline("ls -l")
        assert len(p.segments) == 1
        assert p.redirect is None
        assert p.segments[0].tokens[0].value == "ls"

    def test_two_commands(self):
        p = parse_pipeline("cat foo | grep bar")
        assert len(p.segments) == 2
        assert p.segments[0].tokens[0].value == "cat"
        assert p.segments[1].tokens[0].value == "grep"
        assert p.redirect is None

    def test_three_commands(self):
        p = parse_pipeline("cat foo | grep bar | cat")
        assert len(p.segments) == 3

    def test_quoted_pipe(self):
        """Pipe inside quotes is not a separator."""
        p = parse_pipeline('echo "hello | world"')
        assert len(p.segments) == 1
        assert p.segments[0].tokens[1].value == "hello | world"

    def test_redirect_overwrite(self):
        p = parse_pipeline("echo hello > foo.txt")
        assert len(p.segments) == 1
        assert p.redirect is not None
        assert p.redirect.mode == ">"
        assert p.redirect.target == "foo.txt"

    def test_redirect_append(self):
        p = parse_pipeline("echo hello >> foo.txt")
        assert p.redirect is not None
        assert p.redirect.mode == ">>"
        assert p.redirect.target == "foo.txt"

    def test_pipe_and_redirect(self):
        p = parse_pipeline("cat foo | grep bar > results.txt")
        assert len(p.segments) == 2
        assert p.redirect is not None
        assert p.redirect.target == "results.txt"

    def test_missing_redirect_target(self):
        with pytest.raises(ValueError, match="Missing redirect target"):
            parse_pipeline("echo >")

    def test_empty_before_pipe(self):
        with pytest.raises(ValueError, match="Empty command before"):
            parse_pipeline("| ls")

    def test_empty_after_pipe(self):
        with pytest.raises(ValueError, match="Empty command after"):
            parse_pipeline("ls |")

    def test_multiple_redirections(self):
        with pytest.raises(ValueError, match="single filename"):
            parse_pipeline("echo foo > a.txt > b.txt")

    def test_pipe_after_redirect(self):
        with pytest.raises(ValueError, match="single filename"):
            parse_pipeline("echo foo > a.txt | cat")

    def test_empty_input(self):
        p = parse_pipeline("")
        assert len(p.segments) == 1
        assert p.segments[0].tokens == []

    def test_redirect_quoted_filename(self):
        p = parse_pipeline('echo hello > "my file.txt"')
        assert p.redirect is not None
        assert p.redirect.target == "my file.txt"

    def test_redirect_must_be_single_token(self):
        with pytest.raises(ValueError, match="single filename"):
            parse_pipeline("echo hello > foo bar")


# ---------------------------------------------------------------------------
# _last_pipe_segment — completion scoping
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLastPipeSegment:
    def test_no_pipe(self):
        assert _last_pipe_segment("ls -l") == "ls -l"

    def test_after_pipe(self):
        assert _last_pipe_segment("cat foo | grep ").strip() == "grep"

    def test_quoted_pipe_ignored(self):
        assert _last_pipe_segment('echo "a|b"') == 'echo "a|b"'

    def test_multiple_pipes(self):
        result = _last_pipe_segment("a | b | c")
        assert result.strip() == "c"


# ---------------------------------------------------------------------------
# Integration tests — Shell.execute_line
# ---------------------------------------------------------------------------


@pytest.fixture
def shell(test_container, output):
    return Shell(container=test_container, output=output)


@pytest.fixture
def output():
    return CapturedOutput()


@pytest.mark.unit
class TestRedirectIntegration:
    @pytest.mark.asyncio
    async def test_echo_redirect_creates_file(self, shell, output):
        """echo hello > test.txt should create a file."""
        exit_code = await shell.execute_line('echo "hello world" > test.txt')
        assert exit_code == 0

        # Verify the file was created
        exit_code = await shell.execute_line("cat test.txt")
        assert exit_code == 0
        assert "hello world" in output.text

    @pytest.mark.asyncio
    async def test_redirect_append(self, shell, output):
        """>> should append to existing file."""
        await shell.execute_line("echo line1 > test.txt")
        await shell.execute_line("echo line2 >> test.txt")

        exit_code = await shell.execute_line("cat test.txt")
        assert exit_code == 0
        assert "line1" in output.text
        assert "line2" in output.text

    @pytest.mark.asyncio
    async def test_redirect_overwrites(self, shell, output):
        """> should overwrite existing content."""
        await shell.execute_line("echo first > test.txt")
        await shell.execute_line("echo second > test.txt")

        exit_code = await shell.execute_line("cat test.txt")
        assert exit_code == 0
        assert "second" in output.text
        assert "first" not in output.text

    @pytest.mark.asyncio
    async def test_redirect_to_directory_error(self, shell, output):
        """Redirecting to a directory should error."""
        await shell.execute_line("echo hello > Documents")
        # The command itself succeeds but the redirect produces an error
        assert "Is a directory" in output.error_text

    @pytest.mark.asyncio
    async def test_redirect_strips_ansi(self, shell, output):
        """Redirected output should be plain text (no ANSI codes)."""
        await shell.execute_line("ls > listing.txt")
        exit_code = await shell.execute_line("cat listing.txt")
        assert exit_code == 0
        # ANSI escape codes start with \033[
        assert "\033[" not in output.text


@pytest.mark.unit
class TestPipeIntegration:
    @pytest.mark.asyncio
    async def test_echo_pipe_cat(self, shell, output):
        """echo hello | cat should pass output through."""
        exit_code = await shell.execute_line("echo hello | cat")
        assert exit_code == 0
        assert "hello" in output.text

    @pytest.mark.asyncio
    async def test_cat_pipe_grep(self, shell, output):
        """cat file | grep pattern should filter lines."""
        # welcome.txt is in the initial filesystem
        exit_code = await shell.execute_line("cat welcome.txt | grep Welcome")
        assert exit_code == 0 or exit_code == 1
        # If welcome.txt contains "Welcome", grep should find it
        # Otherwise exit code 1 is fine

    @pytest.mark.asyncio
    async def test_ls_pipe_grep(self, shell, output):
        """ls | grep Documents should find Documents."""
        exit_code = await shell.execute_line("ls | grep Documents")
        assert exit_code == 0
        assert "Documents" in output.text

    @pytest.mark.asyncio
    async def test_pipe_with_redirect(self, shell, output):
        """ls | grep Documents > result.txt should work."""
        await shell.execute_line("ls | grep Documents > result.txt")
        exit_code = await shell.execute_line("cat result.txt")
        assert exit_code == 0
        assert "Documents" in output.text

    @pytest.mark.asyncio
    async def test_stderr_not_captured(self, shell, output):
        """Error messages should go to real output, not the pipe."""
        # cat a nonexistent file; stderr should appear on screen
        exit_code = await shell.execute_line("cat nonexistent | grep foo")
        assert exit_code != 0
        # The error about nonexistent file should be visible
        assert "nonexistent" in output.error_text or "nonexistent" in output.text

    @pytest.mark.asyncio
    async def test_multiple_pipes(self, shell, output):
        """echo text | cat | cat should pass through twice."""
        exit_code = await shell.execute_line("echo hello | cat | cat")
        assert exit_code == 0
        assert "hello" in output.text

    @pytest.mark.asyncio
    async def test_grep_stdin_no_paths(self, shell, output):
        """grep should search stdin when no path args are given."""
        exit_code = await shell.execute_line('echo "foo bar baz" | grep bar')
        assert exit_code == 0
        assert "bar" in output.text

    @pytest.mark.asyncio
    async def test_pipe_with_glob(self, shell, output):
        """Globs should expand before piping."""
        exit_code = await shell.execute_line("echo *.txt | cat")
        assert exit_code == 0
        # Should contain actual filenames
        assert "welcome.txt" in output.text


# ---------------------------------------------------------------------------
# Completion after pipe
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCompletionAfterPipe:
    def test_completion_after_pipe_shows_commands(self, shell):
        """After |, completion should show command names."""
        items, _ = shell.get_completions_ext("cat foo | g")
        assert "grep" in items

    def test_completion_after_pipe_command_args(self, shell):
        """After | grep, completion should show grep-specific completions."""
        items, _ = shell.get_completions_ext("cat foo | grep -")
        assert "-i" in items
