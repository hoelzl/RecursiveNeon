"""Tests for tokenize_ext quoting metadata and shell-level glob expansion."""

from __future__ import annotations

import pytest

from recursive_neon.shell.glob import expand_globs, has_glob_chars
from recursive_neon.shell.output import CapturedOutput
from recursive_neon.shell.parser import Token, tokenize_ext
from recursive_neon.shell.shell import Shell

# ---------------------------------------------------------------------------
# tokenize_ext — quoting metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTokenizeExt:
    def test_unquoted_tokens(self):
        tokens = tokenize_ext("ls -l foo")
        assert tokens == [
            Token("ls", False),
            Token("-l", False),
            Token("foo", False),
        ]

    def test_double_quoted(self):
        tokens = tokenize_ext('cat "my file.txt"')
        assert tokens[0] == Token("cat", False)
        assert tokens[1] == Token("my file.txt", True)

    def test_single_quoted(self):
        tokens = tokenize_ext("cat 'my file.txt'")
        assert tokens[1] == Token("my file.txt", True)

    def test_backslash_escape(self):
        tokens = tokenize_ext("cat my\\ file.txt")
        assert tokens[1] == Token("my file.txt", True)

    def test_mixed_quoted_unquoted(self):
        tokens = tokenize_ext('grep "*.txt" *.md')
        assert tokens[1].quoted is True  # "*.txt"
        assert tokens[2].quoted is False  # *.md

    def test_partial_quote_marks_quoted(self):
        """A token with any quoted part is marked quoted."""
        tokens = tokenize_ext('cat "My Folder"/readme.txt')
        assert tokens[1].quoted is True
        assert tokens[1].value == "My Folder/readme.txt"

    def test_empty_quotes(self):
        tokens = tokenize_ext('echo ""')
        assert tokens[1] == Token("", True)

    def test_empty_input(self):
        assert tokenize_ext("") == []

    def test_values_match_tokenize(self):
        """tokenize_ext values must match tokenize output."""
        from recursive_neon.shell.parser import tokenize

        line = 'cat "My Folder"/readme.txt *.txt -l'
        assert [t.value for t in tokenize_ext(line)] == tokenize(line)


# ---------------------------------------------------------------------------
# has_glob_chars
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHasGlobChars:
    def test_star(self):
        assert has_glob_chars("*.txt") is True

    def test_question_mark(self):
        assert has_glob_chars("?.txt") is True

    def test_bracket(self):
        assert has_glob_chars("[abc].txt") is True

    def test_no_glob(self):
        assert has_glob_chars("readme.txt") is False

    def test_empty(self):
        assert has_glob_chars("") is False


# ---------------------------------------------------------------------------
# expand_globs — unit tests with mock tokens
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExpandGlobs:
    def test_no_globs(self, test_container):
        """Tokens without glob chars pass through unchanged."""
        tokens = [Token("cat", False), Token("readme.txt", False)]
        result = expand_globs(
            tokens,
            test_container.game_state.filesystem.root_id,
            test_container.app_service,
        )
        assert result == ["cat", "readme.txt"]

    def test_quoted_glob_not_expanded(self, test_container):
        """Quoted tokens with glob chars pass through as literals."""
        tokens = [Token("cat", False), Token("*.txt", True)]
        result = expand_globs(
            tokens,
            test_container.game_state.filesystem.root_id,
            test_container.app_service,
        )
        assert result == ["cat", "*.txt"]

    def test_command_name_not_expanded(self, test_container):
        """First token (command name) is never expanded."""
        tokens = [Token("*", False), Token("foo", False)]
        result = expand_globs(
            tokens,
            test_container.game_state.filesystem.root_id,
            test_container.app_service,
        )
        assert result[0] == "*"

    def test_star_txt_in_root(self, test_container):
        """*.txt matches .txt files in root."""
        root_id = test_container.game_state.filesystem.root_id
        tokens = [Token("cat", False), Token("*.txt", False)]
        result = expand_globs(tokens, root_id, test_container.app_service)
        # welcome.txt is a .txt file in root (from initial_fs)
        assert "welcome.txt" in result
        # Directories should NOT be matched
        assert "Documents/" not in result or not any(
            r.endswith(".txt") and "/" in r for r in result
        )

    def test_no_match_passthrough(self, test_container):
        """Unmatched glob passes through as literal (POSIX behavior)."""
        root_id = test_container.game_state.filesystem.root_id
        tokens = [Token("cat", False), Token("*.xyz", False)]
        result = expand_globs(tokens, root_id, test_container.app_service)
        assert result == ["cat", "*.xyz"]

    def test_question_mark(self, test_container):
        """? matches a single character."""
        root_id = test_container.game_state.filesystem.root_id
        # Create files to match
        test_container.app_service.create_file(
            {"name": "a.md", "parent_id": root_id, "content": ""}
        )
        test_container.app_service.create_file(
            {"name": "b.md", "parent_id": root_id, "content": ""}
        )
        tokens = [Token("cat", False), Token("?.md", False)]
        result = expand_globs(tokens, root_id, test_container.app_service)
        assert "a.md" in result
        assert "b.md" in result

    def test_bracket_pattern(self, test_container):
        """[abc].md matches a.md, b.md, etc."""
        root_id = test_container.game_state.filesystem.root_id
        test_container.app_service.create_file(
            {"name": "x.md", "parent_id": root_id, "content": ""}
        )
        test_container.app_service.create_file(
            {"name": "y.md", "parent_id": root_id, "content": ""}
        )
        tokens = [Token("cat", False), Token("[xy].md", False)]
        result = expand_globs(tokens, root_id, test_container.app_service)
        assert "x.md" in result
        assert "y.md" in result

    def test_subdir_glob(self, test_container):
        """Documents/*.txt matches files in Documents/."""
        root_id = test_container.game_state.filesystem.root_id
        tokens = [Token("cat", False), Token("Documents/*.txt", False)]
        result = expand_globs(tokens, root_id, test_container.app_service)
        # initial_fs has Documents/readme.txt, Documents/sample.txt, etc.
        txt_files = [
            r for r in result if r.startswith("Documents/") and r.endswith(".txt")
        ]
        assert len(txt_files) >= 1

    def test_absolute_path_glob(self, test_container):
        """/Documents/*.txt with absolute path."""
        root_id = test_container.game_state.filesystem.root_id
        tokens = [Token("cat", False), Token("/Documents/*.txt", False)]
        result = expand_globs(tokens, root_id, test_container.app_service)
        txt_files = [r for r in result if r.startswith("/Documents/")]
        assert len(txt_files) >= 1

    def test_glob_results_sorted(self, test_container):
        """Expanded results should be sorted alphabetically."""
        root_id = test_container.game_state.filesystem.root_id
        test_container.app_service.create_file(
            {"name": "z.md", "parent_id": root_id, "content": ""}
        )
        test_container.app_service.create_file(
            {"name": "a.md", "parent_id": root_id, "content": ""}
        )
        tokens = [Token("cat", False), Token("*.md", False)]
        result = expand_globs(tokens, root_id, test_container.app_service)
        md_files = [r for r in result if r != "cat"]
        assert md_files == sorted(md_files)

    def test_mixed_quoted_and_glob(self, test_container):
        """Mix of quoted (literal) and unquoted (expanded) tokens."""
        root_id = test_container.game_state.filesystem.root_id
        tokens = [
            Token("cat", False),
            Token("*.txt", True),  # quoted — literal
            Token("*.txt", False),  # unquoted — expand
        ]
        result = expand_globs(tokens, root_id, test_container.app_service)
        # First *.txt should stay literal
        assert result[1] == "*.txt"
        # Second *.txt should expand (if there are .txt files)
        # At minimum, welcome.txt exists
        assert len(result) >= 3

    def test_empty_tokens(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        assert expand_globs([], root_id, test_container.app_service) == []

    def test_directory_match_has_trailing_slash(self, test_container):
        """Directories matched by glob get a trailing /."""
        root_id = test_container.game_state.filesystem.root_id
        tokens = [Token("ls", False), Token("D*", False)]
        result = expand_globs(tokens, root_id, test_container.app_service)
        docs = [r for r in result if r.startswith("D")]
        for d in docs:
            if "Documents" in d:
                assert d.endswith("/")


# ---------------------------------------------------------------------------
# Recursive globs (**) — Phase 7b-1
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRecursiveGlobs:
    """Tests for ** recursive glob expansion."""

    @pytest.fixture(autouse=True)
    def _setup_deep_tree(self, test_container):
        """Create a deep directory tree for recursive glob tests.

        Structure (in addition to initial_fs):
            /deep/
            /deep/a.txt
            /deep/sub/
            /deep/sub/b.txt
            /deep/sub/inner/
            /deep/sub/inner/c.txt
            /deep/sub/inner/notes.md
        """
        self.svc = test_container.app_service
        self.root_id = test_container.game_state.filesystem.root_id

        deep = self.svc.create_directory({"name": "deep", "parent_id": self.root_id})
        self.svc.create_file({"name": "a.txt", "parent_id": deep.id, "content": "a"})
        sub = self.svc.create_directory({"name": "sub", "parent_id": deep.id})
        self.svc.create_file({"name": "b.txt", "parent_id": sub.id, "content": "b"})
        inner = self.svc.create_directory({"name": "inner", "parent_id": sub.id})
        self.svc.create_file({"name": "c.txt", "parent_id": inner.id, "content": "c"})
        self.svc.create_file(
            {"name": "notes.md", "parent_id": inner.id, "content": "notes"}
        )

    def _expand(self, pattern: str) -> list[str]:
        tokens = [Token("cmd", False), Token(pattern, False)]
        result = expand_globs(tokens, self.root_id, self.svc)
        return result[1:]  # skip "cmd"

    def test_double_star_slash_txt(self):
        """**/*.txt matches .txt files at any depth under cwd."""
        matches = self._expand("**/*.txt")
        # Should find files in root, deep/, deep/sub/, deep/sub/inner/
        assert "deep/a.txt" in matches
        assert "deep/sub/b.txt" in matches
        assert "deep/sub/inner/c.txt" in matches
        # Also welcome.txt and Documents/*.txt from initial_fs
        assert "welcome.txt" in matches

    def test_double_star_slash_md(self):
        """**/*.md matches .md files at any depth."""
        matches = self._expand("**/*.md")
        assert "deep/sub/inner/notes.md" in matches

    def test_dir_double_star(self):
        """deep/** matches everything under deep/ recursively."""
        matches = self._expand("deep/**")
        assert "deep/a.txt" in matches
        assert "deep/sub/" in matches
        assert "deep/sub/b.txt" in matches
        assert "deep/sub/inner/" in matches
        assert "deep/sub/inner/c.txt" in matches
        assert "deep/sub/inner/notes.md" in matches

    def test_double_star_specific_name(self):
        """**/notes.md matches notes.md at any depth."""
        matches = self._expand("**/notes.md")
        assert "deep/sub/inner/notes.md" in matches

    def test_dir_between_literals(self):
        """deep/**/c.txt matches c.txt at any depth under deep/."""
        matches = self._expand("deep/**/c.txt")
        assert "deep/sub/inner/c.txt" in matches

    def test_double_star_at_root(self):
        """** alone matches everything under cwd."""
        matches = self._expand("**")
        # Should include files and dirs recursively
        assert "deep/" in matches
        assert "deep/a.txt" in matches
        assert "deep/sub/inner/notes.md" in matches
        assert "welcome.txt" in matches

    def test_double_star_combined_with_question(self):
        """**/?.*  matches single-char filenames at any depth."""
        matches = self._expand("**/?.*")
        assert "deep/a.txt" in matches
        assert "deep/sub/b.txt" in matches
        assert "deep/sub/inner/c.txt" in matches

    def test_double_star_combined_with_bracket(self):
        """**/[ab].txt matches a.txt and b.txt at any depth."""
        matches = self._expand("**/[ab].txt")
        assert "deep/a.txt" in matches
        assert "deep/sub/b.txt" in matches
        assert "deep/sub/inner/c.txt" not in matches

    def test_no_match_passthrough(self):
        """Unmatched ** glob passes through as literal."""
        tokens = [Token("cat", False), Token("**/nonexistent.xyz", False)]
        result = expand_globs(tokens, self.root_id, self.svc)
        assert result == ["cat", "**/nonexistent.xyz"]

    def test_quoted_double_star_not_expanded(self):
        """Quoted ** is not expanded."""
        tokens = [Token("cat", False), Token("**/*.txt", True)]
        result = expand_globs(tokens, self.root_id, self.svc)
        assert result == ["cat", "**/*.txt"]

    def test_absolute_double_star(self):
        """/deep/**/*.txt with absolute path."""
        matches = self._expand("/deep/**/*.txt")
        assert "/deep/a.txt" in matches
        assert "/deep/sub/b.txt" in matches
        assert "/deep/sub/inner/c.txt" in matches

    def test_results_sorted(self):
        """Recursive glob results are sorted alphabetically."""
        matches = self._expand("**/*.txt")
        assert matches == sorted(matches)


# ---------------------------------------------------------------------------
# Integration with Shell.execute_line
# ---------------------------------------------------------------------------


@pytest.fixture
def shell(test_container, output):
    return Shell(container=test_container, output=output)


@pytest.fixture
def output():
    return CapturedOutput()


@pytest.mark.unit
class TestGlobIntegration:
    @pytest.mark.asyncio
    async def test_ls_star(self, shell, output):
        """ls * should list all items in cwd."""
        exit_code = await shell.execute_line("ls *")
        # Should succeed without errors
        assert exit_code == 0
        text = output.text
        # welcome.txt is in root
        assert "welcome" in text.lower() or len(text) > 0

    @pytest.mark.asyncio
    async def test_cat_star_txt(self, shell, output):
        """cat *.txt should concatenate all .txt files in cwd."""
        exit_code = await shell.execute_line("cat *.txt")
        # welcome.txt exists and has content
        assert exit_code == 0
        assert len(output.text) > 0

    @pytest.mark.asyncio
    async def test_quoted_glob_not_expanded(self, shell, output):
        """cat "*.txt" should try to open a file literally named *.txt."""
        exit_code = await shell.execute_line('cat "*.txt"')
        # Should fail because no file named "*.txt" exists
        assert exit_code != 0
        assert "*.txt" in output.error_text

    @pytest.mark.asyncio
    async def test_find_name_quoted(self, shell, output):
        """find . -name '*.txt' should pass *.txt literally to find."""
        exit_code = await shell.execute_line("find . -name '*.txt'")
        assert exit_code == 0
        assert ".txt" in output.text

    @pytest.mark.asyncio
    async def test_no_match_passthrough(self, shell, output):
        """Unmatched glob passes to the command as a literal string."""
        exit_code = await shell.execute_line("cat *.nonexistent")
        # cat should report file not found for the literal "*.nonexistent"
        assert exit_code != 0

    @pytest.mark.asyncio
    async def test_echo_glob_expands(self, shell, output):
        """echo *.txt should print the expanded filenames."""
        exit_code = await shell.execute_line("echo *.txt")
        assert exit_code == 0
        # Should contain actual filenames, not "*.txt" (unless no match)
        assert "welcome.txt" in output.text

    @pytest.mark.asyncio
    async def test_echo_recursive_glob(self, shell, output):
        """echo **/*.txt should expand recursively."""
        # Create a nested file so there's something to match
        svc = shell.session.container.app_service
        root_id = shell.session.container.game_state.filesystem.root_id
        sub = svc.create_directory({"name": "rsub", "parent_id": root_id})
        svc.create_file({"name": "deep.txt", "parent_id": sub.id, "content": ""})

        exit_code = await shell.execute_line("echo **/*.txt")
        assert exit_code == 0
        assert "rsub/deep.txt" in output.text
        assert "welcome.txt" in output.text
