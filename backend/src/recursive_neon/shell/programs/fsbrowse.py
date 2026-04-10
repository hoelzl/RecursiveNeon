"""
fsbrowse — full-screen file browser TUI.

Two-pane layout: directory tree (left 40%) + file preview (right 60%).
Navigate with arrow keys, Enter to enter a directory or preview a file,
Backspace to go up, ``q`` to quit, ``e`` to open a file in neon-edit.

Launched via the ``fsbrowse`` shell command.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from recursive_neon.models.app_models import FileNode
from recursive_neon.shell.output import BOLD, CYAN, DIM, RESET
from recursive_neon.shell.path_resolver import get_node_path
from recursive_neon.shell.programs import ProgramContext, ProgramRegistry
from recursive_neon.shell.tui import ScreenBuffer

if TYPE_CHECKING:
    from recursive_neon.services.app_service import AppService

PREVIEW_MAX_LINES = 200
DIR_ICON = "\u25b8"  # ▸
FILE_ICON = "\u2500"  # ─


@dataclass
class FsBrowseState:
    """Mutable state for the file browser."""

    app_service: AppService
    cwd_id: str
    entries: list[FileNode] = field(default_factory=list)
    cursor: int = 0
    scroll_offset: int = 0
    preview_lines: list[str] = field(default_factory=list)
    preview_name: str = ""
    preview_is_dir: bool = False
    preview_truncated: bool = False
    message: str = ""

    @staticmethod
    def _sorted_dir_first(children: list[FileNode]) -> list[FileNode]:
        """Return *children* sorted directories-first, case-insensitive."""
        dirs = sorted(
            (c for c in children if c.type == "directory"), key=lambda n: n.name.lower()
        )
        files = sorted(
            (c for c in children if c.type == "file"), key=lambda n: n.name.lower()
        )
        return dirs + files

    def refresh_entries(self) -> None:
        """Reload children of the current directory, sorted dirs-first."""
        children = self.app_service.list_directory(self.cwd_id)
        self.entries = self._sorted_dir_first(children)
        self.cursor = min(self.cursor, max(0, len(self.entries) - 1))
        self.scroll_offset = 0
        self._update_preview()

    def _update_preview(self) -> None:
        """Update the preview pane for the currently selected entry."""
        if not self.entries:
            self.preview_lines = []
            self.preview_name = ""
            self.preview_is_dir = False
            self.preview_truncated = False
            return

        node = self.entries[self.cursor]
        self.preview_name = node.name
        self.preview_is_dir = node.type == "directory"

        if node.type == "directory":
            children = self.app_service.list_directory(node.id)
            sorted_children = self._sorted_dir_first(children)
            self.preview_lines = []
            for child in sorted_children:
                if child.type == "directory":
                    self.preview_lines.append(f"{DIR_ICON} {child.name}/")
                else:
                    self.preview_lines.append(f"  {child.name}")
            self.preview_truncated = False
        else:
            content = node.content or ""
            all_lines = content.split("\n")
            if len(all_lines) > PREVIEW_MAX_LINES:
                self.preview_lines = all_lines[:PREVIEW_MAX_LINES]
                self.preview_truncated = True
            else:
                self.preview_lines = all_lines
                self.preview_truncated = False

    @property
    def selected_node(self) -> FileNode | None:
        if not self.entries:
            return None
        return self.entries[self.cursor]

    def current_path(self) -> str:
        return get_node_path(self.cwd_id, self.app_service)


class FsBrowseApp:
    """TUI app for the full-screen file browser."""

    tick_interval_ms: int = 0

    def __init__(
        self,
        app_service: AppService,
        start_dir_id: str,
    ) -> None:
        self.state = FsBrowseState(app_service=app_service, cwd_id=start_dir_id)
        self.width = 80
        self.height = 24
        self._tui_launcher: Callable[[Any], Awaitable[int]] | None = None
        self._pending_edit: FileNode | None = None

    def set_tui_launcher(self, launcher: Callable[[Any], Awaitable[int]]) -> None:
        self._tui_launcher = launcher

    def on_start(self, width: int, height: int) -> ScreenBuffer:
        self.width = width
        self.height = height
        self.state.refresh_entries()
        self.state.message = "[Enter] open  [Backspace] up  [e] edit  [q] quit"
        return self._render()

    def on_key(self, key: str) -> ScreenBuffer | None:
        if key in ("q", "Escape", "C-c"):
            return None

        if key == "ArrowUp":
            if self.state.cursor > 0:
                self.state.cursor -= 1
                self.state._update_preview()
        elif key == "ArrowDown":
            if self.state.cursor < len(self.state.entries) - 1:
                self.state.cursor += 1
                self.state._update_preview()
        elif key == "Enter":
            self._action_enter()
        elif key == "Backspace":
            self._action_go_up()
        elif key == "e":
            self._action_edit()

        return self._render()

    def on_resize(self, width: int, height: int) -> ScreenBuffer:
        self.width = width
        self.height = height
        return self._render()

    async def on_after_key(self) -> ScreenBuffer | None:
        """Launch neon-edit for a pending file edit after the key handler returns."""
        if self._pending_edit is None or self._tui_launcher is None:
            return None

        node = self._pending_edit
        self._pending_edit = None

        from recursive_neon.editor.view import create_editor_for_file

        content = node.content or ""
        view = create_editor_for_file(content=content, name=node.name)

        # Wire up a save callback that writes back to the virtual filesystem
        app_service = self.state.app_service
        file_id = node.id

        def on_save(buf: Any) -> bool:
            try:
                app_service.update_file(file_id, {"content": buf.text})
                return True
            except Exception:
                return False

        view.editor.save_callback = on_save

        await self._tui_launcher(view)

        # Refresh preview after returning from editor
        self.state._update_preview()
        return self._render()

    # ── internal actions ─────────────────────────────────────────────

    def _action_enter(self) -> None:
        node = self.state.selected_node
        if node is None:
            return
        if node.type == "directory":
            self.state.cwd_id = node.id
            self.state.cursor = 0
            self.state.refresh_entries()
        # For files, Enter just updates the preview (already done by cursor move)

    def _action_go_up(self) -> None:
        current_dir = self.state.app_service.get_file(self.state.cwd_id)
        if current_dir.parent_id is not None:
            self.state.cwd_id = current_dir.parent_id
            self.state.cursor = 0
            self.state.refresh_entries()
            # Try to position cursor on the directory we just left
            for i, entry in enumerate(self.state.entries):
                if entry.id == current_dir.id:
                    self.state.cursor = i
                    self.state._update_preview()
                    break

    def _action_edit(self) -> None:
        node = self.state.selected_node
        if node is None or node.type != "file":
            self.state.message = "Select a file to edit"
            return
        if self._tui_launcher is None:
            self.state.message = "Editor not available"
            return
        self._pending_edit = node
        self.state.message = f"Opening {node.name} in editor..."

    # ── rendering ────────────────────────────────────────────────────

    def _render(self) -> ScreenBuffer:
        screen = ScreenBuffer.create(self.width, self.height)
        screen.cursor_visible = False

        left_w = min(max(20, int(self.width * 0.4)), self.width - 2)
        right_w = max(1, self.width - left_w - 1)  # 1 col for separator

        # Title bar
        path_display = self.state.current_path()
        title = f" FILE BROWSER \u2500 {path_display} "
        screen.set_line(0, f"{BOLD}{CYAN}{title:{self.width}}{RESET}")

        # Column headers — build full line to avoid ANSI truncation in set_region
        hdr_left = f"{'  Name':{left_w}}"
        hdr_right = f"{' Preview':{right_w}}"
        screen.set_line(
            1, f"{BOLD}{hdr_left}{RESET}{DIM}\u2502{RESET}{BOLD}{hdr_right}{RESET}"
        )

        # Separator line (no ANSI, safe for set_line)
        hline = "\u2500"
        screen.set_line(2, f"{hline * left_w}\u253c{hline * right_w}")

        # Content area (rows 3 to height-3)
        content_start = 3
        content_rows = max(0, self.height - content_start - 2)  # reserve 2 rows

        if content_rows == 0:
            # Terminal too small — just show title
            return screen

        # Scroll the directory listing
        if self.state.cursor < self.state.scroll_offset:
            self.state.scroll_offset = self.state.cursor
        elif self.state.cursor >= self.state.scroll_offset + content_rows:
            self.state.scroll_offset = self.state.cursor - content_rows + 1

        # Render directory entries (left pane) + separator + preview (right pane)
        for i in range(content_rows):
            row = content_start + i
            idx = self.state.scroll_offset + i

            # Left pane: directory entry
            if idx < len(self.state.entries):
                entry = self.state.entries[idx]
                is_selected = idx == self.state.cursor

                if entry.type == "directory":
                    icon = DIR_ICON
                    name_display = f"{entry.name}/"
                    style = (
                        f"{BOLD}{CYAN}" if not is_selected else f"\033[7m{BOLD}{CYAN}"
                    )
                else:
                    icon = FILE_ICON
                    name_display = entry.name
                    style = "" if not is_selected else "\033[7m"

                # Build plain label, fit to left_w, then wrap with ANSI
                label = f" {icon} {name_display}"
                if len(label) > left_w:
                    label = label[: left_w - 1] + "\u2026"
                plain_left = f"{label:{left_w}}"
                left_part = f"{style}{plain_left}{RESET}" if style else plain_left
            else:
                left_part = " " * left_w

            # Separator column
            sep = f"{DIM}\u2502{RESET}"

            # Right pane: preview
            if i < len(self.state.preview_lines):
                pline = self.state.preview_lines[i]
                if len(pline) > right_w - 1:
                    pline = pline[: right_w - 2] + "\u2026"
                right_part = f" {pline}"
            elif i == len(self.state.preview_lines) and self.state.preview_truncated:
                right_part = f" {DIM}... ({PREVIEW_MAX_LINES} lines shown){RESET}"
            elif i == 0 and not self.state.entries:
                right_part = f" {DIM}(empty directory){RESET}"
            else:
                right_part = ""

            screen.set_line(row, f"{left_part}{sep}{right_part}")

        # Status bar
        status_row = self.height - 2
        if self.state.entries:
            total = len(self.state.entries)
            pos = self.state.cursor + 1
            node = self.state.selected_node
            kind = "dir" if node and node.type == "directory" else "file"
            status = f" {pos}/{total} ({kind})"
        else:
            status = " (empty)"
        screen.set_line(
            status_row,
            f"{DIM}{status:{self.width}}{RESET}",
        )

        # Controls / message
        msg_row = self.height - 1
        screen.set_line(
            msg_row,
            f" {self.state.message}",
        )

        return screen


# ── Shell registration ────────────────────────────────────────────────


def register_fsbrowse_program(registry: ProgramRegistry) -> None:
    registry.register_fn(
        "fsbrowse",
        _run_fsbrowse,
        "File browser — navigate the virtual filesystem\n\n"
        "Usage: fsbrowse [<path>]\n\n"
        "Two-pane file browser with directory tree and preview.\n\n"
        "Keys:\n"
        "  Up/Down    Navigate entries\n"
        "  Enter      Open directory / preview file\n"
        "  Backspace  Go to parent directory\n"
        "  e          Open file in neon-edit\n"
        "  q          Quit",
    )


async def _run_fsbrowse(ctx: ProgramContext) -> int:
    if ctx.run_tui is None:
        ctx.stderr.error("fsbrowse: requires a terminal that supports TUI mode")
        return 1

    # Determine starting directory
    start_id = ctx.cwd_id
    args = ctx.args[1:]
    if args:
        try:
            node = ctx.resolve_path(args[0])
            if node.type == "directory":
                start_id = node.id
            else:
                # If a file was given, open in its parent directory
                if node.parent_id:
                    start_id = node.parent_id
        except (FileNotFoundError, NotADirectoryError) as exc:
            ctx.stderr.error(f"fsbrowse: {exc}")
            return 1

    app = FsBrowseApp(
        app_service=ctx.services.app_service,
        start_dir_id=start_id,
    )
    return await ctx.run_tui(app)
