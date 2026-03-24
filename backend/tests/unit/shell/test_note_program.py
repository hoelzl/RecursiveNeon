"""Tests for the note shell program."""

from __future__ import annotations

import pytest

from recursive_neon.shell.programs.notes import prog_note


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

    async def test_edit_no_flags(self, make_ctx, output, test_container):
        app = test_container.app_service
        app.create_note({"title": "Note", "content": "body"})

        ctx = make_ctx(["note", "edit", "1"])
        assert await prog_note(ctx) == 1
        assert "provide" in output.error_text

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
