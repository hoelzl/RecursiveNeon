"""
Note program — manage notes from the shell.

Subcommands: list, show, create, edit, delete.
"""

from __future__ import annotations

from recursive_neon.shell.completion import CompletionContext, complete_choices
from recursive_neon.shell.output import BOLD, DIM, YELLOW
from recursive_neon.shell.programs import ProgramContext, ProgramRegistry


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
    """Create a new note."""
    # Parse: note create <title> [-c <content>]
    args = ctx.args[2:]
    if not args:
        ctx.stderr.error("note create: missing title")
        return 1

    title_parts: list[str] = []
    content = ""
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

    note = ctx.services.app_service.create_note({"title": title, "content": content})
    ctx.stdout.writeln(f"Created note: {ctx.stdout.styled(note.title, BOLD)}")
    return 0


async def _note_edit(ctx: ProgramContext) -> int:
    """Edit a note's title or content."""
    if len(ctx.args) < 3:
        ctx.stderr.error("note edit: missing note reference")
        return 1
    note = _resolve_note(ctx, ctx.args[2])
    if note is None:
        ctx.stderr.error(f"note edit: note '{ctx.args[2]}' not found")
        return 1

    # Parse optional flags: --title <t> --content <c> / -t <t> -c <c>
    args = ctx.args[3:]
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


_NOTE_SUBCOMMANDS = ["list", "ls", "show", "create", "new", "edit", "delete", "rm"]
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
        "  create <title>     Create a note (-c <content>)\n"
        "  edit <ref>         Edit a note (-t <title> -c <content>)\n"
        "  delete <ref>       Delete a note",
        completer=_complete_note,
    )
