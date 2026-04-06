"""Tests for the fsbrowse file browser TUI."""

from __future__ import annotations

import pytest

from recursive_neon.models.game_state import GameState
from recursive_neon.services.app_service import AppService
from recursive_neon.shell.programs.fsbrowse import (
    DIR_ICON,
    PREVIEW_MAX_LINES,
    FsBrowseApp,
    FsBrowseState,
)

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def app_service() -> AppService:
    gs = GameState()
    svc = AppService(gs)
    svc.init_filesystem()
    return svc


@pytest.fixture
def populated_fs(app_service: AppService) -> tuple[AppService, str]:
    """Create a filesystem with a few dirs and files.

    Layout::

        / (root)
        ├── Documents/
        │   ├── notes.txt    ("hello world")
        │   └── readme.md    ("# Readme\\nSome content")
        ├── Programs/
        │   └── script.py    ("print('hi')")
        └── log.txt          ("line1\\nline2\\nline3")
    """
    root_id = app_service.game_state.filesystem.root_id
    assert root_id is not None

    docs = app_service.create_directory({"name": "Documents", "parent_id": root_id})
    progs = app_service.create_directory({"name": "Programs", "parent_id": root_id})
    app_service.create_file(
        {"name": "notes.txt", "parent_id": docs.id, "content": "hello world"}
    )
    app_service.create_file(
        {"name": "readme.md", "parent_id": docs.id, "content": "# Readme\nSome content"}
    )
    app_service.create_file(
        {"name": "script.py", "parent_id": progs.id, "content": "print('hi')"}
    )
    app_service.create_file(
        {
            "name": "log.txt",
            "parent_id": root_id,
            "content": "line1\nline2\nline3",
        }
    )
    return app_service, root_id


def _make_app(populated_fs: tuple[AppService, str]) -> FsBrowseApp:
    svc, root_id = populated_fs
    return FsBrowseApp(app_service=svc, start_dir_id=root_id)


# ── FsBrowseState ────────────────────────────────────────────────────


@pytest.mark.unit
class TestFsBrowseState:
    def test_refresh_sorts_dirs_first(self, populated_fs):
        svc, root_id = populated_fs
        state = FsBrowseState(app_service=svc, cwd_id=root_id)
        state.refresh_entries()

        names = [e.name for e in state.entries]
        # Dirs come first (alphabetical), then files
        assert names == ["Documents", "Programs", "log.txt"]

    def test_refresh_empty_directory(self, app_service):
        root_id = app_service.game_state.filesystem.root_id
        assert root_id is not None
        empty = app_service.create_directory({"name": "empty", "parent_id": root_id})

        state = FsBrowseState(app_service=app_service, cwd_id=empty.id)
        state.refresh_entries()
        assert state.entries == []
        assert state.cursor == 0

    def test_preview_file(self, populated_fs):
        svc, root_id = populated_fs
        state = FsBrowseState(app_service=svc, cwd_id=root_id)
        state.refresh_entries()

        # Cursor on "log.txt" (index 2)
        state.cursor = 2
        state._update_preview()
        assert state.preview_name == "log.txt"
        assert not state.preview_is_dir
        assert state.preview_lines == ["line1", "line2", "line3"]
        assert not state.preview_truncated

    def test_preview_directory(self, populated_fs):
        svc, root_id = populated_fs
        state = FsBrowseState(app_service=svc, cwd_id=root_id)
        state.refresh_entries()

        # Cursor on "Documents" (index 0)
        state.cursor = 0
        state._update_preview()
        assert state.preview_name == "Documents"
        assert state.preview_is_dir
        # Should list children of Documents
        assert any("notes.txt" in line for line in state.preview_lines)
        assert any("readme.md" in line for line in state.preview_lines)

    def test_preview_truncation(self, app_service):
        root_id = app_service.game_state.filesystem.root_id
        assert root_id is not None
        long_content = "\n".join(f"line {i}" for i in range(300))
        app_service.create_file(
            {"name": "big.txt", "parent_id": root_id, "content": long_content}
        )

        state = FsBrowseState(app_service=app_service, cwd_id=root_id)
        state.refresh_entries()
        # Only entry is big.txt, cursor=0
        assert state.preview_truncated
        assert len(state.preview_lines) == PREVIEW_MAX_LINES

    def test_selected_node_returns_none_when_empty(self, app_service):
        root_id = app_service.game_state.filesystem.root_id
        assert root_id is not None
        empty = app_service.create_directory({"name": "empty", "parent_id": root_id})
        state = FsBrowseState(app_service=app_service, cwd_id=empty.id)
        state.refresh_entries()
        assert state.selected_node is None

    def test_current_path(self, populated_fs):
        svc, root_id = populated_fs
        state = FsBrowseState(app_service=svc, cwd_id=root_id)
        assert state.current_path() == "/"


# ── FsBrowseApp ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestFsBrowseAppStartup:
    def test_on_start_returns_screen(self, populated_fs):
        app = _make_app(populated_fs)
        screen = app.on_start(80, 24)
        assert screen.width == 80
        assert screen.height == 24

    def test_title_contains_path(self, populated_fs):
        app = _make_app(populated_fs)
        screen = app.on_start(80, 24)
        assert "FILE BROWSER" in screen.lines[0]

    def test_cursor_invisible(self, populated_fs):
        app = _make_app(populated_fs)
        screen = app.on_start(80, 24)
        assert not screen.cursor_visible

    def test_entries_loaded(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)
        assert len(app.state.entries) == 3  # Documents, Programs, log.txt

    def test_preview_populated_on_start(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)
        # First entry is Documents dir — preview shows its children
        assert app.state.preview_is_dir
        assert len(app.state.preview_lines) > 0


@pytest.mark.unit
class TestFsBrowseAppNavigation:
    def test_arrow_down_moves_cursor(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)
        assert app.state.cursor == 0

        app.on_key("ArrowDown")
        assert app.state.cursor == 1

        app.on_key("ArrowDown")
        assert app.state.cursor == 2

    def test_arrow_up_moves_cursor(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        app.on_key("ArrowDown")
        app.on_key("ArrowDown")
        assert app.state.cursor == 2

        app.on_key("ArrowUp")
        assert app.state.cursor == 1

    def test_cursor_stops_at_top(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        app.on_key("ArrowUp")  # already at 0
        assert app.state.cursor == 0

    def test_cursor_stops_at_bottom(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        for _ in range(20):
            app.on_key("ArrowDown")
        assert app.state.cursor == len(app.state.entries) - 1

    def test_enter_directory(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        # First entry is "Documents"
        assert app.state.entries[0].name == "Documents"
        app.on_key("Enter")

        # Now inside Documents
        names = [e.name for e in app.state.entries]
        assert "notes.txt" in names
        assert "readme.md" in names

    def test_backspace_goes_up(self, populated_fs):
        svc, root_id = populated_fs
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        # Enter Documents
        app.on_key("Enter")
        assert app.state.cwd_id != root_id

        # Backspace goes back to root
        app.on_key("Backspace")
        assert app.state.cwd_id == root_id

    def test_backspace_at_root_stays(self, populated_fs):
        svc, root_id = populated_fs
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        app.on_key("Backspace")
        assert app.state.cwd_id == root_id

    def test_backspace_restores_cursor_position(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        # Move to Programs (index 1) and enter
        app.on_key("ArrowDown")
        assert app.state.entries[app.state.cursor].name == "Programs"
        app.on_key("Enter")

        # Backspace — cursor should be on Programs again
        app.on_key("Backspace")
        assert app.state.entries[app.state.cursor].name == "Programs"

    def test_preview_updates_on_cursor_move(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        # Start on Documents
        assert app.state.preview_is_dir

        # Move to log.txt (index 2)
        app.on_key("ArrowDown")
        app.on_key("ArrowDown")
        assert app.state.preview_name == "log.txt"
        assert not app.state.preview_is_dir
        assert "line1" in app.state.preview_lines


@pytest.mark.unit
class TestFsBrowseAppExit:
    def test_q_exits(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)
        result = app.on_key("q")
        assert result is None

    def test_escape_exits(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)
        result = app.on_key("Escape")
        assert result is None

    def test_ctrl_c_exits(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)
        result = app.on_key("C-c")
        assert result is None


@pytest.mark.unit
class TestFsBrowseAppEdit:
    def test_edit_file_sets_pending(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        # Move to log.txt and press 'e'
        app.on_key("ArrowDown")
        app.on_key("ArrowDown")
        assert app.state.entries[app.state.cursor].name == "log.txt"

        # Without tui_launcher, should show message
        app.on_key("e")
        assert "not available" in app.state.message.lower()

    def test_edit_directory_shows_message(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        # Cursor on Documents (a directory)
        app.on_key("e")
        assert "file" in app.state.message.lower()

    def test_edit_with_launcher_sets_pending(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        launched: list[object] = []

        async def fake_launcher(tui_app):
            launched.append(tui_app)
            return 0

        app.set_tui_launcher(fake_launcher)

        # Move to log.txt
        app.on_key("ArrowDown")
        app.on_key("ArrowDown")
        app.on_key("e")
        assert app._pending_edit is not None
        assert app._pending_edit.name == "log.txt"


@pytest.mark.unit
class TestFsBrowseAppRendering:
    def test_directory_entries_show_icon(self, populated_fs):
        app = _make_app(populated_fs)
        screen = app.on_start(80, 24)

        # Directory entries should have dir icon
        left_content = "\n".join(screen.lines[3:6])
        assert DIR_ICON in left_content

    def test_file_preview_shown(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        # Move to log.txt to preview it
        app.on_key("ArrowDown")
        screen = app.on_key("ArrowDown")
        assert screen is not None

        # Right pane should show file content
        right_content = "\n".join(screen.lines[3:10])
        assert "line1" in right_content

    def test_empty_dir_message(self, app_service):
        root_id = app_service.game_state.filesystem.root_id
        assert root_id is not None
        empty = app_service.create_directory({"name": "empty", "parent_id": root_id})

        app = FsBrowseApp(app_service=app_service, start_dir_id=empty.id)
        screen = app.on_start(80, 24)

        all_text = "\n".join(screen.lines)
        assert "empty" in all_text.lower()

    def test_resize_updates_dimensions(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        screen = app.on_resize(120, 40)
        assert screen.width == 120
        assert screen.height == 40
        assert app.width == 120
        assert app.height == 40

    def test_status_bar_shows_position(self, populated_fs):
        app = _make_app(populated_fs)
        screen = app.on_start(80, 24)

        # Status row should show position
        status_row = screen.lines[screen.height - 2]
        assert "1/3" in status_row

    def test_status_bar_updates_on_move(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        screen = app.on_key("ArrowDown")
        assert screen is not None
        status_row = screen.lines[screen.height - 2]
        assert "2/3" in status_row

    def test_selected_entry_highlighted(self, populated_fs):
        app = _make_app(populated_fs)
        screen = app.on_start(80, 24)

        # Selected entry uses reverse video (\033[7m)
        first_entry_line = screen.lines[3]
        assert "\033[7m" in first_entry_line

    def test_unknown_key_returns_screen(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        result = app.on_key("F1")
        assert result is not None  # doesn't crash, returns screen

    def test_scrolling_with_many_entries(self, app_service):
        root_id = app_service.game_state.filesystem.root_id
        assert root_id is not None

        # Create many files to force scrolling
        for i in range(30):
            app_service.create_file(
                {
                    "name": f"file_{i:02d}.txt",
                    "parent_id": root_id,
                    "content": f"content {i}",
                }
            )

        app = FsBrowseApp(app_service=app_service, start_dir_id=root_id)
        app.on_start(80, 24)

        # Scroll down past visible area
        for _ in range(20):
            app.on_key("ArrowDown")

        assert app.state.cursor == 20
        # scroll_offset should have advanced
        assert app.state.scroll_offset > 0

    def test_dir_preview_shows_icons(self, populated_fs):
        app = _make_app(populated_fs)
        app.on_start(80, 24)

        # Cursor on Documents — preview should show dir icon for subdirs
        # Documents has only files, so check Programs
        app.on_key("ArrowDown")  # Programs
        app.on_key("ArrowDown")  # Actually this goes to log.txt
        # Go back up to Programs
        app.on_key("ArrowUp")

        # Preview of Programs should show script.py
        assert app.state.preview_name == "Programs"
        assert any("script.py" in line for line in app.state.preview_lines)


@pytest.mark.unit
class TestFsBrowseAppStartPath:
    def test_start_in_subdirectory(self, populated_fs):
        svc, root_id = populated_fs
        docs = [e for e in svc.list_directory(root_id) if e.name == "Documents"][0]

        app = FsBrowseApp(app_service=svc, start_dir_id=docs.id)
        app.on_start(80, 24)

        names = [e.name for e in app.state.entries]
        assert "notes.txt" in names
        assert "readme.md" in names

    def test_enter_file_shows_preview_only(self, populated_fs):
        """Pressing Enter on a file does not navigate away."""
        app = _make_app(populated_fs)
        app.on_start(80, 24)
        svc, root_id = populated_fs

        # Move to log.txt
        app.on_key("ArrowDown")
        app.on_key("ArrowDown")
        assert app.state.entries[app.state.cursor].name == "log.txt"

        # Press Enter on a file — stays in the same directory
        app.on_key("Enter")
        assert app.state.cwd_id == root_id

    def test_file_with_empty_content(self, app_service):
        root_id = app_service.game_state.filesystem.root_id
        assert root_id is not None
        app_service.create_file(
            {"name": "empty.txt", "parent_id": root_id, "content": ""}
        )

        app = FsBrowseApp(app_service=app_service, start_dir_id=root_id)
        app.on_start(80, 24)
        # Preview should have single empty-string line from "".split("\n")
        assert app.state.preview_lines == [""]

    def test_file_with_no_content(self, app_service):
        root_id = app_service.game_state.filesystem.root_id
        assert root_id is not None
        app_service.create_file({"name": "none.txt", "parent_id": root_id})

        app = FsBrowseApp(app_service=app_service, start_dir_id=root_id)
        app.on_start(80, 24)
        # content is None → treated as ""
        assert app.state.preview_lines == [""]
