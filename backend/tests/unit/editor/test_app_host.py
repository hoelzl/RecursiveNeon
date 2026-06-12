"""Tests for the TuiApp window host (editor/app_host.py).

Hosted apps are ours, not Emacs's, so there is no parity scenario —
these tests are the ground truth. The C-c escape-prefix conventions
follow GNU Emacs 29.3 term char mode (probed 2026-06-12): C-c <key>
runs the C-x binding, C-c C-c sends a literal C-c.
"""

from __future__ import annotations

from recursive_neon.shell.tui import ScreenBuffer

from .harness import EditorHarness, make_harness


class FakeApp:
    """Scriptable TuiApp: records lifecycle calls, renders its state."""

    def __init__(self, tick_interval_ms: int = 0) -> None:
        self.tick_interval_ms = tick_interval_ms
        self.keys: list[str] = []
        self.resizes: list[tuple[int, int]] = []
        self.ticks: list[int] = []
        self.size = (0, 0)
        self.tick_screen: ScreenBuffer | None = None

    def _screen(self, body: str) -> ScreenBuffer:
        w, h = self.size
        s = ScreenBuffer.create(w, h)
        s.set_line(0, body)
        s.cursor_row, s.cursor_col = 0, len(body)
        return s

    def on_start(self, width: int, height: int) -> ScreenBuffer:
        self.size = (width, height)
        return self._screen(f"START {width}x{height}")

    def on_key(self, key: str) -> ScreenBuffer | None:
        self.keys.append(key)
        if key == "Q":
            return None
        if key == "!":
            raise RuntimeError("boom")
        return self._screen(f"KEY {key}")

    def on_resize(self, width: int, height: int) -> ScreenBuffer:
        self.size = (width, height)
        self.resizes.append((width, height))
        return self._screen(f"RESIZE {width}x{height}")

    def on_tick(self, dt_ms: int) -> ScreenBuffer | None:
        self.ticks.append(dt_ms)
        return self.tick_screen


def make_host_harness(
    app: FakeApp | None = None,
) -> tuple[EditorHarness, FakeApp]:
    h = make_harness("start text\n", width=80, height=24)
    h.editor.buffer.name = "start.txt"
    fake = app or FakeApp()
    h.editor.tui_app_factories = {"codebreaker": lambda: fake}
    return h, fake


def launch(h: EditorHarness) -> None:
    h.send_keys("M-x")
    h.type_string("codebreaker")
    h.send_keys("Enter")


class TestHostedBuffer:
    def test_mx_opens_hosted_buffer_at_window_size(self) -> None:
        h, app = make_host_harness()
        launch(h)
        assert h.editor.buffer.name == "*codebreaker*"
        # 24 rows - 1 message line - 1 modeline = 22 text rows.
        assert app.size == (80, 22)
        assert h.editor.buffer.lines[0] == "START 80x22"
        assert h.editor.buffer.read_only

    def test_modeline_term_style(self) -> None:
        h, _ = make_host_harness()
        launch(h)
        ml = h.modeline()
        assert ml.startswith("-UUU:%*-  F1  *codebreaker*")
        assert "(TUI run)" in ml

    def test_unavailable_without_factories(self) -> None:
        h = make_harness("x", width=80, height=24)
        h.send_keys("M-x")
        h.type_string("codebreaker")
        h.send_keys("Enter")
        assert h.message_line().startswith("codebreaker not available in this context")

    def test_cursor_follows_app(self) -> None:
        h, _ = make_host_harness()
        launch(h)
        assert h.point() == (0, len("START 80x22"))

    def test_ansi_runs_become_attrs(self) -> None:
        class ColorApp(FakeApp):
            def on_start(self, width: int, height: int) -> ScreenBuffer:
                self.size = (width, height)
                s = ScreenBuffer.create(width, height)
                s.set_line(0, "\033[31mred\033[0m plain")
                return s

        h, _ = make_host_harness(ColorApp())
        launch(h)
        buf = h.editor.buffer
        assert buf.lines[0] == "red plain"  # ANSI stripped from text
        assert buf._line_attrs is not None
        assert buf._line_attrs[0][0] is not None  # "r" carries the colour
        assert buf._line_attrs[0][4] is None  # "p" is default


class TestKeyRouting:
    def test_keys_forward_to_app(self) -> None:
        h, app = make_host_harness()
        launch(h)
        h.send_keys("a", "Escape", "C-n", "Enter")
        assert app.keys == ["a", "Escape", "C-n", "Enter"]
        assert h.editor.buffer.lines[0] == "KEY Enter"

    def test_cc_prefix_runs_cx_bindings(self) -> None:
        h, app = make_host_harness()
        launch(h)
        h.send_keys("C-c", "2")  # like C-x 2: split below (same buffer)
        assert not h.editor._window_tree.is_single()
        h.send_keys("C-c", "o")  # like C-x o: select other window
        # Both windows show the hosted buffer — keys are still captured
        # (Emacs term: any selected window on the term buffer is live).
        h.send_keys("C-c", "b")  # show start.txt in this window instead
        h.type_string("start.txt")
        h.send_keys("Enter")
        assert h.editor.buffer.name == "start.txt"
        # Keys in the unhosted window are NOT captured.
        h.send_keys("z")
        assert "z" not in app.keys
        # Back in the hosted window, capture resumes.
        h.send_keys("C-x", "o")
        assert h.editor.buffer.name == "*codebreaker*"
        h.send_keys("y")
        assert app.keys[-1] == "y"

    def test_cc_cc_sends_literal(self) -> None:
        h, app = make_host_harness()
        launch(h)
        h.send_keys("C-c", "C-c")
        assert app.keys == ["C-c"]

    def test_cc_prefix_shows_pending_message(self) -> None:
        h, _ = make_host_harness()
        launch(h)
        h.send_keys("C-c")
        assert h.message_line().startswith("C-c-")

    def test_cc_b_routes_to_minibuffer(self) -> None:
        h, app = make_host_harness()
        launch(h)
        h.send_keys("C-c", "b")
        assert h.editor.minibuffer is not None
        h.type_string("start.txt")
        h.send_keys("Enter")
        assert h.editor.buffer.name == "start.txt"
        assert app.keys == []  # nothing leaked to the app

    def test_cc_undefined_key_messages(self) -> None:
        h, app = make_host_harness()
        launch(h)
        h.send_keys("C-c", "@")
        assert "C-c @ is undefined" in h.message_line()
        assert app.keys == []

    def test_cc_cg_quits(self) -> None:
        h, app = make_host_harness()
        launch(h)
        h.send_keys("C-c", "C-g")
        assert h.message_line().startswith("Quit")
        assert app.keys == []


class TestLifecycle:
    def test_exit_finishes_and_keeps_screen(self) -> None:
        h, app = make_host_harness()
        launch(h)
        h.send_keys("x", "Q")
        assert h.message_line().startswith("[Process codebreaker finished]")
        assert h.editor.buffer.lines[0] == "KEY x"  # final screen kept
        # Keys are no longer captured; q quits back to start.txt.
        h.send_keys("q")
        assert h.editor.buffer.name == "start.txt"
        assert app.keys == ["x", "Q"]

    def test_mx_after_finish_restarts_in_place(self) -> None:
        h, app = make_host_harness()
        launch(h)
        h.send_keys("Q")
        fresh = FakeApp()
        h.editor.tui_app_factories = {"codebreaker": lambda: fresh}
        launch(h)
        assert h.editor.buffer.name == "*codebreaker*"
        assert h.editor.buffer.lines[0] == "START 80x22"
        state = h.editor.buffer._app_host_state
        assert state.app is fresh and not state.finished

    def test_mx_while_running_switches_back(self) -> None:
        h, app = make_host_harness()
        launch(h)
        h.send_keys("C-c", "b")
        h.type_string("start.txt")
        h.send_keys("Enter")
        launch(h)
        assert h.editor.buffer.name == "*codebreaker*"
        # Same instance — on_start ran only once.
        assert h.editor.buffer._app_host_state.app is app
        assert h.editor.buffer.lines[0] == "START 80x22"

    def test_app_crash_finishes_with_message(self) -> None:
        h, app = make_host_harness()
        launch(h)
        h.send_keys("!")
        assert "Error in codebreaker: boom" in h.message_line()
        assert h.editor.buffer._app_host_state.finished


class TestResizeAndTicks:
    def test_split_resizes_app_to_window(self) -> None:
        h, app = make_host_harness()
        launch(h)
        h.send_keys("C-c", "2")
        # 23 rows for windows; top window gets 12 incl. modeline → 11 text.
        assert app.resizes, "split did not trigger on_resize"
        w, hh = app.resizes[-1]
        assert w == 80 and hh < 22
        assert h.editor.buffer.lines[0] == f"RESIZE {w}x{hh}"

    def test_tick_interval_follows_hosted_app(self) -> None:
        h, app = make_host_harness(FakeApp(tick_interval_ms=250))
        assert h.view.tick_interval_ms == 0
        launch(h)
        assert h.view.tick_interval_ms == 250
        h.send_keys("Q")  # finished → no more ticks
        assert h.view.tick_interval_ms == 0

    def test_on_tick_blits_new_screens(self) -> None:
        app = FakeApp(tick_interval_ms=100)
        h, _ = make_host_harness(app)
        launch(h)
        assert h.view.on_tick(100) is None  # app returned None: no change
        tick = ScreenBuffer.create(*app.size)
        tick.set_line(0, "TICKED")
        app.tick_screen = tick
        assert h.view.on_tick(100) is not None
        assert h.editor.buffer.lines[0] == "TICKED"
        assert app.ticks == [100, 100]

    def test_ticks_continue_in_unselected_window(self) -> None:
        app = FakeApp(tick_interval_ms=100)
        h, _ = make_host_harness(app)
        launch(h)
        # Split, select the bottom window, and show start.txt there so
        # the hosted app is visible only in the unselected top window.
        h.send_keys("C-c", "2", "C-c", "o", "C-c", "b")
        h.type_string("start.txt")
        h.send_keys("Enter")
        assert h.editor.buffer.name == "start.txt"
        tick = ScreenBuffer.create(*app.size)
        tick.set_line(0, "BACKGROUND")
        app.tick_screen = tick
        assert h.view.on_tick(100) is not None
        hosted = next(b for b in h.editor.buffers if b.name == "*codebreaker*")
        assert hosted.lines[0] == "BACKGROUND"
