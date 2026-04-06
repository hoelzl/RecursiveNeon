"""
Regression tests for TD-006 bug 2: editor save_callback closes over a
single shared ``file_id``, so multi-buffer editing (via C-x C-f or
similar) produces duplicate files or saves to the wrong node.

**Scenario that triggered the bug report** (2026-04-05): the user opened
one file, split the window, opened a second file via ``find-file``, and
saved both.  The second save either (a) created a duplicate node
because the ``file_id`` closure was still ``None`` (when the editor was
launched with no initial file) or (b) wrote the second buffer's content
into the first file's node (when the editor was launched with an
initial file that set ``file_id``).

**Root cause**: in ``shell/programs/edit.py``, the ``save_callback``
uses a single ``nonlocal file_id`` variable shared across every buffer
in the editor session.  The correct design is a **per-buffer** mapping
from buffer identity (or filepath) to file id, populated on open
(including via ``find-file``'s ``open_callback``) and consulted on save.

These tests are currently ``xfail(strict=True)`` — they document the
expected behaviour and turn green the moment the fix lands.

See ``docs/V2_HANDOVER.md`` (Phase 7, TD-006) and
``tests/unit/test_filesystem_name_uniqueness.py`` for the companion
filesystem-layer tests.
"""

from __future__ import annotations

import asyncio
from typing import Any

from recursive_neon.shell.output import CapturedOutput
from recursive_neon.shell.programs import ProgramContext
from recursive_neon.shell.programs.edit import _run_edit

# ═══════════════════════════════════════════════════════════════════════
# Test helpers
# ═══════════════════════════════════════════════════════════════════════


class _CapturingRunTui:
    """Mock ``run_tui`` that captures the view and returns immediately.

    Lets tests exercise the editor's callbacks without actually running
    the TUI event loop.
    """

    def __init__(self) -> None:
        self.view: Any = None

    async def __call__(self, view: Any) -> int:
        self.view = view
        return 0


def _make_ctx(
    test_container: Any, args: list[str], *, cwd_id: str | None = None
) -> tuple[ProgramContext, _CapturingRunTui]:
    root_id = test_container.game_state.filesystem.root_id
    run_tui = _CapturingRunTui()
    ctx = ProgramContext(
        args=args,
        stdout=CapturedOutput(),
        stderr=CapturedOutput(),
        env={"USER": "test", "HOME": "/", "HOSTNAME": "test-host"},
        services=test_container,
        cwd_id=cwd_id or root_id,
        run_tui=run_tui,
    )
    return ctx, run_tui


def _run(ctx: ProgramContext) -> int:
    return asyncio.run(_run_edit(ctx))


def _count_children_named(app_service: Any, parent_id: str, name: str) -> int:
    return sum(1 for c in app_service.list_directory(parent_id) if c.name == name)


# ═══════════════════════════════════════════════════════════════════════
# Single-save regression: find-file on an existing file, then save
# ═══════════════════════════════════════════════════════════════════════


class TestSaveDoesNotDuplicateExistingFile:
    def test_editor_launched_without_args_then_find_file_and_save(self, test_container):
        """Launch ``edit`` with no args, open an existing file via
        find-file, edit, save.  The save must **update** the existing
        file, not create a duplicate node with the same name.
        """
        app_service = test_container.app_service
        root_id = test_container.game_state.filesystem.root_id
        # Seed the filesystem with a file we'll later open via find-file
        target = app_service.create_file(
            {"name": "target.txt", "parent_id": root_id, "content": "original"}
        )

        ctx, run_tui = _make_ctx(test_container, ["edit"])
        assert _run(ctx) == 0
        view = run_tui.view
        assert view is not None

        # Simulate find-file: open_callback loads content, then the
        # editor creates a buffer with filepath set.  This is exactly
        # what ``default_commands.find_file`` does.
        open_cb = view.editor.open_callback
        assert open_cb is not None
        content = open_cb("/target.txt")
        view.editor.create_buffer(
            name="target.txt", text=content, filepath="/target.txt"
        )
        buf = view.editor.buffer  # current buffer is the new one
        # User edits the buffer
        buf.end_of_buffer()
        buf.insert_string(" edited")

        # User saves — this must UPDATE target.txt, not create a dup
        ok = view.editor.save_callback(buf)
        assert ok is True

        assert _count_children_named(app_service, root_id, "target.txt") == 1
        # And the existing node's content must reflect the edit
        updated = app_service.get_file(target.id)
        assert updated.content == "original edited"

    def test_editor_launched_with_file_then_find_file_different_file_and_save(
        self, test_container
    ):
        """Launch ``edit file1.txt``, open ``file2.txt`` via find-file,
        switch to it, edit, save.  The second save must update
        ``file2.txt``, not overwrite ``file1.txt`` via the stale
        ``file_id`` closure.
        """
        app_service = test_container.app_service
        root_id = test_container.game_state.filesystem.root_id
        file1 = app_service.create_file(
            {"name": "file1.txt", "parent_id": root_id, "content": "content1"}
        )
        file2 = app_service.create_file(
            {"name": "file2.txt", "parent_id": root_id, "content": "content2"}
        )

        ctx, run_tui = _make_ctx(test_container, ["edit", "/file1.txt"])
        assert _run(ctx) == 0
        view = run_tui.view
        assert view is not None

        # Simulate find-file on a different file
        open_cb = view.editor.open_callback
        assert open_cb is not None
        content = open_cb("/file2.txt")
        view.editor.create_buffer(name="file2.txt", text=content, filepath="/file2.txt")
        buf2 = view.editor.buffer
        assert buf2.text == "content2"
        # Edit buffer2
        buf2.end_of_buffer()
        buf2.insert_string(" edited")

        # Save buffer2 — must hit file2, not file1
        ok = view.editor.save_callback(buf2)
        assert ok is True

        # file1 should be unchanged
        assert app_service.get_file(file1.id).content == "content1"
        # file2 should be updated
        assert app_service.get_file(file2.id).content == "content2 edited"
        # No duplicates
        assert _count_children_named(app_service, root_id, "file1.txt") == 1
        assert _count_children_named(app_service, root_id, "file2.txt") == 1


# ═══════════════════════════════════════════════════════════════════════
# Multi-buffer save sequence: the exact user-reported scenario
# ═══════════════════════════════════════════════════════════════════════


class TestUserReportedScenario:
    def test_open_split_open_second_save_both(self, test_container):
        """Reproduces the user-reported scenario from the bug report:

        1. Open file1.txt via ``edit file1.txt``.
        2. (split would happen here — irrelevant to the save logic)
        3. Open file2.txt via find-file.
        4. Switch back to buffer1, edit, save.
        5. Switch to buffer2, edit, save.

        After step 5, the filesystem must have exactly one file1.txt
        and one file2.txt, each containing its own buffer's edits.
        """
        app_service = test_container.app_service
        root_id = test_container.game_state.filesystem.root_id
        file1 = app_service.create_file(
            {"name": "file1.txt", "parent_id": root_id, "content": "aaa"}
        )
        file2 = app_service.create_file(
            {"name": "file2.txt", "parent_id": root_id, "content": "bbb"}
        )

        ctx, run_tui = _make_ctx(test_container, ["edit", "/file1.txt"])
        assert _run(ctx) == 0
        view = run_tui.view
        editor = view.editor

        # Step 1 complete: editor has buffer1 for file1.txt
        buf1 = editor.buffer
        assert buf1.filepath == "/file1.txt"
        assert buf1.text == "aaa"

        # Step 3: find-file file2.txt
        content = editor.open_callback("/file2.txt")
        editor.create_buffer(name="file2.txt", text=content, filepath="/file2.txt")
        buf2 = editor.buffer
        assert buf2.text == "bbb"

        # Step 4: switch to buffer1, edit, save
        editor.switch_to_buffer("file1.txt")
        assert editor.buffer is buf1
        buf1.end_of_buffer()
        buf1.insert_string(" + edit1")
        assert editor.save_callback(buf1) is True

        # Step 5: switch to buffer2, edit, save
        editor.switch_to_buffer("file2.txt")
        assert editor.buffer is buf2
        buf2.end_of_buffer()
        buf2.insert_string(" + edit2")
        assert editor.save_callback(buf2) is True

        # Invariants after all saves:
        # 1. Exactly one file1.txt and one file2.txt in root.
        assert _count_children_named(app_service, root_id, "file1.txt") == 1
        assert _count_children_named(app_service, root_id, "file2.txt") == 1
        # 2. Each file has the correct content from its own buffer.
        assert app_service.get_file(file1.id).content == "aaa + edit1"
        assert app_service.get_file(file2.id).content == "bbb + edit2"


# ═══════════════════════════════════════════════════════════════════════
# Save-then-save to different buffer (write-file / create two new files)
# ═══════════════════════════════════════════════════════════════════════


class TestCreateTwoNewFilesInSession:
    def test_write_file_to_two_new_paths_creates_two_files(self, test_container):
        """Start with ``edit`` (no args), write two different new files
        via consecutive write-file operations on two different buffers.
        Both files must be created; neither should be collapsed into
        the other.
        """
        app_service = test_container.app_service
        root_id = test_container.game_state.filesystem.root_id

        ctx, run_tui = _make_ctx(test_container, ["edit"])
        assert _run(ctx) == 0
        view = run_tui.view
        editor = view.editor

        # Buffer 1 — the scratch buffer
        buf1 = editor.buffer
        buf1.insert_string("first content")
        buf1.filepath = "/new1.txt"
        buf1.name = "new1.txt"
        assert editor.save_callback(buf1) is True

        # Buffer 2 — a fresh buffer for a different new file
        editor.create_buffer(name="new2.txt", text="", filepath="/new2.txt")
        buf2 = editor.buffer
        buf2.insert_string("second content")
        assert editor.save_callback(buf2) is True

        # Both files must exist with the correct content
        assert _count_children_named(app_service, root_id, "new1.txt") == 1
        assert _count_children_named(app_service, root_id, "new2.txt") == 1
        children = {c.name: c for c in app_service.list_directory(root_id)}
        assert children["new1.txt"].content == "first content"
        assert children["new2.txt"].content == "second content"
