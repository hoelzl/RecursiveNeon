"""Tests for the task shell program."""

from __future__ import annotations

import pytest

from recursive_neon.shell.programs.tasks import prog_task


@pytest.mark.unit
class TestTaskLists:
    async def test_lists_empty(self, make_ctx, output):
        ctx = make_ctx(["task", "lists"])
        assert await prog_task(ctx) == 0
        assert "No task lists" in output.text

    async def test_lists_shows_lists(self, make_ctx, output, test_container):
        app = test_container.app_service
        tl = app.create_task_list({"name": "Work"})
        app.create_task(tl.id, {"title": "Do stuff", "completed": False})
        app.create_task(tl.id, {"title": "Done stuff", "completed": True})

        ctx = make_ctx(["task", "lists"])
        assert await prog_task(ctx) == 0
        assert "Work" in output.text
        assert "(1/2)" in output.text


@pytest.mark.unit
class TestTaskList:
    async def test_list_default(self, make_ctx, output, test_container):
        app = test_container.app_service
        tl = app.create_task_list({"name": "default"})
        app.create_task(tl.id, {"title": "Task A", "completed": False})
        app.create_task(tl.id, {"title": "Task B", "completed": True})

        ctx = make_ctx(["task", "list"])
        assert await prog_task(ctx) == 0
        assert "Task A" in output.text
        assert "Task B" in output.text
        assert "1." in output.text
        assert "2." in output.text

    async def test_list_by_name(self, make_ctx, output, test_container):
        app = test_container.app_service
        tl = app.create_task_list({"name": "Work"})
        app.create_task(tl.id, {"title": "Code review", "completed": False})

        ctx = make_ctx(["task", "list", "Work"])
        assert await prog_task(ctx) == 0
        assert "Code review" in output.text

    async def test_list_not_found(self, make_ctx, output):
        ctx = make_ctx(["task", "list", "nonexistent"])
        assert await prog_task(ctx) == 1
        assert "not found" in output.error_text

    async def test_list_no_tasks(self, make_ctx, output, test_container):
        test_container.app_service.create_task_list({"name": "Empty"})
        ctx = make_ctx(["task", "list", "Empty"])
        assert await prog_task(ctx) == 0
        assert "no tasks" in output.text

    async def test_list_ambiguous(self, make_ctx, output, test_container):
        app = test_container.app_service
        app.create_task_list({"name": "Work"})
        app.create_task_list({"name": "Personal"})

        ctx = make_ctx(["task", "list"])
        assert await prog_task(ctx) == 1
        assert "multiple lists" in output.error_text


@pytest.mark.unit
class TestTaskAdd:
    async def test_add_auto_creates_default_list(self, make_ctx, output, test_container):
        ctx = make_ctx(["task", "add", "Buy", "groceries"])
        assert await prog_task(ctx) == 0
        assert "Buy groceries" in output.text

        lists = test_container.app_service.get_task_lists()
        assert len(lists) == 1
        assert lists[0].name == "default"
        assert len(lists[0].tasks) == 1

    async def test_add_to_named_list(self, make_ctx, output, test_container):
        app = test_container.app_service
        app.create_task_list({"name": "Work"})

        ctx = make_ctx(["task", "add", "Deploy", "--list", "Work"])
        assert await prog_task(ctx) == 0
        assert "Work" in output.text
        assert "Deploy" in output.text

    async def test_add_to_missing_list(self, make_ctx, output):
        ctx = make_ctx(["task", "add", "X", "--list", "nope"])
        assert await prog_task(ctx) == 1
        assert "not found" in output.error_text

    async def test_add_missing_title(self, make_ctx, output):
        ctx = make_ctx(["task", "add"])
        assert await prog_task(ctx) == 1
        assert "missing title" in output.error_text


@pytest.mark.unit
class TestTaskDone:
    async def test_done_by_index(self, make_ctx, output, test_container):
        app = test_container.app_service
        tl = app.create_task_list({"name": "default"})
        app.create_task(tl.id, {"title": "Finish code", "completed": False})

        ctx = make_ctx(["task", "done", "1"])
        assert await prog_task(ctx) == 0
        assert "[x]" in output.text

        updated_list = app.get_task_list(tl.id)
        assert updated_list.tasks[0].completed is True

    async def test_done_not_found(self, make_ctx, output, test_container):
        test_container.app_service.create_task_list({"name": "default"})
        ctx = make_ctx(["task", "done", "99"])
        assert await prog_task(ctx) == 1
        assert "not found" in output.error_text


@pytest.mark.unit
class TestTaskUndone:
    async def test_undone_by_index(self, make_ctx, output, test_container):
        app = test_container.app_service
        tl = app.create_task_list({"name": "default"})
        app.create_task(tl.id, {"title": "Reopen this", "completed": True})

        ctx = make_ctx(["task", "undone", "1"])
        assert await prog_task(ctx) == 0
        assert "[ ]" in output.text

        updated_list = app.get_task_list(tl.id)
        assert updated_list.tasks[0].completed is False


@pytest.mark.unit
class TestTaskDelete:
    async def test_delete_by_index(self, make_ctx, output, test_container):
        app = test_container.app_service
        tl = app.create_task_list({"name": "default"})
        app.create_task(tl.id, {"title": "Remove me", "completed": False})

        ctx = make_ctx(["task", "delete", "1"])
        assert await prog_task(ctx) == 0
        assert "Remove me" in output.text

        updated_list = app.get_task_list(tl.id)
        assert len(updated_list.tasks) == 0

    async def test_delete_not_found(self, make_ctx, output, test_container):
        test_container.app_service.create_task_list({"name": "default"})
        ctx = make_ctx(["task", "delete", "99"])
        assert await prog_task(ctx) == 1
        assert "not found" in output.error_text


@pytest.mark.unit
class TestTaskSubcommandDispatch:
    async def test_missing_subcommand(self, make_ctx, output):
        ctx = make_ctx(["task"])
        assert await prog_task(ctx) == 1
        assert "missing subcommand" in output.error_text

    async def test_unknown_subcommand(self, make_ctx, output):
        ctx = make_ctx(["task", "bogus"])
        assert await prog_task(ctx) == 1
        assert "unknown subcommand" in output.error_text
