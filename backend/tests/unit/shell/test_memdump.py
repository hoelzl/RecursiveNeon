"""Tests for the memdump minigame TUI."""

from __future__ import annotations

import random

import pytest

from recursive_neon.shell.programs.memdump import (
    BASE_ADDRESS,
    MAX_MOVES,
    MEM_SIZE,
    NUM_PATTERNS,
    PATTERN_POOL,
    MemDumpApp,
    MemDumpState,
    Phase,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _known_state() -> MemDumpState:
    """Create a deterministic game state for testing.

    Patterns:
        "ROOT" at offset 0x10
        "KEY"  at offset 0x30
        "EXEC" at offset 0x50
    """
    return MemDumpState.from_patterns(
        [("ROOT", 0x10), ("KEY", 0x30), ("EXEC", 0x50)],
        rng=random.Random(42),
    )


def _make_app() -> MemDumpApp:
    return MemDumpApp(state=_known_state())


# ── MemDumpState ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestMemDumpState:
    def test_new_game_has_correct_structure(self):
        state = MemDumpState.new_game()
        assert len(state.memory) == MEM_SIZE
        assert len(state.patterns) == NUM_PATTERNS
        assert state.phase == Phase.PLAYING
        assert state.moves_remaining == MAX_MOVES

    def test_patterns_from_pool(self):
        state = MemDumpState.new_game()
        for p in state.patterns:
            assert p.text in PATTERN_POOL

    def test_patterns_embedded_in_memory(self):
        state = MemDumpState.new_game()
        for p in state.patterns:
            encoded = p.text.encode("ascii")
            segment = state.memory[p.offset : p.offset + len(encoded)]
            assert segment == encoded

    def test_from_patterns_known(self):
        state = _known_state()
        assert len(state.patterns) == 3
        assert state.patterns[0].text == "ROOT"
        assert state.patterns[0].offset == 0x10
        assert state.memory[0x10 : 0x10 + 4] == b"ROOT"

    def test_found_count(self):
        state = _known_state()
        assert state.found_count == 0
        state.patterns[0].found = True
        assert state.found_count == 1

    def test_total_patterns(self):
        state = _known_state()
        assert state.total_patterns == 3

    def test_match_offsets_empty_search(self):
        state = _known_state()
        assert state.match_offsets() == []

    def test_match_offsets_finds_pattern(self):
        state = _known_state()
        state.search = "ROOT"
        offsets = state.match_offsets()
        assert 0x10 in offsets

    def test_match_offsets_partial(self):
        state = _known_state()
        state.search = "RO"
        offsets = state.match_offsets()
        assert 0x10 in offsets

    def test_pattern_offsets(self):
        state = _known_state()
        state.patterns[0].found = True  # ROOT at 0x10
        offsets = state.pattern_offsets()
        assert offsets == {0x10, 0x11, 0x12, 0x13}

    def test_no_pattern_overlap(self):
        """Patterns should not overlap with each other."""
        state = MemDumpState.new_game(rng=random.Random(99))
        ranges = []
        for p in state.patterns:
            r = set(range(p.offset, p.offset + len(p.text)))
            for prev in ranges:
                assert r.isdisjoint(prev), f"{p.text} overlaps"
            ranges.append(r)

    def test_deterministic_with_rng(self):
        s1 = MemDumpState.new_game(rng=random.Random(123))
        s2 = MemDumpState.new_game(rng=random.Random(123))
        assert s1.memory == s2.memory
        assert [(p.text, p.offset) for p in s1.patterns] == [
            (p.text, p.offset) for p in s2.patterns
        ]


# ── MemDumpApp startup ──────────────────────────────────────────────


@pytest.mark.unit
class TestMemDumpAppStartup:
    def test_on_start_returns_screen(self):
        app = _make_app()
        screen = app.on_start(80, 24)
        assert screen.width == 80
        assert screen.height == 24

    def test_title_present(self):
        app = _make_app()
        screen = app.on_start(80, 24)
        assert "MEMORY DUMP" in screen.lines[0]

    def test_cursor_invisible(self):
        app = _make_app()
        screen = app.on_start(80, 24)
        assert not screen.cursor_visible

    def test_hex_addresses_shown(self):
        app = _make_app()
        screen = app.on_start(80, 24)
        all_text = "\n".join(screen.lines)
        assert f"{BASE_ADDRESS:04X}" in all_text


# ── Find-as-you-type ────────────────────────────────────────────────


@pytest.mark.unit
class TestMemDumpSearch:
    def test_typing_appends_to_search(self):
        app = _make_app()
        app.on_start(80, 24)

        app.on_key("R")
        assert app.state.search == "R"
        app.on_key("O")
        assert app.state.search == "RO"

    def test_typing_costs_moves(self):
        app = _make_app()
        app.on_start(80, 24)

        app.on_key("R")
        assert app.state.moves_remaining == MAX_MOVES - 1

    def test_backspace_deletes(self):
        app = _make_app()
        app.on_start(80, 24)

        app.on_key("R")
        app.on_key("O")
        app.on_key("Backspace")
        assert app.state.search == "R"

    def test_backspace_costs_move(self):
        app = _make_app()
        app.on_start(80, 24)

        app.on_key("R")
        app.on_key("Backspace")
        assert app.state.moves_remaining == MAX_MOVES - 2

    def test_backspace_on_empty_is_noop(self):
        app = _make_app()
        app.on_start(80, 24)

        app.on_key("Backspace")
        assert app.state.search == ""
        assert app.state.moves_remaining == MAX_MOVES

    def test_escape_clears_search(self):
        app = _make_app()
        app.on_start(80, 24)

        app.on_key("R")
        app.on_key("O")
        app.on_key("Escape")
        assert app.state.search == ""

    def test_escape_on_empty_exits(self):
        app = _make_app()
        app.on_start(80, 24)

        result = app.on_key("Escape")
        assert result is None

    def test_search_highlights_match(self):
        app = _make_app()
        app.on_start(80, 24)

        for ch in "ROOT":
            app.on_key(ch)

        screen = app.on_key("ArrowDown")  # just re-render
        assert screen is not None
        # The row containing ROOT (offset 0x10 → row 1) should have
        # reverse video highlighting (\033[7m)
        all_text = "\n".join(screen.lines)
        assert "\033[7m" in all_text


# ── Confirming patterns ─────────────────────────────────────────────


@pytest.mark.unit
class TestMemDumpConfirm:
    def test_confirm_correct_pattern(self):
        app = _make_app()
        app.on_start(80, 24)

        for ch in "ROOT":
            app.on_key(ch)
        app.on_key("Enter")

        assert app.state.patterns[0].found
        assert app.state.search == ""
        assert (
            "found" in app.state.message.lower()
            or "remaining" in app.state.message.lower()
        )

    def test_confirm_wrong_text(self):
        app = _make_app()
        app.on_start(80, 24)

        for ch in "NOPE":
            app.on_key(ch)
        app.on_key("Enter")

        assert app.state.found_count == 0
        assert (
            "not a target" in app.state.message.lower()
            or "no match" in app.state.message.lower()
        )

    def test_confirm_empty_search(self):
        app = _make_app()
        app.on_start(80, 24)

        app.on_key("Enter")
        assert "type" in app.state.message.lower()

    def test_find_all_patterns_wins(self):
        app = _make_app()
        app.on_start(80, 24)

        for pattern in ["ROOT", "KEY", "EXEC"]:
            for ch in pattern:
                app.on_key(ch)
            app.on_key("Enter")

        assert app.state.phase == Phase.WON
        assert "EXTRACTED" in app.state.message

    def test_win_screen_allows_new_game(self):
        app = _make_app()
        app.on_start(80, 24)

        for pattern in ["ROOT", "KEY", "EXEC"]:
            for ch in pattern:
                app.on_key(ch)
            app.on_key("Enter")

        app.on_key("Enter")  # new game
        assert app.state.phase == Phase.PLAYING


# ── Losing ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestMemDumpLoss:
    def test_exhaust_moves_loses(self):
        app = _make_app()
        app.on_start(80, 24)

        # Type random characters to exhaust moves
        for _ in range(MAX_MOVES):
            app.on_key("Z")

        assert app.state.phase == Phase.LOST
        assert "OUT OF MOVES" in app.state.message

    def test_loss_shows_missing_patterns(self):
        app = _make_app()
        app.on_start(80, 24)

        for _ in range(MAX_MOVES):
            app.on_key("Z")

        # All patterns should be listed as missing
        for p in app.state.patterns:
            assert p.text in app.state.message

    def test_loss_with_partial_finds(self):
        app = _make_app()
        app.on_start(80, 24)

        # Find ROOT first
        for ch in "ROOT":
            app.on_key(ch)
        app.on_key("Enter")

        # Exhaust remaining moves
        remaining = app.state.moves_remaining
        for _ in range(remaining):
            app.on_key("Z")

        assert app.state.phase == Phase.LOST
        assert app.state.found_count == 1
        # Missing patterns should be listed
        assert "KEY" in app.state.message
        assert "EXEC" in app.state.message

    def test_new_game_after_loss(self):
        app = _make_app()
        app.on_start(80, 24)

        for _ in range(MAX_MOVES):
            app.on_key("Z")

        app.on_key("Enter")
        assert app.state.phase == Phase.PLAYING


# ── Navigation and rendering ────────────────────────────────────────


@pytest.mark.unit
class TestMemDumpRendering:
    def test_resize_updates(self):
        app = _make_app()
        app.on_start(80, 24)
        screen = app.on_resize(120, 40)
        assert screen.width == 120
        assert screen.height == 40

    def test_scroll_down(self):
        app = _make_app()
        app.on_start(80, 14)  # short terminal to force scrolling

        app.on_key("ArrowDown")
        assert app.state.scroll_offset == 1

    def test_scroll_up(self):
        app = _make_app()
        app.on_start(80, 14)

        app.on_key("ArrowDown")
        app.on_key("ArrowDown")
        app.on_key("ArrowUp")
        assert app.state.scroll_offset == 1

    def test_scroll_clamps_at_top(self):
        app = _make_app()
        app.on_start(80, 24)

        app.on_key("ArrowUp")
        assert app.state.scroll_offset == 0

    def test_hex_dump_shows_ascii(self):
        app = _make_app()
        screen = app.on_start(80, 24)
        all_text = "\n".join(screen.lines)
        # ASCII column delimiter
        assert "|" in all_text

    def test_found_patterns_displayed(self):
        app = _make_app()
        app.on_start(80, 24)

        for ch in "ROOT":
            app.on_key(ch)
        screen = app.on_key("Enter")
        assert screen is not None
        all_text = "\n".join(screen.lines)
        assert "ROOT" in all_text

    def test_moves_display(self):
        app = _make_app()
        screen = app.on_start(80, 24)
        all_text = "\n".join(screen.lines)
        assert f"{MAX_MOVES}" in all_text

    def test_ctrl_c_exits(self):
        app = _make_app()
        app.on_start(80, 24)
        assert app.on_key("C-c") is None

    def test_q_exits_no_search(self):
        app = _make_app()
        app.on_start(80, 24)
        assert app.on_key("q") is None

    def test_q_clears_search_first(self):
        app = _make_app()
        app.on_start(80, 24)
        app.on_key("R")
        result = app.on_key("q")
        assert result is not None  # clears search, doesn't exit
        assert app.state.search == ""

    def test_unknown_key_ignored(self):
        app = _make_app()
        app.on_start(80, 24)
        result = app.on_key("F1")
        assert result is not None
