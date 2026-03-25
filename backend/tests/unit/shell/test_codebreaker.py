"""Tests for the CodeBreaker minigame."""

from __future__ import annotations

from recursive_neon.shell.programs.codebreaker import (
    CODE_LENGTH,
    MAX_GUESSES,
    SYMBOLS,
    CodeBreakerApp,
    CodeBreakerState,
)

# ── CodeBreakerState ──────────────────────────────────────────────────────


class TestCodeBreakerState:
    def test_new_game_generates_valid_secret(self):
        state = CodeBreakerState.new_game()
        assert len(state.secret) == CODE_LENGTH
        assert all(s in SYMBOLS for s in state.secret)

    def test_all_exact(self):
        state = CodeBreakerState(secret=["R", "G", "B", "Y"])
        exact, partial = state.check_guess(["R", "G", "B", "Y"])
        assert exact == 4
        assert partial == 0

    def test_no_matches(self):
        state = CodeBreakerState(secret=["R", "R", "R", "R"])
        exact, partial = state.check_guess(["G", "G", "G", "G"])
        assert exact == 0
        assert partial == 0

    def test_all_partial(self):
        state = CodeBreakerState(secret=["R", "G", "B", "Y"])
        exact, partial = state.check_guess(["Y", "B", "G", "R"])
        assert exact == 0
        assert partial == 4

    def test_mixed_exact_and_partial(self):
        state = CodeBreakerState(secret=["R", "G", "B", "Y"])
        exact, partial = state.check_guess(["R", "B", "G", "M"])
        assert exact == 1  # R
        assert partial == 2  # G and B swapped

    def test_duplicate_in_guess_limited_by_secret(self):
        """Guessing R R R R when secret has one R gives only 1 match."""
        state = CodeBreakerState(secret=["R", "G", "B", "Y"])
        exact, partial = state.check_guess(["R", "R", "R", "R"])
        assert exact == 1  # first R
        assert partial == 0

    def test_duplicate_in_secret_and_guess(self):
        state = CodeBreakerState(secret=["R", "R", "G", "B"])
        exact, partial = state.check_guess(["R", "R", "R", "R"])
        assert exact == 2  # two Rs in correct positions
        assert partial == 0

    def test_partial_with_duplicates(self):
        state = CodeBreakerState(secret=["R", "G", "B", "Y"])
        exact, partial = state.check_guess(["G", "R", "Y", "B"])
        assert exact == 0
        assert partial == 4

    def test_exact_trumps_partial(self):
        """An exact match should not also count as partial."""
        state = CodeBreakerState(secret=["R", "G", "R", "B"])
        exact, partial = state.check_guess(["R", "R", "R", "G"])
        assert exact == 2  # pos 0 and 2
        assert partial == 1  # G at pos 3 matches pos 1

    def test_initial_state_not_game_over(self):
        state = CodeBreakerState.new_game()
        assert not state.game_over
        assert not state.won
        assert len(state.guesses) == 0


# ── CodeBreakerApp ────────────────────────────────────────────────────────


class TestCodeBreakerApp:
    def test_on_start_returns_screen(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        screen = app.on_start(80, 24)
        assert screen.width == 80
        assert screen.height == 24
        # Title should be in first row
        assert "CODEBREAKER" in screen.lines[0]

    def test_escape_exits(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)
        result = app.on_key("Escape")
        assert result is None

    def test_ctrl_c_exits(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)
        result = app.on_key("C-c")
        assert result is None

    def test_arrow_left_right_moves_cursor(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)

        # Start at position 0
        assert app.state.cursor_pos == 0

        app.on_key("ArrowRight")
        assert app.state.cursor_pos == 1

        app.on_key("ArrowRight")
        assert app.state.cursor_pos == 2

        app.on_key("ArrowLeft")
        assert app.state.cursor_pos == 1

    def test_cursor_stays_in_bounds(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)

        app.on_key("ArrowLeft")  # Already at 0
        assert app.state.cursor_pos == 0

        for _ in range(10):
            app.on_key("ArrowRight")
        assert app.state.cursor_pos == CODE_LENGTH - 1

    def test_symbol_keys_set_slot(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)

        app.on_key("r")  # lowercase should work
        assert app.state.current_input[0] == "R"
        assert app.state.cursor_pos == 1  # auto-advance

        app.on_key("G")
        assert app.state.current_input[1] == "G"
        assert app.state.cursor_pos == 2

    def test_arrow_up_down_cycles_symbols(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)

        app.on_key("ArrowUp")
        assert app.state.current_input[0] == SYMBOLS[1]  # G (R→G)

        app.on_key("ArrowDown")
        assert app.state.current_input[0] == SYMBOLS[0]  # R (G→R)

    def test_backspace_clears_input(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)

        app.on_key("r")
        app.on_key("g")
        assert len(app.state.current_input) == 2

        app.on_key("Backspace")
        assert len(app.state.current_input) == 0
        assert app.state.cursor_pos == 0

    def test_incomplete_guess_shows_message(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)

        app.on_key("r")
        app.on_key("g")
        # Only 2 of 4 slots filled
        app.on_key("Enter")

        assert "Need" in app.state.message
        assert len(app.state.guesses) == 0

    def test_submit_correct_guess_wins(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)

        for s in ["R", "G", "B", "Y"]:
            app.on_key(s)
        app.on_key("Enter")

        assert app.state.won
        assert app.state.game_over
        assert len(app.state.guesses) == 1
        assert "GRANTED" in app.state.message

    def test_submit_wrong_guess_shows_feedback(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)

        for s in ["R", "R", "R", "R"]:
            app.on_key(s)
        app.on_key("Enter")

        assert not app.state.game_over
        assert len(app.state.guesses) == 1
        assert app.state.feedback[0] == (1, 0)  # 1 exact, 0 partial
        assert "1 exact" in app.state.message

    def test_exhaust_guesses_loses(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)

        # Make 10 wrong guesses
        for _ in range(MAX_GUESSES):
            for s in ["C", "C", "C", "C"]:
                app.on_key(s)
            app.on_key("Enter")

        assert app.state.game_over
        assert not app.state.won
        assert "DENIED" in app.state.message

    def test_new_game_after_win(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)

        for s in ["R", "G", "B", "Y"]:
            app.on_key(s)
        app.on_key("Enter")
        assert app.state.game_over

        # Press Enter to start new game
        result = app.on_key("Enter")
        assert result is not None
        assert not app.state.game_over
        assert len(app.state.guesses) == 0

    def test_new_game_after_loss(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)

        for _ in range(MAX_GUESSES):
            for s in ["C", "C", "C", "C"]:
                app.on_key(s)
            app.on_key("Enter")

        assert app.state.game_over
        result = app.on_key("Enter")
        assert result is not None
        assert not app.state.game_over

    def test_on_resize_returns_screen(self):
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)

        screen = app.on_resize(100, 30)
        assert screen.width == 100
        assert screen.height == 30
        assert app.width == 100
        assert app.height == 30

    def test_guess_feedback_appears_in_screen(self):
        """After a guess, the screen should show the guess and feedback dots."""
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)

        for s in ["R", "G", "M", "C"]:
            app.on_key(s)
        screen = app.on_key("Enter")

        # Row 5 should have the first guess
        assert screen is not None
        line = screen.lines[5]
        assert "1." in line
        # Should contain feedback dots (exact=2: R, G correct)
        assert "●" in line

    def test_unknown_keys_ignored(self):
        """Keys that are not mapped should not crash."""
        app = CodeBreakerApp(secret=["R", "G", "B", "Y"])
        app.on_start(80, 24)

        result = app.on_key("F1")
        assert result is not None  # Returns screen, doesn't crash

        result = app.on_key("Tab")
        assert result is not None
