"""
Game-world integration commands for neon-edit.

Bridges the editor to the game's notes, task lists, and NPCs so the
player can interact with game state directly from within the editor.

All commands are registered via ``@defcommand`` and become available
through ``M-x``.  The ``Editor.game_state`` and related fields must
be set by the hosting environment (``edit.py``) for these commands to
function; when they are ``None`` the commands display a helpful error.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from recursive_neon.editor.commands import defcommand

if TYPE_CHECKING:
    from recursive_neon.editor.buffer import Buffer
    from recursive_neon.editor.editor import Editor
    from recursive_neon.models.app_models import TaskList
    from recursive_neon.services.app_service import AppService


# ── helpers ──────────────────────────────────────────────────────────


def _require_game_state(ed: Editor) -> bool:
    """Show an error and return False if game state is not wired."""
    if ed.game_state is None:
        ed.message = "No game state available (editor not launched from shell)"
        return False
    return True


# ── open-note ────────────────────────────────────────────────────────


@defcommand("open-note", "Open a game note as a buffer.")
def open_note(ed: Editor, prefix: int | None) -> None:
    if not _require_game_state(ed):
        return
    assert ed.app_service is not None

    notes = ed.app_service.get_notes()
    if not notes:
        ed.message = "No notes found"
        return

    candidates = [n.title for n in notes]

    def completer(partial: str) -> list[str]:
        return [c for c in candidates if c.lower().startswith(partial.lower())]

    def callback(title: str) -> None:
        title = title.strip()
        if not title:
            ed.message = "Cancelled"
            return
        # Find the note by title
        matched = [n for n in notes if n.title == title]
        if not matched:
            ed.message = f"No note titled {title!r}"
            return
        note = matched[0]
        buf_name = f"*note: {note.title}*"

        # Switch to existing buffer if already open
        if ed.switch_to_buffer(buf_name):
            return

        # Create buffer with note content
        buf = ed.create_buffer(buf_name, text=note.content)
        buf.modified = False

        # Install save hook that writes back to the note
        def on_save(saved_buf: Buffer) -> bool:
            try:
                ed.app_service.update_note(  # type: ignore[union-attr]
                    note.id,
                    {"title": note.title, "content": saved_buf.text},
                )
                return True
            except Exception:
                return False

        buf.on_save = on_save

    ed.start_minibuffer("Open note: ", callback, completer=completer)


@defcommand("open-task-list", "Open a task list as a checkbox buffer.")
def open_task_list(ed: Editor, prefix: int | None) -> None:
    if not _require_game_state(ed):
        return
    assert ed.app_service is not None

    task_lists = ed.app_service.get_task_lists()
    if not task_lists:
        ed.message = "No task lists found"
        return

    candidates = [tl.name for tl in task_lists]

    def completer(partial: str) -> list[str]:
        return [c for c in candidates if c.lower().startswith(partial.lower())]

    def callback(name: str) -> None:
        name = name.strip()
        if not name:
            ed.message = "Cancelled"
            return
        matched = [tl for tl in task_lists if tl.name == name]
        if not matched:
            ed.message = f"No task list named {name!r}"
            return
        tl = matched[0]
        buf_name = f"*tasks: {tl.name}*"

        if ed.switch_to_buffer(buf_name):
            return

        # Render tasks as checkbox lines
        lines = _render_task_list(tl)
        buf = ed.create_buffer(buf_name, text="\n".join(lines))
        buf.modified = False

        # Install save hook that parses checkbox state back
        def on_save(saved_buf: Buffer) -> bool:
            try:
                _sync_task_list_from_buffer(ed.app_service, tl.id, saved_buf.text)  # type: ignore[arg-type]
                return True
            except Exception:
                return False

        buf.on_save = on_save

    ed.start_minibuffer("Open task list: ", callback, completer=completer)


def _render_task_list(tl: TaskList) -> list[str]:
    """Render a TaskList as ``- [x] title`` / ``- [ ] title`` lines."""
    lines: list[str] = []
    for task in tl.tasks:
        marker = "x" if task.completed else " "
        lines.append(f"- [{marker}] {task.title}")
    return lines


_TASK_LINE_RE = re.compile(r"^- \[([ xX])\] (.+)$")


def _sync_task_list_from_buffer(
    app_service: AppService,
    list_id: str,
    text: str,
) -> None:
    """Parse checkbox buffer text and update task completion state."""
    tl = app_service.get_task_list(list_id)
    lines = text.split("\n")
    task_idx = 0
    for line in lines:
        m = _TASK_LINE_RE.match(line.rstrip())
        if m and task_idx < len(tl.tasks):
            completed = m.group(1).lower() == "x"
            task = tl.tasks[task_idx]
            if task.completed != completed:
                app_service.update_task(list_id, task.id, {"completed": completed})
            task_idx += 1


@defcommand("list-npcs", "Show all known NPCs in a read-only buffer.")
def list_npcs(ed: Editor, prefix: int | None) -> None:
    if not _require_game_state(ed):
        return
    if ed.npc_manager is None:
        ed.message = "No NPC manager available"
        return

    npcs = ed.npc_manager.list_npcs()
    if not npcs:
        ed.message = "No NPCs registered"
        return

    buf_name = "*NPCs*"
    if ed.switch_to_buffer(buf_name):
        return

    lines = []
    for npc in npcs:
        lines.append(f"{npc.name} ({npc.id})")
        lines.append(f"  Role: {npc.role.value}, Location: {npc.location}")
        lines.append(f"  {npc.greeting}")
        lines.append("")

    buf = ed.create_buffer(buf_name, text="\n".join(lines))
    buf.read_only = True
    buf.modified = False
