"""Tests for the note shell program."""

from __future__ import annotations

import pytest

from recursive_neon.shell.programs.notes import (
    _format_note_text,
    _parse_note_text,
    prog_note,
)


@pytest.mark.unit
class TestNoteList:
    async def test_list_empty(self, make_ctx, output):
        ctx = make_ctx(["note", "list"])
        assert await prog_note(ctx) == 0
        assert "No notes" in output.text

    async def test_list_shows_notes(self, make_ctx, output, test_container):
        app = test_container.app_service
        app.create_note({"title": "First Note", "content": "Hello world"})
        app.create_note({"title": "Second Note", "content": "Another one"})

        ctx = make_ctx(["note", "list"])
        assert await prog_note(ctx) == 0
        assert "First Note" in output.text
        assert "Second Note" in output.text
        assert "[1]" in output.text
        assert "[2]" in output.text


@pytest.mark.unit
class TestNoteShow:
    async def test_show_by_index(self, make_ctx, output, test_container):
        app = test_container.app_service
        app.create_note({"title": "My Note", "content": "Full content here"})

        ctx = make_ctx(["note", "show", "1"])
        assert await prog_note(ctx) == 0
        assert "My Note" in output.text
        assert "Full content here" in output.text

    async def test_show_by_uuid_prefix(self, make_ctx, output, test_container):
        app = test_container.app_service
        note = app.create_note({"title": "UUID Note", "content": "body"})

        ctx = make_ctx(["note", "show", note.id[:8]])
        assert await prog_note(ctx) == 0
        assert "UUID Note" in output.text

    async def test_show_not_found(self, make_ctx, output):
        ctx = make_ctx(["note", "show", "99"])
        assert await prog_note(ctx) == 1
        assert "not found" in output.error_text

    async def test_show_missing_ref(self, make_ctx, output):
        ctx = make_ctx(["note", "show"])
        assert await prog_note(ctx) == 1
        assert "missing" in output.error_text


@pytest.mark.unit
class TestNoteCreate:
    async def test_create_simple(self, make_ctx, output, test_container):
        ctx = make_ctx(["note", "create", "My", "New", "Note"])
        assert await prog_note(ctx) == 0
        assert "My New Note" in output.text

        notes = test_container.app_service.get_notes()
        assert len(notes) == 1
        assert notes[0].title == "My New Note"

    async def test_create_with_content(self, make_ctx, output, test_container):
        ctx = make_ctx(["note", "create", "Title", "-c", "Some content"])
        assert await prog_note(ctx) == 0

        notes = test_container.app_service.get_notes()
        assert notes[0].content == "Some content"

    async def test_create_missing_title(self, make_ctx, output):
        ctx = make_ctx(["note", "create"])
        assert await prog_note(ctx) == 1
        assert "missing title" in output.error_text


@pytest.mark.unit
class TestNoteEdit:
    async def test_edit_title(self, make_ctx, output, test_container):
        app = test_container.app_service
        app.create_note({"title": "Old Title", "content": "body"})

        ctx = make_ctx(["note", "edit", "1", "--title", "New Title"])
        assert await prog_note(ctx) == 0
        assert "New Title" in output.text
        assert app.get_notes()[0].title == "New Title"

    async def test_edit_content(self, make_ctx, output, test_container):
        app = test_container.app_service
        app.create_note({"title": "Note", "content": "old"})

        ctx = make_ctx(["note", "edit", "1", "-c", "new content"])
        assert await prog_note(ctx) == 0
        assert app.get_notes()[0].content == "new content"

    async def test_edit_no_flags_no_tui(self, make_ctx, output, test_container):
        """Without TUI support, note edit <ref> with no flags shows an error."""
        app = test_container.app_service
        app.create_note({"title": "Note", "content": "body"})

        ctx = make_ctx(["note", "edit", "1"])
        assert await prog_note(ctx) == 1
        assert "TUI" in output.error_text

    async def test_edit_not_found(self, make_ctx, output):
        ctx = make_ctx(["note", "edit", "99", "--title", "X"])
        assert await prog_note(ctx) == 1
        assert "not found" in output.error_text

    async def test_edit_unknown_flag(self, make_ctx, output, test_container):
        test_container.app_service.create_note({"title": "Note", "content": "body"})
        ctx = make_ctx(["note", "edit", "1", "--tytle", "New"])
        assert await prog_note(ctx) == 1
        assert "unknown option" in output.error_text


@pytest.mark.unit
class TestNoteDelete:
    async def test_delete(self, make_ctx, output, test_container):
        app = test_container.app_service
        app.create_note({"title": "Delete Me", "content": ""})

        ctx = make_ctx(["note", "delete", "1"])
        assert await prog_note(ctx) == 0
        assert "Delete Me" in output.text
        assert len(app.get_notes()) == 0

    async def test_delete_not_found(self, make_ctx, output):
        ctx = make_ctx(["note", "delete", "99"])
        assert await prog_note(ctx) == 1
        assert "not found" in output.error_text


@pytest.mark.unit
class TestNoteSubcommandDispatch:
    async def test_missing_subcommand(self, make_ctx, output):
        ctx = make_ctx(["note"])
        assert await prog_note(ctx) == 1
        assert "missing subcommand" in output.error_text

    async def test_unknown_subcommand(self, make_ctx, output):
        ctx = make_ctx(["note", "bogus"])
        assert await prog_note(ctx) == 1
        assert "unknown subcommand" in output.error_text

    async def test_ls_alias(self, make_ctx, output):
        ctx = make_ctx(["note", "ls"])
        assert await prog_note(ctx) == 0
        assert "No notes" in output.text

    async def test_rm_alias(self, make_ctx, output, test_container):
        test_container.app_service.create_note({"title": "X", "content": ""})
        ctx = make_ctx(["note", "rm", "1"])
        assert await prog_note(ctx) == 0
        assert len(test_container.app_service.get_notes()) == 0


# ---------------------------------------------------------------------------
# Note ↔ editor text format
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNoteFormat:
    def test_format_note_text(self):
        assert _format_note_text("Title", "content") == "# Title\n\ncontent"

    def test_format_note_text_empty_content(self):
        assert _format_note_text("Title", "") == "# Title\n\n"

    def test_parse_standard(self):
        title, content = _parse_note_text("# My Title\n\nSome content here")
        assert title == "My Title"
        assert content == "Some content here"

    def test_parse_no_hash_prefix(self):
        title, content = _parse_note_text("Plain Title\n\nContent")
        assert title == "Plain Title"
        assert content == "Content"

    def test_parse_empty(self):
        assert _parse_note_text("") == ("", "")

    def test_parse_title_only(self):
        title, content = _parse_note_text("# Just Title")
        assert title == "Just Title"
        assert content == ""

    def test_parse_multiline_content(self):
        text = "# Title\n\nLine 1\nLine 2\nLine 3"
        title, content = _parse_note_text(text)
        assert title == "Title"
        assert content == "Line 1\nLine 2\nLine 3"

    def test_parse_no_blank_separator(self):
        """Content immediately after title line (no blank line)."""
        title, content = _parse_note_text("# Title\nContent")
        assert title == "Title"
        assert content == "Content"

    def test_roundtrip(self):
        original_title = "My Note"
        original_content = "Line 1\nLine 2"
        text = _format_note_text(original_title, original_content)
        title, content = _parse_note_text(text)
        assert title == original_title
        assert content == original_content


# ---------------------------------------------------------------------------
# Editor integration — note edit
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNoteEditInEditor:
    async def test_opens_editor_with_note_content(
        self, make_ctx, output, test_container
    ):
        app = test_container.app_service
        app.create_note({"title": "My Note", "content": "Hello world"})

        captured = {}

        async def mock_run_tui(view):
            captured["text"] = view.editor.buffer.text
            captured["name"] = view.editor.buffer.name
            return 0

        ctx = make_ctx(["note", "edit", "1"])
        ctx.run_tui = mock_run_tui
        assert await prog_note(ctx) == 0
        assert captured["text"] == "# My Note\n\nHello world"
        assert captured["name"] == "note:My Note"

    async def test_save_updates_note(self, make_ctx, output, test_container):
        app = test_container.app_service
        app.create_note({"title": "Old Title", "content": "old content"})

        async def mock_run_tui(view):
            buf = view.editor.buffer
            buf.lines = ["# New Title", "", "new content"]
            buf.point.move_to(0, 0)
            assert view.editor.save_callback(buf) is True
            return 0

        ctx = make_ctx(["note", "edit", "1"])
        ctx.run_tui = mock_run_tui
        assert await prog_note(ctx) == 0

        note = app.get_notes()[0]
        assert note.title == "New Title"
        assert note.content == "new content"
        assert "Updated note" in output.text

    async def test_save_rejects_empty_title(self, make_ctx, output, test_container):
        app = test_container.app_service
        app.create_note({"title": "Note", "content": "body"})

        async def mock_run_tui(view):
            buf = view.editor.buffer
            buf.lines = ["#  ", "", "content only"]
            assert view.editor.save_callback(buf) is False
            return 0

        ctx = make_ctx(["note", "edit", "1"])
        ctx.run_tui = mock_run_tui
        await prog_note(ctx)

        # Note should be unchanged
        assert app.get_notes()[0].title == "Note"

    async def test_quit_without_saving(self, make_ctx, output, test_container):
        app = test_container.app_service
        app.create_note({"title": "Note", "content": "body"})

        async def mock_run_tui(view):
            return 0  # quit without calling save_callback

        ctx = make_ctx(["note", "edit", "1"])
        ctx.run_tui = mock_run_tui
        assert await prog_note(ctx) == 0

        note = app.get_notes()[0]
        assert note.title == "Note"
        assert note.content == "body"


# ---------------------------------------------------------------------------
# Editor integration — note create
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNoteCreateInEditor:
    async def test_opens_editor_with_title(self, make_ctx, output, test_container):
        captured = {}

        async def mock_run_tui(view):
            captured["text"] = view.editor.buffer.text
            captured["name"] = view.editor.buffer.name
            return 0

        ctx = make_ctx(["note", "create", "My", "New", "Note"])
        ctx.run_tui = mock_run_tui
        assert await prog_note(ctx) == 0
        assert captured["text"] == "# My New Note\n\n"
        assert captured["name"] == "note:My New Note"

    async def test_save_creates_note(self, make_ctx, output, test_container):
        app = test_container.app_service

        async def mock_run_tui(view):
            buf = view.editor.buffer
            buf.lines = ["# My Note", "", "Some content"]
            buf.point.move_to(0, 0)
            assert view.editor.save_callback(buf) is True
            return 0

        ctx = make_ctx(["note", "create", "My", "Note"])
        ctx.run_tui = mock_run_tui
        assert await prog_note(ctx) == 0

        notes = app.get_notes()
        assert len(notes) == 1
        assert notes[0].title == "My Note"
        assert notes[0].content == "Some content"
        assert "Created note" in output.text

    async def test_save_twice_updates_instead_of_duplicating(
        self, make_ctx, output, test_container
    ):
        app = test_container.app_service

        async def mock_run_tui(view):
            buf = view.editor.buffer
            buf.lines = ["# Draft", "", "first version"]
            view.editor.save_callback(buf)
            buf.lines = ["# Draft", "", "second version"]
            view.editor.save_callback(buf)
            return 0

        ctx = make_ctx(["note", "create", "Draft"])
        ctx.run_tui = mock_run_tui
        assert await prog_note(ctx) == 0

        notes = app.get_notes()
        assert len(notes) == 1
        assert notes[0].content == "second version"

    async def test_quit_without_saving_creates_nothing(
        self, make_ctx, output, test_container
    ):
        app = test_container.app_service

        async def mock_run_tui(view):
            return 0

        ctx = make_ctx(["note", "create", "Abandoned"])
        ctx.run_tui = mock_run_tui
        assert await prog_note(ctx) == 0
        assert len(app.get_notes()) == 0
        assert "Created note" not in output.text

    async def test_create_with_c_flag_skips_editor(
        self, make_ctx, output, test_container
    ):
        """The -c flag still creates immediately without opening the editor."""
        app = test_container.app_service
        tui_called = False

        async def mock_run_tui(view):
            nonlocal tui_called
            tui_called = True
            return 0

        ctx = make_ctx(["note", "create", "Title", "-c", "inline content"])
        ctx.run_tui = mock_run_tui
        assert await prog_note(ctx) == 0

        assert not tui_called
        notes = app.get_notes()
        assert len(notes) == 1
        assert notes[0].content == "inline content"

    async def test_create_no_tui_falls_back_to_empty(
        self, make_ctx, output, test_container
    ):
        """Without TUI, note create <title> (no -c) creates with empty content."""
        app = test_container.app_service

        ctx = make_ctx(["note", "create", "Fallback", "Note"])
        # run_tui is None by default
        assert await prog_note(ctx) == 0

        notes = app.get_notes()
        assert len(notes) == 1
        assert notes[0].title == "Fallback Note"
        assert notes[0].content == ""
