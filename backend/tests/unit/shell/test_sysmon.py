"""Tests for the sysmon TUI app."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from recursive_neon.models.process import ProcessTable
from recursive_neon.shell.programs.sysmon import SysMonApp, _format_uptime, _render_bar


# ── Helper rendering functions ───────────────────────────────────────


@pytest.mark.unit
class TestRenderBar:
    def test_zero(self):
        bar = _render_bar(0.0)
        assert "█" not in bar
        assert "░" in bar

    def test_full(self):
        bar = _render_bar(100.0)
        assert "░" not in bar
        assert "█" in bar

    def test_half(self):
        bar = _render_bar(50.0, width=10)
        # 50% of 10 = 5 filled
        assert bar.count("█") == 5
        assert bar.count("░") == 5

    def test_clamps_above_100(self):
        bar = _render_bar(150.0, width=10)
        assert bar.count("█") == 10

    def test_clamps_below_0(self):
        bar = _render_bar(-10.0, width=10)
        assert bar.count("█") == 0


@pytest.mark.unit
class TestFormatUptime:
    def test_seconds(self):
        now = datetime.now(tz=UTC)
        assert _format_uptime(now) == "00:00:00"

    def test_with_days(self):
        from datetime import timedelta

        start = datetime.now(tz=UTC) - timedelta(days=2, hours=3, minutes=15)
        result = _format_uptime(start)
        assert result.startswith("2d 03:15:")


# ── SysMonApp TUI ───────────────────────────────────────────────────


def _make_table() -> ProcessTable:
    """Create a small deterministic process table for tests."""
    t = ProcessTable()
    t.add("init", "root", 0.0, 0.1, "sleeping")
    t.add("sshd", "root", 0.5, 0.3, "sleeping", ["network"])
    t.add("postgres", "admin", 5.0, 10.0, "running", ["database"])
    t.add("watchdog", "root", 0.2, 0.1, "running", ["security"])
    return t


@pytest.mark.unit
class TestSysMonAppStartup:
    def test_on_start_returns_screen(self):
        app = SysMonApp(_make_table())
        screen = app.on_start(80, 24)
        assert screen is not None
        assert screen.width == 80
        assert screen.height == 24

    def test_title_present(self):
        app = SysMonApp(_make_table())
        screen = app.on_start(80, 24)
        assert any("SYSTEM MONITOR" in line for line in screen.lines)

    def test_processes_displayed(self):
        app = SysMonApp(_make_table())
        screen = app.on_start(80, 24)
        text = "\n".join(screen.lines)
        assert "init" in text
        assert "sshd" in text
        assert "postgres" in text
        assert "watchdog" in text

    def test_header_columns_present(self):
        app = SysMonApp(_make_table())
        screen = app.on_start(80, 24)
        text = "\n".join(screen.lines)
        assert "PID" in text
        assert "NAME" in text
        assert "CPU%" in text
        assert "MEM%" in text

    def test_cpu_bar_present(self):
        app = SysMonApp(_make_table())
        screen = app.on_start(80, 24)
        text = "\n".join(screen.lines)
        assert "CPU" in text
        assert "█" in text or "░" in text

    def test_cursor_hidden(self):
        app = SysMonApp(_make_table())
        screen = app.on_start(80, 24)
        assert screen.cursor_visible is False


@pytest.mark.unit
class TestSysMonAppKeys:
    def test_q_quits(self):
        app = SysMonApp(_make_table())
        app.on_start(80, 24)
        assert app.on_key("q") is None

    def test_escape_quits(self):
        app = SysMonApp(_make_table())
        app.on_start(80, 24)
        assert app.on_key("Escape") is None

    def test_ctrl_c_quits(self):
        app = SysMonApp(_make_table())
        app.on_start(80, 24)
        assert app.on_key("C-c") is None

    def test_unknown_key_returns_screen(self):
        app = SysMonApp(_make_table())
        app.on_start(80, 24)
        result = app.on_key("x")
        assert result is not None

    def test_resize(self):
        app = SysMonApp(_make_table())
        app.on_start(80, 24)
        screen = app.on_resize(120, 40)
        assert screen.width == 120
        assert screen.height == 40


@pytest.mark.unit
class TestSysMonAppSorting:
    def _get_process_order(self, app: SysMonApp) -> list[str]:
        """Extract process names from the rendered screen in display order."""
        screen = app.on_start(80, 30)
        # Find lines that contain process data (have a PID number)
        names = []
        table = _make_table()
        known_names = {p.name for p in table.list_all()}
        for line in screen.lines:
            for name in known_names:
                if name in line:
                    names.append(name)
                    break
        return names

    def test_default_sort_by_pid(self):
        app = SysMonApp(_make_table())
        names = self._get_process_order(app)
        assert names == ["init", "sshd", "postgres", "watchdog"]

    def test_sort_by_cpu(self):
        app = SysMonApp(_make_table())
        app.on_start(80, 30)
        app.on_key("c")
        assert app.sort_key == "cpu"

    def test_sort_by_memory(self):
        app = SysMonApp(_make_table())
        app.on_start(80, 30)
        app.on_key("m")
        assert app.sort_key == "mem"

    def test_sort_by_name(self):
        app = SysMonApp(_make_table())
        app.on_start(80, 30)
        app.on_key("n")
        assert app.sort_key == "name"

    def test_sort_by_pid(self):
        app = SysMonApp(_make_table())
        app.on_start(80, 30)
        app.on_key("c")  # change away from pid
        app.on_key("p")  # back to pid
        assert app.sort_key == "pid"

    def test_cpu_sort_order(self):
        app = SysMonApp(_make_table())
        app.sort_key = "cpu"
        procs = app._sorted_processes()
        cpus = [p.cpu for p in procs]
        assert cpus == sorted(cpus, reverse=True)

    def test_mem_sort_order(self):
        app = SysMonApp(_make_table())
        app.sort_key = "mem"
        procs = app._sorted_processes()
        mems = [p.memory for p in procs]
        assert mems == sorted(mems, reverse=True)

    def test_name_sort_order(self):
        app = SysMonApp(_make_table())
        app.sort_key = "name"
        procs = app._sorted_processes()
        names = [p.name.lower() for p in procs]
        assert names == sorted(names)


def _make_large_table() -> ProcessTable:
    """Create a table with more processes than fit on a small screen."""
    t = ProcessTable()
    for i in range(30):
        t.add(f"proc_{i:02d}", "root", cpu=float(i), memory=float(i * 0.5))
    return t


@pytest.mark.unit
class TestSysMonAppScrolling:
    def test_no_scroll_when_all_fit(self):
        """With few processes, scroll stays at 0."""
        app = SysMonApp(_make_table())
        app.on_start(80, 24)
        app.on_key("ArrowDown")
        # Render clamps back to 0 since all 4 processes fit
        assert app.scroll_offset == 0

    def test_scroll_down_when_overflow(self):
        app = SysMonApp(_make_large_table())
        app.on_start(80, 15)  # small screen, processes won't fit
        app.on_key("ArrowDown")
        assert app.scroll_offset > 0

    def test_scroll_up_at_top(self):
        app = SysMonApp(_make_table())
        app.on_start(80, 24)
        app.on_key("ArrowUp")
        assert app.scroll_offset == 0

    def test_scroll_clamped_to_max(self):
        app = SysMonApp(_make_large_table())
        app.on_start(80, 15)
        for _ in range(100):
            app.on_key("ArrowDown")
        # Should be clamped, not at 100
        assert app.scroll_offset < 100
        assert app.scroll_offset >= 0

    def test_sort_resets_scroll(self):
        app = SysMonApp(_make_large_table())
        app.on_start(80, 15)
        app.on_key("ArrowDown")
        app.on_key("ArrowDown")
        assert app.scroll_offset > 0
        app.on_key("c")
        assert app.scroll_offset == 0


@pytest.mark.unit
class TestSysMonShellRegistration:
    async def test_no_tui_shows_error(self, make_ctx, output):
        from recursive_neon.shell.programs.sysmon import _run_sysmon

        ctx = make_ctx(["sysmon"])
        assert await _run_sysmon(ctx) == 1
        assert "TUI" in output.error_text

    async def test_with_tui_launches_app(self, make_ctx, output, test_container):
        from recursive_neon.shell.programs.sysmon import _run_sysmon

        launched = {}

        async def mock_run_tui(view):
            launched["app"] = view
            return 0

        ctx = make_ctx(["sysmon"])
        ctx.run_tui = mock_run_tui
        assert await _run_sysmon(ctx) == 0
        assert "app" in launched
        assert isinstance(launched["app"], SysMonApp)
