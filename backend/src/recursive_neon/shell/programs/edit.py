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
    from recursive_neon.editor.dired import DiredEntry
    from recursive_neon.models.app_models import FileNode


class VfsDiredProvider:
    """``DiredProvider`` over the virtual filesystem.

    Translates dired's absolute virtual paths into AppService node
    operations via the shell's path resolver. Metadata the VFS does not
    model (permissions, owner, link counts) is synthesized inside
    ``editor/dired.py``; this class only reports what the VFS knows:
    names, types, content sizes, timestamps and subdirectory counts.
    """

    def __init__(self, ctx: ProgramContext) -> None:
        self._ctx = ctx
        self._app = ctx.services.app_service

    def _resolve_dir(self, path: str) -> FileNode:
        node = self._ctx.resolve_path(path)
        if node.type != "directory":
            raise NotADirectoryError(f"{path}: Not a directory")
        return node

    def _entry(self, node: FileNode) -> DiredEntry:
        from recursive_neon.editor.dired import DiredEntry

        if node.type == "directory":
            nsubdirs = sum(
                1
                for child in self._app.list_directory(node.id)
                if child.type == "directory"
            )
            return DiredEntry(
                name=node.name,
                is_dir=True,
                mtime=node.updated_at or node.created_at,
                nsubdirs=nsubdirs,
            )
        return DiredEntry(
            name=node.name,
            is_dir=False,
            size=len((node.content or "").encode("utf-8")),
            mtime=node.updated_at or node.created_at,
        )

    def list_dir(self, path: str) -> list[DiredEntry]:
        node = self._resolve_dir(path)
        return [self._entry(child) for child in self._app.list_directory(node.id)]

    def metadata(self, path: str) -> DiredEntry:
        return self._entry(self._ctx.resolve_path(path))

    def is_dir(self, path: str) -> bool | None:
        try:
            return self._ctx.resolve_path(path).type == "directory"
        except (FileNotFoundError, NotADirectoryError, ValueError):
            return None

    def create_dir(self, path: str) -> None:
        parent, name = self._ctx.resolve_parent_and_name(path)
        self._app.create_directory({"name": name, "parent_id": parent.id})

    def delete(self, path: str) -> None:
        self._app.delete_file(self._ctx.resolve_path(path).id)

    def _target(self, new: str, default_name: str) -> tuple[FileNode, str]:
        """Resolve a rename/copy target: an existing directory means
        "into that directory under the original name" (like ``mv``/``cp``
        and Emacs's dired); anything else is a parent + new-name pair."""
        try:
            node = self._ctx.resolve_path(new)
            if node.type == "directory":
                return node, default_name
        except (FileNotFoundError, NotADirectoryError, ValueError):
            pass
        return self._ctx.resolve_parent_and_name(new)

    def _node_path(self, parent: FileNode, name: str) -> str:
        from recursive_neon.shell.path_resolver import get_node_path

        base = get_node_path(parent.id, self._app)
        return ("/" + name) if base == "/" else f"{base}/{name}"

    def rename(self, old: str, new: str) -> str:
        node = self._ctx.resolve_path(old)
        parent, name = self._target(new, node.name)
        self._app.move_file(node.id, parent.id, name)
        return self._node_path(parent, name)

    def copy(self, old: str, new: str) -> str:
        node = self._ctx.resolve_path(old)
        parent, name = self._target(new, node.name)
        self._app.copy_file(node.id, parent.id, name)
        return self._node_path(parent, name)


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
    dired_dir_id: str | None = None  # directory argument → open dired

    if args:
        path_str = args[0]
        try:
            node = ctx.resolve_path(path_str)
            if node.type == "directory":
                # ``edit <dir>`` opens a dired buffer, like ``emacs <dir>``.
                dired_dir_id = node.id
            else:
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

    # Hand the editor the user's current directory so ``C-x C-f`` opens
    # with the path pre-filled (matches Emacs's ``default-directory``).
    from recursive_neon.shell.path_resolver import get_node_path

    try:
        view.editor.default_directory = get_node_path(ctx.cwd_id, app_service)
    except Exception:
        view.editor.default_directory = ""

    # Wire up shell factory for M-x shell
    data_dir = ctx.env.get("_data_dir")

    def shell_factory() -> Any:
        from recursive_neon.shell.shell import Shell

        return Shell(ctx.services, data_dir=data_dir)

    view.editor.shell_factory = shell_factory

    # Wire game-world integration (Phase 7e)
    view.editor.game_state = ctx.services.game_state
    view.editor.app_service = ctx.services.app_service
    view.editor.npc_manager = ctx.services.npc_manager
    if hasattr(ctx.services, "event_bus"):
        view.editor.event_bus = ctx.services.event_bus

    # Wire NPC message callback so replies surface in editor buffers
    npc_mgr = ctx.services.npc_manager
    if hasattr(npc_mgr, "on_message_callback"):
        npc_mgr.on_message_callback = view.editor.on_npc_event

    # Wire the dired provider (C-x d, find-file on a directory)
    view.editor.dired_provider = VfsDiredProvider(ctx)

    # Wire TUI app factories so M-x codebreaker / sysmon / portscan /
    # fsbrowse / memdump host the apps in an editor window
    # (editor/app_host.py). Imports are deferred — an app is only paid
    # for when it is actually launched.
    def _codebreaker() -> Any:
        from recursive_neon.shell.programs.codebreaker import CodeBreakerApp

        return CodeBreakerApp()

    def _sysmon() -> Any:
        from recursive_neon.shell.programs.sysmon import SysMonApp

        return SysMonApp(
            process_table=ctx.services.process_table,
            start_time=ctx.services.start_time,
        )

    def _portscan() -> Any:
        from recursive_neon.shell.programs.portscan import PortScanApp

        return PortScanApp()

    def _memdump() -> Any:
        from recursive_neon.shell.programs.memdump import MemDumpApp

        return MemDumpApp()

    def _fsbrowse() -> Any:
        from recursive_neon.shell.programs.fsbrowse import FsBrowseApp

        return FsBrowseApp(app_service=app_service, start_dir_id=ctx.cwd_id)

    view.editor.tui_app_factories = {
        "codebreaker": _codebreaker,
        "sysmon": _sysmon,
        "portscan": _portscan,
        "memdump": _memdump,
        "fsbrowse": _fsbrowse,
    }

    # Load user config from the controlled data_dir path.
    # Errors surface in *Messages* and cannot escape the data_dir boundary.
    from recursive_neon.config import settings
    from recursive_neon.editor.config_loader import load_config

    load_config(view.editor, settings.editor_config_path)

    # A directory argument opens its dired buffer on top of the initial
    # *scratch* buffer (Emacs launched on a directory does the same).
    if dired_dir_id is not None:
        from recursive_neon.editor.dired import open_dired

        open_dired(view.editor, get_node_path(dired_dir_id, app_service))
        view.sync_active_window_to_buffer()

    return await ctx.run_tui(view)
