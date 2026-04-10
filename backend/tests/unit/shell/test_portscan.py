"""Tests for the portscan minigame TUI."""

from __future__ import annotations

import pytest

from recursive_neon.shell.programs.portscan import (
    GRID_COLS,
    LOCKOUT_DURATION_MS,
    MAX_ATTEMPTS,
    MAX_SCANS,
    NUM_OPEN,
    NUM_PORTS,
    Phase,
    PortScanApp,
    PortScanState,
    PortType,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _known_types() -> list[PortType]:
    """A deterministic port layout for testing.

    Layout (ports 1-12)::

        OPEN  CLOSED CLOSED DECOY
        CLOSED OPEN  DECOY  CLOSED
        CLOSED CLOSED OPEN  CLOSED

    Open ports: 1, 6, 11 → answer = [1, 6, 11]
    """
    return [
        PortType.OPEN,
        PortType.CLOSED,
        PortType.CLOSED,
        PortType.DECOY,
        PortType.CLOSED,
        PortType.OPEN,
        PortType.DECOY,
        PortType.CLOSED,
        PortType.CLOSED,
        PortType.CLOSED,
        PortType.OPEN,
        PortType.CLOSED,
    ]


def _make_app() -> PortScanApp:
    state = PortScanState.from_types(_known_types())
    return PortScanApp(state=state)


def _enter_sequence(app: PortScanApp, ports: list[int]) -> None:
    """Type a sequence of port numbers into the entry slots."""
    s = app.state
    for i, port_num in enumerate(ports):
        s.seq_cursor = i
        for ch in str(port_num):
            app.on_key(ch)


# ── PortScanState ────────────────────────────────────────────────────


@pytest.mark.unit
class TestPortScanState:
    def test_new_game_has_correct_counts(self):
        state = PortScanState.new_game()
        types = [p.port_type for p in state.ports]
        assert types.count(PortType.OPEN) == NUM_OPEN
        assert len(state.ports) == NUM_PORTS
        assert len(state.answer) == NUM_OPEN

    def test_from_types_known_layout(self):
        state = PortScanState.from_types(_known_types())
        assert state.answer == [1, 6, 11]
        assert len(state.ports) == 12
        assert state.phase == Phase.SCANNING

    def test_answer_is_sorted(self):
        state = PortScanState.new_game()
        assert state.answer == sorted(state.answer)

    def test_initial_scans_and_attempts(self):
        state = PortScanState.new_game()
        assert state.scans_remaining == MAX_SCANS
        assert state.attempts_remaining == MAX_ATTEMPTS

    def test_sequence_slots_match_open_count(self):
        state = PortScanState.new_game()
        assert len(state.sequence_slots) == NUM_OPEN

    def test_from_types_custom_open_count(self):
        """from_types with different number of open ports."""
        types = [PortType.OPEN, PortType.OPEN, PortType.CLOSED, PortType.CLOSED]
        state = PortScanState.from_types(types)
        assert state.answer == [1, 2]
        assert len(state.sequence_slots) == 2


# ── PortScanApp startup ─────────────────────────────────────────────


@pytest.mark.unit
class TestPortScanAppStartup:
    def test_on_start_returns_screen(self):
        app = _make_app()
        screen = app.on_start(80, 24)
        assert screen.width == 80
        assert screen.height == 24

    def test_title_present(self):
        app = _make_app()
        screen = app.on_start(80, 24)
        assert "PORT SCANNER" in screen.lines[0]

    def test_cursor_invisible(self):
        app = _make_app()
        screen = app.on_start(80, 24)
        assert not screen.cursor_visible

    def test_ports_displayed(self):
        app = _make_app()
        screen = app.on_start(80, 24)
        all_text = "\n".join(screen.lines)
        # Port numbers should appear in the grid
        assert "01" in all_text
        assert "12" in all_text


# ── Scanning phase ───────────────────────────────────────────────────


@pytest.mark.unit
class TestPortScanScanning:
    def test_arrow_moves_cursor(self):
        app = _make_app()
        app.on_start(80, 24)
        assert app.state.cursor == 0

        app.on_key("ArrowRight")
        assert app.state.cursor == 1

        app.on_key("ArrowDown")
        assert app.state.cursor == 1 + GRID_COLS

        app.on_key("ArrowLeft")
        assert app.state.cursor == GRID_COLS

        app.on_key("ArrowUp")
        assert app.state.cursor == 0

    def test_cursor_clamps_at_edges(self):
        app = _make_app()
        app.on_start(80, 24)

        app.on_key("ArrowLeft")  # already at col 0
        assert app.state.cursor == 0

        app.on_key("ArrowUp")  # already at row 0
        assert app.state.cursor == 0

        # Move to bottom-right
        for _ in range(20):
            app.on_key("ArrowRight")
        for _ in range(20):
            app.on_key("ArrowDown")
        assert app.state.cursor == NUM_PORTS - 1

    def test_scan_reveals_port(self):
        app = _make_app()
        app.on_start(80, 24)

        assert not app.state.ports[0].scanned
        app.on_key("Enter")  # scan port 1
        assert app.state.ports[0].scanned
        assert app.state.scans_remaining == MAX_SCANS - 1

    def test_scan_already_scanned(self):
        app = _make_app()
        app.on_start(80, 24)

        app.on_key("Enter")
        scans_after = app.state.scans_remaining
        app.on_key("Enter")  # scan same port again
        assert app.state.scans_remaining == scans_after  # no change
        assert "already" in app.state.message.lower()

    def test_scan_limit(self):
        app = _make_app()
        app.on_start(80, 24)

        for i in range(MAX_SCANS):
            app.state.cursor = i
            app.on_key("Enter")

        assert app.state.scans_remaining == 0
        # Try one more
        app.state.cursor = MAX_SCANS
        app.on_key("Enter")
        assert not app.state.ports[MAX_SCANS].scanned
        assert "no scans" in app.state.message.lower()

    def test_space_also_scans(self):
        app = _make_app()
        app.on_start(80, 24)
        app.on_key(" ")
        assert app.state.ports[0].scanned

    def test_scanned_port_shows_type(self):
        app = _make_app()
        app.on_start(80, 24)

        app.on_key("Enter")  # port 1 is OPEN
        screen = app.on_key("ArrowRight")  # just to re-render
        assert screen is not None
        # Check the actual grid row (row 3) contains the OPEN label,
        # not just the legend or message area.
        grid_row = screen.lines[3]
        assert "OPEN" in grid_row

    def test_tab_switches_to_sequence(self):
        app = _make_app()
        app.on_start(80, 24)

        # Must scan at least one port first
        app.on_key("Enter")
        app.on_key("Tab")
        assert app.state.phase == Phase.SEQUENCE

    def test_tab_blocked_without_scans(self):
        app = _make_app()
        app.on_start(80, 24)

        app.on_key("Tab")
        assert app.state.phase == Phase.SCANNING

    def test_q_exits(self):
        app = _make_app()
        app.on_start(80, 24)
        result = app.on_key("q")
        assert result is None


# ── Sequence entry ───────────────────────────────────────────────────


@pytest.mark.unit
class TestPortScanSequence:
    def _to_sequence(self, app: PortScanApp) -> None:
        """Scan one port and switch to sequence mode."""
        app.on_start(80, 24)
        app.on_key("Enter")  # scan
        app.on_key("Tab")  # switch

    def test_digit_entry(self):
        app = _make_app()
        self._to_sequence(app)

        app.on_key("5")
        assert app.state.sequence_slots[0] == 5
        # Auto-advance
        assert app.state.seq_cursor == 1

    def test_two_digit_entry(self):
        app = _make_app()
        self._to_sequence(app)

        app.on_key("1")  # slot 0 = 1, auto-advance to slot 1
        # Go back to slot 0 to make it two digits
        app.on_key("ArrowLeft")
        app.on_key("1")  # slot 0 = 11
        assert app.state.sequence_slots[0] == 11

    def test_backspace_clears_slot(self):
        app = _make_app()
        self._to_sequence(app)

        app.on_key("5")
        app.on_key("ArrowLeft")
        app.on_key("Backspace")
        assert app.state.sequence_slots[0] is None

    def test_tab_back_to_scanning(self):
        app = _make_app()
        self._to_sequence(app)

        app.on_key("Tab")
        assert app.state.phase == Phase.SCANNING

    def test_submit_incomplete_shows_message(self):
        app = _make_app()
        self._to_sequence(app)

        app.on_key("Enter")  # all slots empty
        assert "fill" in app.state.message.lower()

    def test_correct_sequence_wins(self):
        app = _make_app()
        self._to_sequence(app)

        _enter_sequence(app, [1, 6, 11])
        app.on_key("Enter")

        assert app.state.phase == Phase.WON
        assert "GRANTED" in app.state.message

    def test_wrong_sequence_triggers_lockout(self):
        app = _make_app()
        self._to_sequence(app)

        _enter_sequence(app, [2, 3, 4])
        app.on_key("Enter")

        assert app.state.phase == Phase.LOCKOUT
        assert app.state.lockout_remaining_ms == LOCKOUT_DURATION_MS
        assert app.state.attempts_remaining == MAX_ATTEMPTS - 1

    def test_wrong_sequence_resets_slots(self):
        app = _make_app()
        self._to_sequence(app)

        _enter_sequence(app, [2, 3, 4])
        app.on_key("Enter")

        assert all(v is None for v in app.state.sequence_slots)

    def test_out_of_range_rejected(self):
        app = _make_app()
        self._to_sequence(app)

        # Try to enter port 99 (>12)
        app.on_key("9")  # slot 0 = 9, auto advance
        app.on_key("ArrowLeft")  # back to slot 0
        app.on_key("9")  # would be 99, rejected
        assert app.state.sequence_slots[0] == 9  # unchanged


# ── Lockout + on_tick ────────────────────────────────────────────────


@pytest.mark.unit
class TestPortScanLockout:
    def _to_lockout(self, app: PortScanApp) -> None:
        """Get the app into lockout state."""
        app.on_start(80, 24)
        app.on_key("Enter")  # scan
        app.on_key("Tab")  # sequence mode
        _enter_sequence(app, [2, 3, 4])  # wrong
        app.on_key("Enter")

    def test_lockout_tick_decrements(self):
        app = _make_app()
        self._to_lockout(app)

        assert app.state.phase == Phase.LOCKOUT
        screen = app.on_tick(1000)
        assert screen is not None
        assert app.state.lockout_remaining_ms == LOCKOUT_DURATION_MS - 1000

    def test_lockout_expires_to_sequence(self):
        app = _make_app()
        self._to_lockout(app)

        app.on_tick(LOCKOUT_DURATION_MS)
        assert app.state.phase == Phase.SEQUENCE
        assert app.state.lockout_remaining_ms == 0

    def test_lockout_ignores_keys(self):
        app = _make_app()
        self._to_lockout(app)

        # Keys during lockout should not crash or change phase
        result = app.on_key("Enter")
        assert result is not None
        assert app.state.phase == Phase.LOCKOUT

    def test_tick_outside_lockout_returns_none(self):
        app = _make_app()
        app.on_start(80, 24)
        result = app.on_tick(100)
        assert result is None

    def test_lockout_countdown_renders(self):
        app = _make_app()
        self._to_lockout(app)

        screen = app.on_tick(1000)
        assert screen is not None
        all_text = "\n".join(screen.lines)
        assert "LOCKOUT" in all_text

    def test_three_wrong_guesses_loses(self):
        app = _make_app()
        app.on_start(80, 24)
        app.on_key("Enter")  # scan
        app.on_key("Tab")

        for _ in range(MAX_ATTEMPTS - 1):
            _enter_sequence(app, [2, 3, 4])
            app.on_key("Enter")
            # Wait out lockout
            app.on_tick(LOCKOUT_DURATION_MS)

        # Final wrong guess
        _enter_sequence(app, [2, 3, 4])
        app.on_key("Enter")

        assert app.state.phase == Phase.LOST
        assert "LOCKOUT" in app.state.message


# ── Won / Lost end states ───────────────────────────────────────────


@pytest.mark.unit
class TestPortScanEndStates:
    def test_new_game_after_win(self):
        app = _make_app()
        app.on_start(80, 24)
        app.on_key("Enter")
        app.on_key("Tab")
        _enter_sequence(app, [1, 6, 11])
        app.on_key("Enter")
        assert app.state.phase == Phase.WON

        app.on_key("Enter")  # new game
        assert app.state.phase == Phase.SCANNING
        assert app.state.scans_remaining == MAX_SCANS

    def test_new_game_after_loss(self):
        app = _make_app()
        app.on_start(80, 24)
        app.on_key("Enter")
        app.on_key("Tab")

        for _ in range(MAX_ATTEMPTS - 1):
            _enter_sequence(app, [2, 3, 4])
            app.on_key("Enter")
            app.on_tick(LOCKOUT_DURATION_MS)

        _enter_sequence(app, [2, 3, 4])
        app.on_key("Enter")
        assert app.state.phase == Phase.LOST

        app.on_key("Enter")  # new game
        assert app.state.phase == Phase.SCANNING

    def test_quit_from_won(self):
        app = _make_app()
        app.on_start(80, 24)
        app.on_key("Enter")
        app.on_key("Tab")
        _enter_sequence(app, [1, 6, 11])
        app.on_key("Enter")

        result = app.on_key("q")
        assert result is None

    def test_ctrl_c_exits_from_any_phase(self):
        app = _make_app()
        app.on_start(80, 24)
        assert app.on_key("C-c") is None

    def test_escape_exits_from_won(self):
        app = _make_app()
        app.on_start(80, 24)
        app.on_key("Enter")
        app.on_key("Tab")
        _enter_sequence(app, [1, 6, 11])
        app.on_key("Enter")

        result = app.on_key("Escape")
        assert result is None


# ── Rendering ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPortScanRendering:
    def test_resize_updates(self):
        app = _make_app()
        app.on_start(80, 24)
        screen = app.on_resize(120, 40)
        assert screen.width == 120
        assert screen.height == 40

    def test_legend_visible(self):
        app = _make_app()
        screen = app.on_start(80, 24)
        all_text = "\n".join(screen.lines)
        assert "OPEN" in all_text
        assert "SHUT" in all_text
        assert "TRAP" in all_text

    def test_unknown_key_returns_screen(self):
        app = _make_app()
        app.on_start(80, 24)
        result = app.on_key("F1")
        assert result is not None

    def test_win_screen_shows_granted(self):
        app = _make_app()
        app.on_start(80, 24)
        app.on_key("Enter")
        app.on_key("Tab")
        _enter_sequence(app, [1, 6, 11])
        screen = app.on_key("Enter")
        assert screen is not None
        all_text = "\n".join(screen.lines)
        assert "GRANTED" in all_text

    def test_loss_screen_shows_answer(self):
        app = _make_app()
        app.on_start(80, 24)
        app.on_key("Enter")
        app.on_key("Tab")

        for _ in range(MAX_ATTEMPTS - 1):
            _enter_sequence(app, [2, 3, 4])
            app.on_key("Enter")
            app.on_tick(LOCKOUT_DURATION_MS)

        _enter_sequence(app, [2, 3, 4])
        screen = app.on_key("Enter")
        assert screen is not None
        all_text = "\n".join(screen.lines)
        # Answer [1, 6, 11] should be revealed
        assert "1" in all_text
        assert "6" in all_text
        assert "11" in all_text

    def test_sequence_slots_render(self):
        app = _make_app()
        app.on_start(80, 24)
        app.on_key("Enter")
        app.on_key("Tab")
        screen = app.on_key("ArrowRight")  # just re-render in sequence mode
        assert screen is not None
        all_text = "\n".join(screen.lines)
        assert "Sequence" in all_text


# ── Additional coverage ─────────────────────────────────────────────


@pytest.mark.unit
class TestPortScanAdditional:
    def _to_sequence(self, app: PortScanApp) -> None:
        app.on_start(80, 24)
        app.on_key("Enter")
        app.on_key("Tab")

    def test_q_exits_from_sequence(self):
        app = _make_app()
        self._to_sequence(app)
        assert app.on_key("q") is None

    def test_escape_exits_from_sequence(self):
        app = _make_app()
        self._to_sequence(app)
        assert app.on_key("Escape") is None

    def test_correct_ports_wrong_order_wins(self):
        """Order-insensitive: [11, 1, 6] should win (answer is [1, 6, 11])."""
        app = _make_app()
        self._to_sequence(app)
        _enter_sequence(app, [11, 1, 6])
        app.on_key("Enter")
        assert app.state.phase == Phase.WON

    def test_duplicate_port_rejected_on_submit(self):
        """Submitting a sequence with duplicate port numbers is rejected."""
        app = _make_app()
        self._to_sequence(app)
        # Manually set duplicate slots (bypass digit entry)
        app.state.sequence_slots = [1, 1, 6]
        app.on_key("Enter")
        assert app.state.phase == Phase.SEQUENCE
        assert "once" in app.state.message.lower()

    def test_feedback_counts_unique_matches(self):
        """Wrong sequence feedback counts unique correct ports, not duplicates."""
        app = _make_app()
        self._to_sequence(app)
        # Enter [1, 2, 3] against answer [1, 6, 11] → 1/3 correct
        _enter_sequence(app, [1, 2, 3])
        app.on_key("Enter")
        assert app.state.phase == Phase.LOCKOUT
        assert "1/3" in app.state.message

    def test_scanned_port_type_in_grid_row(self):
        """Scanned port type label appears on the grid row, not just legend."""
        app = _make_app()
        app.on_start(80, 24)
        # Scan port 1 (OPEN) — grid row 3
        app.on_key("Enter")
        screen = app.on_key("ArrowRight")
        assert screen is not None
        # OPEN should be in the grid row (row 3), not just legend
        assert "OPEN" in screen.lines[3]

    def test_small_terminal(self):
        """Small terminal should not crash."""
        app = _make_app()
        screen = app.on_start(40, 12)
        assert screen is not None
