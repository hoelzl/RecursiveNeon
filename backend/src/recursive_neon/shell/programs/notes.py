"""
Note program — manage notes from the shell.

Subcommands: list, show, create, edit, delete.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from recursive_neon.shell.completion import CompletionContext, complete_choices
from recursive_neon.shell.output import BOLD, DIM, YELLOW
from recursive_neon.shell.programs import ProgramContext, ProgramRegistry

if TYPE_CHECKING:
    from recursive_neon.editor.buffer import Buffer


# ---------------------------------------------------------------------------
# Note ↔ editor text format: ``# Title\n\n...content...``
# ---------------------------------------------------------------------------


def _format_note_text(title: str, content: str) -> str:
    """Format a note as editor text with ``# Title`` first-line convention."""
    return f"# {title}\n\n{content}"


def _parse_note_text(text: str) -> tuple[str, str]:
    """Parse editor text into *(title, content)*.

    The first line is the title (``# `` prefix stripped if present).
    Content is everything after the first line, with one leading blank
    line stripped (matching the format produced by :func:`_format_note_text`).
    """
    if not text:
        return ("", "")

    lines = text.split("\n")
    first_line = lines[0]

    # Extract title
    if first_line.startswith("# "):
        title = first_line[2:].strip()
    else:
        title = first_line.strip()

    # Extract content — skip the title line and one blank separator line
    rest = lines[1:]
    if rest and rest[0] == "":
        rest = rest[1:]
    content = "\n".join(rest)

    return (title, content)


async def prog_note(ctx: ProgramContext) -> int:
    """Dispatch note subcommands."""
    if len(ctx.args) < 2:
        ctx.stderr.error("note: missing subcommand (list, show, create, edit, delete)")
        return 1

    sub = ctx.args[1]
    dispatch = {
        "list": _note_list,
        "ls": _note_list,
        "show": _note_show,
        "create": _note_create,
        "new": _note_create,
        "edit": _note_edit,
        "delete": _note_delete,
        "rm": _note_delete,
        "browse": _note_browse,
    }
    handler = dispatch.get(sub)
    if handler is None:
        ctx.stderr.error(f"note: unknown subcommand '{sub}'")
        return 1
    return await handler(ctx)


async def _note_list(ctx: ProgramContext) -> int:
    """List all notes."""
    notes = ctx.services.app_service.get_notes()
    if not notes:
        ctx.stdout.writeln("No notes.")
        return 0

    for i, note in enumerate(notes, 1):
        idx = ctx.stdout.styled(f"[{i}]", YELLOW)
        title = ctx.stdout.styled(note.title, BOLD)
        date = ctx.stdout.styled(note.updated_at.strftime("%Y-%m-%d"), DIM)
        preview = note.content[:60].replace("\n", " ")
        if len(note.content) > 60:
            preview += "..."
        ctx.stdout.writeln(f"{idx} {title}  {date}")
        if preview:
            ctx.stdout.writeln(f"    {preview}")
    return 0


def _resolve_note(ctx: ProgramContext, ref: str):
    """Resolve a note reference (1-based index or UUID prefix).

    Returns None if not found or if the UUID prefix is ambiguous.
    """
    notes = ctx.services.app_service.get_notes()
    # Try as 1-based index
    try:
        idx = int(ref)
        if 1 <= idx <= len(notes):
            return notes[idx - 1]
    except ValueError:
        pass
    # Try as UUID prefix (must be unambiguous)
    matches = [note for note in notes if note.id.startswith(ref)]
    if len(matches) == 1:
        return matches[0]
    return None


async def _note_show(ctx: ProgramContext) -> int:
    """Show a note's full content."""
    if len(ctx.args) < 3:
        ctx.stderr.error("note show: missing note reference")
        return 1
    note = _resolve_note(ctx, ctx.args[2])
    if note is None:
        ctx.stderr.error(f"note show: note '{ctx.args[2]}' not found")
        return 1
    ctx.stdout.writeln(ctx.stdout.styled(note.title, BOLD))
    ctx.stdout.writeln(ctx.stdout.styled(f"Created: {note.created_at}", DIM))
    ctx.stdout.writeln(ctx.stdout.styled(f"Updated: {note.updated_at}", DIM))
    ctx.stdout.writeln()
    ctx.stdout.writeln(note.content)
    return 0


async def _note_create(ctx: ProgramContext) -> int:
    """Create a new note.

    With ``-c``, creates immediately.  Without it, opens the editor so
    the user can compose the note body interactively.
    """
    # Parse: note create <title> [-c <content>]
    args = ctx.args[2:]
    if not args:
        ctx.stderr.error("note create: missing title")
        return 1

    title_parts: list[str] = []
    content: str | None = None
    i = 0
    while i < len(args):
        if args[i] in ("-c", "--content") and i + 1 < len(args):
            content = args[i + 1]
            i += 2
        else:
            title_parts.append(args[i])
            i += 1

    title = " ".join(title_parts)
    if not title:
        ctx.stderr.error("note create: missing title")
        return 1

    # Inline content supplied — create immediately
    if content is not None:
        note = ctx.services.app_service.create_note(
            {"title": title, "content": content}
        )
        ctx.stdout.writeln(f"Created note: {ctx.stdout.styled(note.title, BOLD)}")
        return 0

    # No -c flag — open editor if TUI is available
    if ctx.run_tui is None:
        # No TUI — create with empty content (graceful fallback)
        note = ctx.services.app_service.create_note({"title": title, "content": ""})
        ctx.stdout.writeln(f"Created note: {ctx.stdout.styled(note.title, BOLD)}")
        return 0

    return await _note_create_in_editor(ctx, title)


async def _note_create_in_editor(ctx: ProgramContext, title: str) -> int:
    """Open the editor for composing a new note."""
    assert ctx.run_tui is not None
    from recursive_neon.editor.view import create_editor_for_file

    text = _format_note_text(title, "")
    view = create_editor_for_file(content=text, name=f"note:{title}")

    app_service = ctx.services.app_service
    created_note_id: str | None = None

    def save_callback(buf: Buffer) -> bool:
        nonlocal created_note_id
        parsed_title, parsed_content = _parse_note_text(buf.text)
        if not parsed_title:
            return False
        if created_note_id is not None:
            app_service.update_note(
                created_note_id, {"title": parsed_title, "content": parsed_content}
            )
        else:
            new_note = app_service.create_note(
                {"title": parsed_title, "content": parsed_content}
            )
            created_note_id = new_note.id
        return True

    view.editor.save_callback = save_callback

    result = await ctx.run_tui(view)

    if created_note_id is not None:
        note_obj = app_service.get_note(created_note_id)
        ctx.stdout.writeln(f"Created note: {ctx.stdout.styled(note_obj.title, BOLD)}")

    return result


async def _note_edit(ctx: ProgramContext) -> int:
    """Edit a note — opens in neon-edit, or accepts inline flags."""
    if len(ctx.args) < 3:
        ctx.stderr.error("note edit: missing note reference")
        return 1
    note = _resolve_note(ctx, ctx.args[2])
    if note is None:
        ctx.stderr.error(f"note edit: note '{ctx.args[2]}' not found")
        return 1

    # Parse optional flags: --title <t> --content <c> / -t <t> -c <c>
    args = ctx.args[3:]

    # If flags are present, use inline editing (backward compat)
    if args:
        updates: dict[str, str] = {}
        i = 0
        while i < len(args):
            if args[i] in ("-t", "--title") and i + 1 < len(args):
                updates["title"] = args[i + 1]
                i += 2
            elif args[i] in ("-c", "--content") and i + 1 < len(args):
                updates["content"] = args[i + 1]
                i += 2
            else:
                ctx.stderr.error(f"note edit: unknown option: {args[i]}")
                return 1
        if not updates:
            ctx.stderr.error("note edit: provide --title and/or --content")
            return 1
        updated = ctx.services.app_service.update_note(note.id, updates)
        ctx.stdout.writeln(f"Updated note: {ctx.stdout.styled(updated.title, BOLD)}")
        return 0

    # No flags — open in editor
    if ctx.run_tui is None:
        ctx.stderr.error(
            "note edit: requires a terminal that supports TUI mode"
            " (or use --title/-t --content/-c flags)"
        )
        return 1

    return await _note_edit_in_editor(ctx, note)


async def _note_edit_in_editor(ctx: ProgramContext, note) -> int:
    """Open an existing note in the editor."""
    assert ctx.run_tui is not None
    from recursive_neon.editor.view import create_editor_for_file

    text = _format_note_text(note.title, note.content)
    view = create_editor_for_file(content=text, name=f"note:{note.title}")

    app_service = ctx.services.app_service
    note_id = note.id

    def save_callback(buf: Buffer) -> bool:
        parsed_title, parsed_content = _parse_note_text(buf.text)
        if not parsed_title:
            return False
        app_service.update_note(
            note_id, {"title": parsed_title, "content": parsed_content}
        )
        return True

    view.editor.save_callback = save_callback

    result = await ctx.run_tui(view)

    updated_note = app_service.get_note(note_id)
    ctx.stdout.writeln(f"Updated note: {ctx.stdout.styled(updated_note.title, BOLD)}")

    return result


async def _note_delete(ctx: ProgramContext) -> int:
    """Delete a note."""
    if len(ctx.args) < 3:
        ctx.stderr.error("note delete: missing note reference")
        return 1
    note = _resolve_note(ctx, ctx.args[2])
    if note is None:
        ctx.stderr.error(f"note delete: note '{ctx.args[2]}' not found")
        return 1
    ctx.services.app_service.delete_note(note.id)
    ctx.stdout.writeln(f"Deleted note: {note.title}")
    return 0


# ---------------------------------------------------------------------------
# note browse — interactive notes editor
# ---------------------------------------------------------------------------

_NOTES_BUFFER_NAME = "*Notes*"


async def _note_browse(ctx: ProgramContext) -> int:
    """Open an interactive notes browser in neon-edit."""
    if ctx.run_tui is None:
        ctx.stderr.error("note browse: requires a terminal that supports TUI mode")
        return 1

    from recursive_neon.editor.keymap import Keymap
    from recursive_neon.editor.view import create_editor_for_file

    app_service = ctx.services.app_service
    view = create_editor_for_file(content="", name=_NOTES_BUFFER_NAME)
    ed = view.editor

    # -- helpers -----------------------------------------------------------

    def _render_notes_list() -> str:
        """Build the text content for the *Notes* buffer."""
        notes = app_service.get_notes()
        if not notes:
            return "  (no notes)\n\n  Press [c] to create a note."
        lines = []
        for i, note in enumerate(notes, 1):
            preview = note.content[:50].replace("\n", " ")
            if len(note.content) > 50:
                preview += "..."
            date = note.updated_at.strftime("%Y-%m-%d")
            lines.append(f"  [{i:>3}]  {note.title:<30}  {date}  {preview}")
        lines.append("")
        lines.append("  [Enter] Open  [c] Create  [d] Delete  [g] Refresh  [q] Quit")
        return "\n".join(lines)

    def _refresh_notes_buffer() -> None:
        """Repopulate the *Notes* buffer with the current note list."""
        buf = ed.buffer
        if buf.name != _NOTES_BUFFER_NAME:
            # Switch to *Notes* if it exists
            if not ed.switch_to_buffer(_NOTES_BUFFER_NAME):
                return
            buf = ed.buffer
        buf.read_only = False
        buf.lines = _render_notes_list().split("\n")
        buf.point.move_to(0, 0)
        buf.modified = False
        buf.read_only = True

    def _current_note_index() -> int | None:
        """Parse the 1-based note index from the line at point."""
        buf = ed.buffer
        if buf.name != _NOTES_BUFFER_NAME:
            return None
        line = buf.lines[buf.point.line] if buf.point.line < buf.line_count else ""
        # Lines look like: "  [  1]  Title ..."
        import re

        m = re.match(r"\s*\[\s*(\d+)\]", line)
        return int(m.group(1)) if m else None

    # -- buffer-local actions ----------------------------------------------

    def _open_note_at_point(editor, _prefix) -> None:  # noqa: ANN001
        idx = _current_note_index()
        if idx is None:
            editor.message = "No note on this line"
            return
        notes = app_service.get_notes()
        if not (1 <= idx <= len(notes)):
            editor.message = f"Note {idx} not found"
            return
        note = notes[idx - 1]

        # Check if already open
        buf_name = f"note:{note.title}"
        if editor.switch_to_buffer(buf_name):
            editor.message = f"Switched to {buf_name}"
            return

        # Create a new buffer for this note
        text = _format_note_text(note.title, note.content)
        editor.create_buffer(name=buf_name, text=text)
        note_id = note.id

        def save_cb(b: Buffer) -> bool:
            parsed_title, parsed_content = _parse_note_text(b.text)
            if not parsed_title:
                return False
            app_service.update_note(
                note_id, {"title": parsed_title, "content": parsed_content}
            )
            # Update buffer name to reflect new title
            b.name = f"note:{parsed_title}"
            return True

        editor.save_callback = save_cb
        editor.message = f"Opened note: {note.title}"

    def _create_note(editor, _prefix) -> None:  # noqa: ANN001
        def callback(title: str) -> None:
            title = title.strip()
            if not title:
                return
            new_note = app_service.create_note({"title": title, "content": ""})
            text = _format_note_text(new_note.title, "")
            editor.create_buffer(name=f"note:{new_note.title}", text=text)
            note_id = new_note.id

            def save_cb(b: Buffer) -> bool:
                parsed_title, parsed_content = _parse_note_text(b.text)
                if not parsed_title:
                    return False
                app_service.update_note(
                    note_id, {"title": parsed_title, "content": parsed_content}
                )
                b.name = f"note:{parsed_title}"
                return True

            editor.save_callback = save_cb
            editor.message = f"Created note: {new_note.title}"

        editor.start_minibuffer("Note title: ", callback)

    def _delete_note_at_point(editor, _prefix) -> None:  # noqa: ANN001
        idx = _current_note_index()
        if idx is None:
            editor.message = "No note on this line"
            return
        notes = app_service.get_notes()
        if not (1 <= idx <= len(notes)):
            editor.message = f"Note {idx} not found"
            return
        note = notes[idx - 1]

        def confirm(answer: str) -> None:
            if answer.strip().lower() in ("y", "yes"):
                app_service.delete_note(note.id)
                editor.message = f"Deleted: {note.title}"
                _refresh_notes_buffer()
            else:
                editor.message = "Cancelled"

        editor.start_minibuffer(f"Delete '{note.title}'? (y/n) ", confirm)

    def _refresh(editor, _prefix) -> None:  # noqa: ANN001
        _refresh_notes_buffer()
        editor.message = "Notes list refreshed"

    # -- set up *Notes* buffer with local keymap ---------------------------

    notes_km = Keymap("notes", parent=ed.global_keymap)
    notes_km.bind("Enter", _open_note_at_point)
    notes_km.bind("o", _open_note_at_point)
    notes_km.bind("c", _create_note)
    notes_km.bind("d", _delete_note_at_point)
    notes_km.bind("g", _refresh)
    notes_km.bind("q", "quit-editor")

    buf = ed.buffer
    buf.name = _NOTES_BUFFER_NAME
    buf.keymap = notes_km
    buf.on_focus = _refresh_notes_buffer
    _refresh_notes_buffer()

    return await ctx.run_tui(view)


_NOTE_SUBCOMMANDS = [
    "list",
    "ls",
    "show",
    "create",
    "new",
    "edit",
    "delete",
    "rm",
    "browse",
]
_NOTE_REF_SUBCOMMANDS = {"show", "edit", "delete", "rm"}


def _complete_note(ctx: CompletionContext) -> list[str]:
    if ctx.arg_index == 1:
        return complete_choices(_NOTE_SUBCOMMANDS, ctx.current)
    if ctx.arg_index == 2 and len(ctx.args) >= 2:
        sub = ctx.args[1]
        if sub in _NOTE_REF_SUBCOMMANDS:
            return _complete_note_refs(ctx)
        if sub in ("create", "new") and ctx.current.startswith("-"):
            return complete_choices(["-c", "--content"], ctx.current)
    if (
        len(ctx.args) >= 2
        and ctx.args[1] == "edit"
        and ctx.arg_index >= 3
        and ctx.current.startswith("-")
    ):
        return complete_choices(["-t", "--title", "-c", "--content"], ctx.current)
    return []


def _complete_note_refs(ctx: CompletionContext) -> list[str]:
    notes = ctx.services.app_service.get_notes()
    return [str(i) for i, _ in enumerate(notes, 1) if str(i).startswith(ctx.current)]


def register_note_program(registry: ProgramRegistry) -> None:
    """Register the note program."""
    registry.register_fn(
        "note",
        prog_note,
        "Manage notes\n"
        "\n"
        "Usage: note <subcommand> [args...]\n"
        "\n"
        "Subcommands:\n"
        "  list               List all notes\n"
        "  show <ref>         Show a note (by index or ID)\n"
        "  create <title>     Create a note (opens editor, or -c <content>)\n"
        "  edit <ref>         Edit a note in neon-edit (or -t/-c flags)\n"
        "  delete <ref>       Delete a note\n"
        "  browse             Interactive notes browser in neon-edit",
        completer=_complete_note,
    )
