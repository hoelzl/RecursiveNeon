"""Tests for editor ↔ game-state bridge commands (Phase 7e-1).

Covers open-note, open-task-list, and list-npcs M-x commands.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from recursive_neon.editor.commands import COMMANDS
from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.models.app_models import Note, TaskList
from recursive_neon.models.game_state import GameState
from recursive_neon.models.npc import NPC, NPCPersonality, NPCRole
from recursive_neon.services.app_service import AppService


def _submit_minibuffer(ed: Editor, text: str) -> None:
    """Type *text* into the active minibuffer and press Enter."""
    assert ed.minibuffer is not None
    ed.minibuffer.text = text
    ed.minibuffer.cursor = len(text)
    ed.minibuffer.process_key("Enter")


@pytest.fixture
def editor() -> Editor:
    km = build_default_keymap()
    ed = Editor(global_keymap=km)
    return ed


@pytest.fixture
def game_state() -> GameState:
    return GameState()


@pytest.fixture
def app_service(game_state: GameState) -> AppService:
    svc = AppService(game_state)
    svc.init_filesystem()
    return svc


@pytest.fixture
def wired_editor(
    editor: Editor, game_state: GameState, app_service: AppService
) -> Editor:
    """Editor with game state wired in."""
    editor.game_state = game_state
    editor.app_service = app_service
    return editor


def _make_note(app_service: AppService, title: str, content: str) -> Note:
    return app_service.create_note({"title": title, "content": content})


def _make_task_list(app_service: AppService, name: str, tasks: list[dict]) -> TaskList:
    tl = app_service.create_task_list({"name": name})
    for t in tasks:
        app_service.create_task(tl.id, t)
    return app_service.get_task_list(tl.id)


# ── Commands registered ──────────────────────────────────────────────


class TestCommandsRegistered:
    def test_open_note_registered(self, editor):
        assert "open-note" in COMMANDS

    def test_open_task_list_registered(self, editor):
        assert "open-task-list" in COMMANDS

    def test_list_npcs_registered(self, editor):
        assert "list-npcs" in COMMANDS


# ── open-note ────────────────────────────────────────────────────────


class TestOpenNote:
    def test_no_game_state(self, editor: Editor):
        editor.execute_command("open-note")
        assert "No game state" in editor.message

    def test_no_notes(self, wired_editor: Editor):
        wired_editor.execute_command("open-note")
        assert "No notes" in wired_editor.message

    def test_opens_note_buffer(self, wired_editor: Editor, app_service: AppService):
        _make_note(app_service, "My Note", "Hello world")
        wired_editor.execute_command("open-note")
        _submit_minibuffer(wired_editor, "My Note")
        buf = wired_editor.buffer
        assert buf.name == "*note: My Note*"
        assert buf.text == "Hello world"
        assert not buf.modified

    def test_note_save_roundtrip(self, wired_editor: Editor, app_service: AppService):
        note = _make_note(app_service, "Roundtrip", "original")
        wired_editor.execute_command("open-note")
        _submit_minibuffer(wired_editor, "Roundtrip")
        buf = wired_editor.buffer
        assert buf.on_save is not None
        # Edit via insert_string (inserts at point, which is at 0,0)
        buf.insert_string("modified ")
        assert buf.on_save(buf)
        updated = app_service.get_note(note.id)
        assert "modified" in updated.content

    def test_switch_to_existing_buffer(
        self, wired_editor: Editor, app_service: AppService
    ):
        _make_note(app_service, "Switch", "content")
        wired_editor.execute_command("open-note")
        _submit_minibuffer(wired_editor, "Switch")
        wired_editor.execute_command("open-note")
        _submit_minibuffer(wired_editor, "Switch")
        note_bufs = [b for b in wired_editor.buffers if b.name == "*note: Switch*"]
        assert len(note_bufs) == 1

    def test_nonexistent_note(self, wired_editor: Editor, app_service: AppService):
        _make_note(app_service, "Exists", "yes")
        wired_editor.execute_command("open-note")
        _submit_minibuffer(wired_editor, "Nope")
        assert "No note titled" in wired_editor.message

    def test_empty_input_cancelled(self, wired_editor: Editor, app_service: AppService):
        _make_note(app_service, "X", "y")
        wired_editor.execute_command("open-note")
        _submit_minibuffer(wired_editor, "")
        assert "Cancelled" in wired_editor.message


# ── open-task-list ───────────────────────────────────────────────────


class TestOpenTaskList:
    def test_no_game_state(self, editor: Editor):
        editor.execute_command("open-task-list")
        assert "No game state" in editor.message

    def test_no_task_lists(self, wired_editor: Editor):
        wired_editor.execute_command("open-task-list")
        assert "No task lists" in wired_editor.message

    def test_opens_task_list_buffer(
        self, wired_editor: Editor, app_service: AppService
    ):
        _make_task_list(
            app_service,
            "Work",
            [
                {"title": "Fix bug", "completed": False},
                {"title": "Write docs", "completed": True},
            ],
        )
        wired_editor.execute_command("open-task-list")
        _submit_minibuffer(wired_editor, "Work")
        buf = wired_editor.buffer
        assert buf.name == "*tasks: Work*"
        assert "- [ ] Fix bug" in buf.text
        assert "- [x] Write docs" in buf.text

    def test_task_toggle_via_save(self, wired_editor: Editor, app_service: AppService):
        tl = _make_task_list(
            app_service,
            "Toggle",
            [
                {"title": "Task A", "completed": False},
            ],
        )
        wired_editor.execute_command("open-task-list")
        _submit_minibuffer(wired_editor, "Toggle")
        buf = wired_editor.buffer
        buf.lines[0] = "- [x] Task A"
        assert buf.on_save is not None
        assert buf.on_save(buf)
        updated_tl = app_service.get_task_list(tl.id)
        assert updated_tl.tasks[0].completed is True

    def test_nonexistent_task_list(self, wired_editor: Editor, app_service: AppService):
        _make_task_list(app_service, "Real", [])
        wired_editor.execute_command("open-task-list")
        _submit_minibuffer(wired_editor, "Fake")
        assert "No task list named" in wired_editor.message

    def test_switch_to_existing_buffer(
        self, wired_editor: Editor, app_service: AppService
    ):
        _make_task_list(app_service, "Dup", [{"title": "T", "completed": False}])
        wired_editor.execute_command("open-task-list")
        _submit_minibuffer(wired_editor, "Dup")
        wired_editor.execute_command("open-task-list")
        _submit_minibuffer(wired_editor, "Dup")
        task_bufs = [b for b in wired_editor.buffers if b.name == "*tasks: Dup*"]
        assert len(task_bufs) == 1


# ── list-npcs ────────────────────────────────────────────────────────


class TestListNPCs:
    def test_no_game_state(self, editor: Editor):
        editor.execute_command("list-npcs")
        assert "No game state" in editor.message

    def test_no_npc_manager(self, wired_editor: Editor):
        wired_editor.npc_manager = None
        wired_editor.execute_command("list-npcs")
        assert "No NPC manager" in wired_editor.message

    def test_no_npcs(self, wired_editor: Editor):
        mock_mgr = Mock()
        mock_mgr.list_npcs.return_value = []
        wired_editor.npc_manager = mock_mgr
        wired_editor.execute_command("list-npcs")
        assert "No NPCs" in wired_editor.message

    def test_lists_npcs_in_buffer(self, wired_editor: Editor):
        npc = NPC(
            id="test_npc",
            name="TestBot",
            personality=NPCPersonality.FRIENDLY,
            role=NPCRole.INFORMANT,
            background="A test bot",
            occupation="Tester",
            location="Lab",
            greeting="Hi there!",
            conversation_style="friendly",
        )
        mock_mgr = Mock()
        mock_mgr.list_npcs.return_value = [npc]
        wired_editor.npc_manager = mock_mgr
        wired_editor.execute_command("list-npcs")
        buf = wired_editor.buffer
        assert buf.name == "*NPCs*"
        assert "TestBot" in buf.text
        assert "informant" in buf.text
        assert "Lab" in buf.text
        assert buf.read_only

    def test_switch_to_existing_npcs_buffer(self, wired_editor: Editor):
        npc = NPC(
            id="t",
            name="T",
            personality=NPCPersonality.FRIENDLY,
            role=NPCRole.CIVILIAN,
            background="x",
            occupation="x",
            location="x",
            greeting="x",
            conversation_style="x",
        )
        mock_mgr = Mock()
        mock_mgr.list_npcs.return_value = [npc]
        wired_editor.npc_manager = mock_mgr
        wired_editor.execute_command("list-npcs")
        wired_editor.execute_command("list-npcs")
        npc_bufs = [b for b in wired_editor.buffers if b.name == "*NPCs*"]
        assert len(npc_bufs) == 1
