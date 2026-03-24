"""Tests for grep, find, and write filesystem programs."""

from __future__ import annotations

import pytest

from recursive_neon.shell.programs.filesystem import prog_find, prog_grep, prog_write


@pytest.mark.unit
class TestGrep:
    async def test_grep_matches(self, make_ctx, output, test_container):
        """Grep finds matching lines."""
        # The initial filesystem has welcome.txt with content
        ctx = make_ctx(["grep", "Welcome", "/welcome.txt"])
        assert await prog_grep(ctx) == 0
        assert "Welcome" in output.text

    async def test_grep_no_match(self, make_ctx, output):
        """Grep returns 1 when no matches found."""
        ctx = make_ctx(["grep", "ZZZNOMATCH", "/welcome.txt"])
        assert await prog_grep(ctx) == 1
        assert output.text.strip() == ""

    async def test_grep_case_insensitive(self, make_ctx, output):
        ctx = make_ctx(["grep", "-i", "welcome", "/welcome.txt"])
        assert await prog_grep(ctx) == 0
        assert output.text.strip() != ""

    async def test_grep_recursive_directory(self, make_ctx, output):
        """Grep recurses into directories."""
        ctx = make_ctx(["grep", ".", "/Documents"])
        result = await prog_grep(ctx)
        # Documents has files with content, so should find something
        assert result == 0
        assert "/Documents/" in output.text

    async def test_grep_regex(self, make_ctx, output, test_container):
        """Grep supports regex patterns."""
        app = test_container.app_service
        root_id = test_container.game_state.filesystem.root_id
        app.create_file(
            {"name": "regex.txt", "parent_id": root_id, "content": "line123\nline456"}
        )
        ctx = make_ctx(["grep", r"line\d+", "/regex.txt"])
        assert await prog_grep(ctx) == 0
        assert "line123" in output.text
        assert "line456" in output.text

    async def test_grep_invalid_regex(self, make_ctx, output):
        ctx = make_ctx(["grep", "[invalid", "/welcome.txt"])
        assert await prog_grep(ctx) == 1
        assert "invalid pattern" in output.error_text

    async def test_grep_missing_pattern(self, make_ctx, output):
        ctx = make_ctx(["grep"])
        assert await prog_grep(ctx) == 1
        assert "missing pattern" in output.error_text

    async def test_grep_file_not_found(self, make_ctx, output):
        ctx = make_ctx(["grep", "x", "/nonexistent"])
        assert await prog_grep(ctx) == 1

    async def test_grep_shows_line_numbers(self, make_ctx, output, test_container):
        app = test_container.app_service
        root_id = test_container.game_state.filesystem.root_id
        app.create_file(
            {
                "name": "numbered.txt",
                "parent_id": root_id,
                "content": "aaa\nbbb\nccc",
            }
        )
        ctx = make_ctx(["grep", "bbb", "/numbered.txt"])
        assert await prog_grep(ctx) == 0
        assert "2:" in output.text

    async def test_grep_default_cwd(self, make_ctx, output, test_container):
        """Grep with no path defaults to current directory."""
        ctx = make_ctx(["grep", "Welcome"])
        # Should search cwd (root), which contains welcome.txt
        assert await prog_grep(ctx) == 0


@pytest.mark.unit
class TestFind:
    async def test_find_by_name(self, make_ctx, output):
        ctx = make_ctx(["find", "/", "-name", "welcome.txt"])
        assert await prog_find(ctx) == 0
        assert "welcome.txt" in output.text

    async def test_find_with_glob(self, make_ctx, output):
        ctx = make_ctx(["find", "/", "-name", "*.txt"])
        assert await prog_find(ctx) == 0
        assert "welcome.txt" in output.text

    async def test_find_no_match(self, make_ctx, output):
        ctx = make_ctx(["find", "/", "-name", "nonexistent.xyz"])
        assert await prog_find(ctx) == 0
        assert output.text.strip() == ""

    async def test_find_directory(self, make_ctx, output):
        ctx = make_ctx(["find", "/", "-name", "Documents"])
        assert await prog_find(ctx) == 0
        assert "Documents" in output.text

    async def test_find_missing_name(self, make_ctx, output):
        ctx = make_ctx(["find", "/"])
        assert await prog_find(ctx) == 1
        assert "missing -name" in output.error_text

    async def test_find_default_path(self, make_ctx, output):
        """Find defaults to current directory."""
        ctx = make_ctx(["find", "-name", "*.txt"])
        assert await prog_find(ctx) == 0
        assert ".txt" in output.text

    async def test_find_path_not_found(self, make_ctx, output):
        ctx = make_ctx(["find", "/nonexistent", "-name", "*.txt"])
        assert await prog_find(ctx) == 1


@pytest.mark.unit
class TestWrite:
    async def test_write_new_file(self, make_ctx, output, test_container):
        ctx = make_ctx(["write", "/newfile.txt", "hello", "world"])
        assert await prog_write(ctx) == 0
        assert "Wrote" in output.text

        node = test_container.app_service.get_file(
            _find_file_id(test_container, "newfile.txt")
        )
        assert node.content == "hello world"

    async def test_write_overwrite(self, make_ctx, output, test_container):
        app = test_container.app_service
        root_id = test_container.game_state.filesystem.root_id
        app.create_file(
            {"name": "existing.txt", "parent_id": root_id, "content": "old"}
        )

        ctx = make_ctx(["write", "/existing.txt", "new", "content"])
        assert await prog_write(ctx) == 0

        node = app.get_file(_find_file_id(test_container, "existing.txt"))
        assert node.content == "new content"

    async def test_write_empty(self, make_ctx, output, test_container):
        ctx = make_ctx(["write", "/empty.txt"])
        assert await prog_write(ctx) == 0

        node = test_container.app_service.get_file(
            _find_file_id(test_container, "empty.txt")
        )
        assert node.content == ""

    async def test_write_directory_error(self, make_ctx, output):
        ctx = make_ctx(["write", "/Documents"])
        assert await prog_write(ctx) == 1
        assert "Is a directory" in output.error_text

    async def test_write_missing_operand(self, make_ctx, output):
        ctx = make_ctx(["write"])
        assert await prog_write(ctx) == 1
        assert "missing file" in output.error_text


def _find_file_id(container, name: str) -> str:
    """Helper to find a file by name in the root directory."""
    root_id = container.game_state.filesystem.root_id
    for node in container.app_service.list_directory(root_id):
        if node.name == name:
            return node.id
    raise ValueError(f"File {name} not found")
