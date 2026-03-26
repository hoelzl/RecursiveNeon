"""
neon-edit — TUI text editor shell program.

Opens a virtual filesystem file in the Emacs-inspired editor.
Bridges the editor's save callback to the virtual filesystem.

Usage: edit <path>    — open an existing file for editing
       edit           — open a scratch buffer
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from recursive_neon.shell.programs import ProgramContext, ProgramRegistry

if TYPE_CHECKING:
    from recursive_neon.editor.buffer import Buffer


def register_edit_program(registry: ProgramRegistry) -> None:
    registry.register_fn(
        "edit",
        _run_edit,
        "Open a file in neon-edit (TUI text editor)\n\n"
        "Usage: edit [<path>]\n\n"
        "Emacs-style keybindings:\n"
        "  C-x C-s   Save file\n"
        "  C-x C-c   Quit editor\n"
        "  C-f/b/n/p Move cursor\n"
        "  C-k        Kill line\n"
        "  C-y        Yank (paste)\n"
        "  C-/        Undo\n"
        "  C-space    Set mark\n"
        "  C-w        Kill region\n"
        "  C-g        Cancel",
    )


async def _run_edit(ctx: ProgramContext) -> int:
    if ctx.run_tui is None:
        ctx.stderr.error("edit: requires a terminal that supports TUI mode")
        return 1

    # Parse arguments
    args = ctx.args[1:]  # skip command name
    filepath: str | None = None
    content = ""
    name = "*scratch*"
    file_id: str | None = None

    if args:
        path_str = args[0]
        try:
            node = ctx.resolve_path(path_str)
            if node.type == "directory":
                ctx.stderr.error(f"edit: {path_str}: Is a directory")
                return 1
            content = node.content or ""
            name = node.name
            filepath = path_str
            file_id = node.id
        except (FileNotFoundError, ValueError) as e:
            # New file — try to resolve parent to validate path
            try:
                parent, fname = ctx.resolve_parent_and_name(path_str)
                name = fname
                filepath = path_str
                # file_id stays None — will create on save
            except (FileNotFoundError, ValueError):
                ctx.stderr.error(f"edit: {e}")
                return 1

    # Lazy import to avoid circular dependency (view → shell.tui → shell → edit)
    from recursive_neon.editor.view import create_editor_for_file

    # Create the editor view
    view = create_editor_for_file(content=content, name=name, filepath=filepath)

    # Wire up save callback to virtual filesystem
    app_service = ctx.services.app_service

    def save_callback(buf: Buffer) -> bool:
        nonlocal file_id
        try:
            if file_id is not None:
                # Update existing file
                app_service.update_file(file_id, {"content": buf.text})
            else:
                # Create new file
                if filepath:
                    parent, fname = ctx.resolve_parent_and_name(filepath)
                    new_node = app_service.create_file(
                        {"name": fname, "parent_id": parent.id, "content": buf.text}
                    )
                    file_id = new_node.id
                else:
                    return False
            return True
        except Exception:
            return False

    view.editor.save_callback = save_callback

    # Wire up open callback for C-x C-f (find-file)
    def open_callback(path: str) -> str:
        try:
            node = ctx.resolve_path(path)
            if node.type == "directory":
                return ""
            return node.content or ""
        except (FileNotFoundError, ValueError):
            return ""  # new file

    view.editor.open_callback = open_callback

    return await ctx.run_tui(view)
