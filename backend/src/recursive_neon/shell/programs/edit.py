"""
neon-edit — TUI text editor shell program.

Opens a virtual filesystem file in the Emacs-inspired editor.
Bridges the editor's save callback to the virtual filesystem.

Usage: edit <path>    — open an existing file for editing
       edit           — open a scratch buffer
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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
    initial_file_id: str | None = None

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
            initial_file_id = node.id
        except (FileNotFoundError, ValueError) as e:
            # New file — try to resolve parent to validate path
            try:
                parent, fname = ctx.resolve_parent_and_name(path_str)
                name = fname
                filepath = path_str
                # initial_file_id stays None — will create on save
            except (FileNotFoundError, ValueError):
                ctx.stderr.error(f"edit: {e}")
                return 1

    # Lazy import to avoid circular dependency (view → shell.tui → shell → edit)
    from recursive_neon.editor.view import create_editor_for_file

    # Create the editor view
    view = create_editor_for_file(content=content, name=name, filepath=filepath)

    # Wire up save callback to virtual filesystem.
    # Per-buffer mapping from buffer identity to filesystem node ID.
    app_service = ctx.services.app_service
    buf_file_ids: dict[int, str] = {}

    # Register the initial buffer if it has a file_id
    if initial_file_id is not None:
        buf_file_ids[id(view.editor.buffer)] = initial_file_id

    def save_callback(buf: Buffer) -> bool:
        try:
            fid = buf_file_ids.get(id(buf))
            if fid is not None:
                # Update existing file
                app_service.update_file(fid, {"content": buf.text})
            else:
                # Create new file — use buf.filepath (set by write-file command)
                path = buf.filepath
                if path:
                    parent, fname = ctx.resolve_parent_and_name(path)
                    # Check if the file already exists (e.g., opened via find-file)
                    try:
                        existing = ctx.resolve_path(path)
                        if existing.type != "directory":
                            # Update existing file and register it
                            app_service.update_file(existing.id, {"content": buf.text})
                            buf_file_ids[id(buf)] = existing.id
                            return True
                    except (FileNotFoundError, ValueError):
                        pass
                    new_node = app_service.create_file(
                        {"name": fname, "parent_id": parent.id, "content": buf.text}
                    )
                    buf_file_ids[id(buf)] = new_node.id
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
            # Register the file_id for this path so save works correctly
            # The buffer doesn't exist yet — it will be registered when
            # the editor creates it and we get a save_callback call.
            # We stash the mapping keyed by path for the save_callback
            # to pick up via resolve_path.
            return node.content or ""
        except (FileNotFoundError, ValueError):
            return ""  # new file

    view.editor.open_callback = open_callback

    # Wire up path completer for C-x C-f (find-file) and C-x C-w (write-file)
    from recursive_neon.shell.completion import _path_completions

    def path_completer(partial: str) -> list[str]:
        return _path_completions(partial, ctx.cwd_id, app_service, quote=False)

    view.editor.path_completer = path_completer

    # Wire up shell factory for M-x shell
    data_dir = ctx.env.get("_data_dir")

    def shell_factory() -> Any:
        from recursive_neon.shell.shell import Shell

        return Shell(ctx.services, data_dir=data_dir)

    view.editor.shell_factory = shell_factory

    # Load user config (~/.neon-edit.py) — errors surface in *Messages*
    from recursive_neon.editor.config_loader import load_config

    load_config(view.editor)

    return await ctx.run_tui(view)
