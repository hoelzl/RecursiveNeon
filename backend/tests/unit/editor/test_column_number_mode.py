"""Tests for the column-number-mode toggle command.

GNU Emacs's column-number-mode is a *global* minor mode: the toggle
message has no "in current buffer" suffix (unlike auto-fill-mode) and
the effect applies to every buffer's modeline. Verified against Emacs 29
via the parity harness (scenario 24).
"""

from __future__ import annotations

import pytest

from recursive_neon.editor.variables import VARIABLES

from .harness import make_harness


@pytest.fixture(autouse=True)
def _restore_global_default():
    """The command mutates the global variable default; undo after each test."""
    var = VARIABLES["column-number-mode"]
    saved = var.default
    yield
    var.default = saved


class TestColumnNumberMode:
    def test_toggle_enables_with_global_message(self) -> None:
        h = make_harness("hello\nworld", width=60)
        h.send_keys("M-x")
        h.type_string("column-number-mode")
        h.send_keys("Enter")
        assert h.editor.message == "Column-Number mode enabled"
        assert h.editor.get_variable("column-number-mode") is True

    def test_toggle_twice_disables(self) -> None:
        h = make_harness("hello\nworld", width=60)
        h.editor.execute_command("column-number-mode")
        h.editor.execute_command("column-number-mode")
        assert h.editor.message == "Column-Number mode disabled"
        assert h.editor.get_variable("column-number-mode") is False

    def test_prefix_arg_forces_direction(self) -> None:
        h = make_harness("", width=60)
        h.editor.execute_command("column-number-mode", prefix=1)
        assert h.editor.get_variable("column-number-mode") is True
        # Positive prefix on an already-enabled mode keeps it enabled.
        h.editor.execute_command("column-number-mode", prefix=4)
        assert h.editor.get_variable("column-number-mode") is True

    def test_modeline_shows_paren_format_when_enabled(self) -> None:
        h = make_harness("hello\nworld", width=60)
        h.editor.execute_command("column-number-mode")
        h.send_keys("C-n", "C-f", "C-f", "C-f")
        assert "(2,3)" in h.modeline()

    def test_global_effect_spans_buffers(self) -> None:
        """The mode is global: a buffer created later shows the format too."""
        h = make_harness("hello", width=60)
        h.editor.execute_command("column-number-mode")
        h.editor.create_buffer(text="other")
        h.send_keys("C-f")  # force a re-render in the new buffer
        assert "(1,1)" in h.modeline()
