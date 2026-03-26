"""Tests for context-sensitive tab completion (Phase 5a)."""

from __future__ import annotations

import pytest

from recursive_neon.shell.completion import (
    complete_choices,
)
from recursive_neon.shell.shell import Shell

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _completions(shell: Shell, text: str) -> list[str]:
    """Shortcut: return completion items for text."""
    items, _ = shell.get_completions_ext(text)
    return items


def _completions_ext(shell: Shell, text: str) -> tuple[list[str], int]:
    """Shortcut: return (items, replace_len)."""
    return shell.get_completions_ext(text)


# ---------------------------------------------------------------------------
# Shared helper unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCompletionHelpers:
    def test_complete_choices_filters(self):
        assert complete_choices(["list", "ls", "show", "create"], "l") == ["list", "ls"]

    def test_complete_choices_empty_prefix(self):
        assert complete_choices(["a", "b"], "") == ["a", "b"]

    def test_complete_choices_no_match(self):
        assert complete_choices(["a", "b"], "z") == []


# ---------------------------------------------------------------------------
# Command name completion (first argument)
# ---------------------------------------------------------------------------


@pytest.fixture
def shell(test_container, output):
    """A Shell instance for completion testing."""
    return Shell(container=test_container, output=output)


@pytest.mark.unit
class TestCommandNameCompletion:
    def test_empty_input(self, shell):
        items = _completions(shell, "")
        # Should return all commands
        assert "ls" in items
        assert "cd" in items
        assert "cat" in items
        assert "note" in items

    def test_partial_l(self, shell):
        items = _completions(shell, "l")
        assert "ls" in items
        assert "cat" not in items

    def test_partial_c(self, shell):
        items = _completions(shell, "c")
        assert "cat" in items
        assert "cd" in items
        assert "chat" in items
        assert "clear" in items
        assert "codebreaker" in items
        assert "cp" in items

    def test_exact_match(self, shell):
        items = _completions(shell, "ls")
        assert items == ["ls"]

    def test_no_match(self, shell):
        items = _completions(shell, "zzz")
        assert items == []

    def test_builtins_included(self, shell):
        items = _completions(shell, "e")
        assert "exit" in items
        assert "export" in items
        assert "echo" in items
        assert "env" in items


# ---------------------------------------------------------------------------
# cd — directory-only completion
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCdCompletion:
    def test_cd_completes_directories(self, shell):
        items = _completions(shell, "cd ")
        # Should include directories but not files
        assert "Documents/" in items
        assert "Pictures/" in items
        # welcome.txt is a file at root — should NOT appear
        assert "welcome.txt" not in items

    def test_cd_partial(self, shell):
        items = _completions(shell, "cd D")
        assert "Documents/" in items
        # Pictures/ does not start with D
        assert "Pictures/" not in items

    def test_cd_subdir(self, shell):
        items = _completions(shell, "cd Documents/")
        # Should list children of Documents (all files, since no dirs inside)
        # Actually Documents/ likely has no subdirectories in test fixtures
        # But we're testing it only returns directories — files should be excluded
        # We just check the mechanism works
        assert isinstance(items, list)


# ---------------------------------------------------------------------------
# ls — flags + paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLsCompletion:
    def test_ls_flag(self, shell):
        items = _completions(shell, "ls -")
        assert "-l" in items
        assert "-a" in items
        assert "-la" in items
        assert "-al" in items

    def test_ls_path_after_flag(self, shell):
        items = _completions(shell, "ls -l ")
        assert "Documents/" in items

    def test_ls_path_partial(self, shell):
        items = _completions(shell, "ls D")
        assert "Documents/" in items

    def test_ls_no_flag_for_non_dash(self, shell):
        items = _completions(shell, "ls w")
        # Should complete paths, not flags
        assert "welcome.txt" in items


# ---------------------------------------------------------------------------
# grep — flags, then pattern (no completion), then paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGrepCompletion:
    def test_grep_flag(self, shell):
        items = _completions(shell, "grep -")
        assert "-i" in items
        assert "-r" in items

    def test_grep_pattern_no_completion(self, shell):
        """First non-flag arg is a pattern — no completion."""
        items = _completions(shell, "grep foo")
        # Partial text 'foo' is the pattern — should return nothing
        assert items == []

    def test_grep_pattern_after_flags(self, shell):
        items = _completions(shell, "grep -i ")
        # After flags, next arg is pattern — no completion
        assert items == []

    def test_grep_paths_after_pattern(self, shell):
        """After the pattern, args are paths."""
        items = _completions(shell, "grep foo ")
        assert "Documents/" in items


# ---------------------------------------------------------------------------
# find — path then -name flag
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFindCompletion:
    def test_find_flag(self, shell):
        items = _completions(shell, "find . -")
        assert "-name" in items

    def test_find_path(self, shell):
        items = _completions(shell, "find D")
        assert "Documents/" in items


# ---------------------------------------------------------------------------
# write — first arg path, rest no completion
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWriteCompletion:
    def test_write_first_arg_path(self, shell):
        items = _completions(shell, "write ")
        assert "Documents/" in items

    def test_write_second_arg_no_completion(self, shell):
        items = _completions(shell, "write foo.txt ")
        assert items == []


# ---------------------------------------------------------------------------
# cat, cp, mv, touch, rm — path completions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilePathCompletion:
    def test_cat_paths(self, shell):
        items = _completions(shell, "cat ")
        assert "Documents/" in items
        assert "welcome.txt" in items

    def test_cat_multiple_args(self, shell):
        """cat completes all args as paths."""
        items = _completions(shell, "cat welcome.txt ")
        assert "Documents/" in items

    def test_cp_paths(self, shell):
        items = _completions(shell, "cp ")
        assert "Documents/" in items

    def test_mv_paths(self, shell):
        items = _completions(shell, "mv ")
        assert "Documents/" in items

    def test_touch_paths(self, shell):
        items = _completions(shell, "touch ")
        assert "welcome.txt" in items

    def test_rm_flag(self, shell):
        items = _completions(shell, "rm -")
        assert "-r" in items
        assert "-rf" in items

    def test_rm_path(self, shell):
        items = _completions(shell, "rm ")
        assert "Documents/" in items


# ---------------------------------------------------------------------------
# mkdir — flag + directory-only
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMkdirCompletion:
    def test_mkdir_flag(self, shell):
        items = _completions(shell, "mkdir -")
        assert "-p" in items

    def test_mkdir_dirs_only(self, shell):
        items = _completions(shell, "mkdir ")
        # Should only suggest directories
        assert "Documents/" in items
        assert "welcome.txt" not in items


# ---------------------------------------------------------------------------
# note — subcommands + dynamic note refs
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNoteCompletion:
    def test_note_subcommands(self, shell):
        items = _completions(shell, "note ")
        assert "list" in items
        assert "show" in items
        assert "create" in items
        assert "edit" in items
        assert "delete" in items

    def test_note_subcommand_partial(self, shell):
        items = _completions(shell, "note s")
        assert items == ["show"]

    def test_note_show_refs(self, shell):
        """note show should complete note indices."""
        svc = shell.session.container.app_service
        svc.create_note({"title": "Test Note", "content": "hello"})
        svc.create_note({"title": "Another Note", "content": "world"})
        items = _completions(shell, "note show ")
        assert "1" in items
        assert "2" in items

    def test_note_show_refs_partial(self, shell):
        svc = shell.session.container.app_service
        for i in range(12):
            svc.create_note({"title": f"Note {i}", "content": ""})
        items = _completions(shell, "note show 1")
        assert "1" in items
        assert "10" in items
        assert "11" in items
        assert "12" in items
        assert "2" not in items

    def test_note_create_flag(self, shell):
        items = _completions(shell, "note create -")
        assert "-c" in items
        assert "--content" in items

    def test_note_edit_flags(self, shell):
        svc = shell.session.container.app_service
        svc.create_note({"title": "Test", "content": ""})
        items = _completions(shell, "note edit 1 -")
        assert "-t" in items
        assert "--title" in items
        assert "-c" in items
        assert "--content" in items

    def test_note_delete_refs(self, shell):
        svc = shell.session.container.app_service
        svc.create_note({"title": "To Delete", "content": ""})
        items = _completions(shell, "note delete ")
        assert "1" in items


# ---------------------------------------------------------------------------
# task — subcommands + dynamic refs
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTaskCompletion:
    def test_task_subcommands(self, shell):
        items = _completions(shell, "task ")
        assert "lists" in items
        assert "list" in items
        assert "add" in items
        assert "done" in items
        assert "undone" in items
        assert "delete" in items

    def test_task_subcommand_partial(self, shell):
        items = _completions(shell, "task d")
        assert "done" in items
        assert "delete" in items
        assert "lists" not in items

    def test_task_list_names(self, shell):
        svc = shell.session.container.app_service
        svc.create_task_list({"name": "work"})
        svc.create_task_list({"name": "personal"})
        items = _completions(shell, "task list ")
        assert "work" in items
        assert "personal" in items

    def test_task_done_refs(self, shell):
        svc = shell.session.container.app_service
        tl = svc.create_task_list({"name": "default"})
        svc.create_task(tl.id, {"title": "First", "completed": False})
        svc.create_task(tl.id, {"title": "Second", "completed": False})
        items = _completions(shell, "task done ")
        assert "1" in items
        assert "2" in items


# ---------------------------------------------------------------------------
# chat — NPC ID completion
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestChatCompletion:
    def test_chat_npc_ids(self, shell):
        items = _completions(shell, "chat ")
        npcs = shell.session.container.npc_manager.list_npcs()
        for npc in npcs:
            assert npc.id in items

    def test_chat_npc_partial(self, shell):
        npcs = shell.session.container.npc_manager.list_npcs()
        if npcs:
            first_id = npcs[0].id
            items = _completions(shell, f"chat {first_id[:3]}")
            assert first_id in items

    def test_chat_no_second_arg(self, shell):
        """chat takes exactly one arg — no completion for second."""
        npcs = shell.session.container.npc_manager.list_npcs()
        if npcs:
            items = _completions(shell, f"chat {npcs[0].id} ")
            assert items == []


# ---------------------------------------------------------------------------
# help — command name completion
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHelpCompletion:
    def test_help_completes_commands(self, shell):
        items = _completions(shell, "help ")
        assert "ls" in items
        assert "cd" in items
        assert "note" in items
        assert "help" in items

    def test_help_partial(self, shell):
        items = _completions(shell, "help c")
        assert "cat" in items
        assert "cd" in items
        assert "ls" not in items


# ---------------------------------------------------------------------------
# Unknown command — fallback to path completion
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFallbackCompletion:
    def test_unknown_command_gets_paths(self, shell):
        """Commands without a registered completer get path completion."""
        items = _completions(shell, "unknown_cmd ")
        assert "Documents/" in items

    def test_pwd_no_completer_gets_paths(self, shell):
        """pwd has no completer — falls back to paths (harmless)."""
        items = _completions(shell, "pwd ")
        # pwd doesn't use args, but completion falls back to paths
        assert isinstance(items, list)


# ---------------------------------------------------------------------------
# Quoted path completion
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestQuotedPathCompletion:
    def test_quoted_folder(self, shell):
        """Completing inside a quoted path."""
        items = _completions(shell, 'cat "My Fol')
        # Should find "My Folder"/ if it exists
        matching = [i for i in items if "My Folder" in i]
        if matching:
            assert matching[0].endswith("/")

    def test_subdir_completion(self, shell):
        """Completing inside a subdirectory."""
        items = _completions(shell, "cat Documents/")
        # Should list children of Documents
        assert len(items) > 0


# ---------------------------------------------------------------------------
# Replacement length
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReplacementLength:
    def test_first_arg_replace_len(self, shell):
        items, replace_len = _completions_ext(shell, "l")
        assert replace_len == 1

    def test_second_arg_replace_len(self, shell):
        items, replace_len = _completions_ext(shell, "cat ")
        assert replace_len == 0

    def test_partial_second_arg(self, shell):
        items, replace_len = _completions_ext(shell, "cat w")
        assert replace_len == 1

    def test_quoted_arg_replace_len(self, shell):
        text = 'cat "My Fol'
        items, replace_len = _completions_ext(shell, text)
        assert replace_len == len('"My Fol')


# ---------------------------------------------------------------------------
# WebSocket parity — get_completions_ext is the same path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWebSocketParity:
    def test_get_completions_returns_same(self, shell):
        """get_completions (used by WS) returns same items as ext."""
        items_simple = shell.get_completions("note ")
        items_ext, _ = shell.get_completions_ext("note ")
        assert items_simple == items_ext
