"""Tests for auto-fill-mode (M-x auto-fill-mode).

A text-mode buffer starts with auto-fill OFF (matching GNU Emacs);
M-x auto-fill-mode toggles the minor mode, echoing the standard
``Auto-Fill mode <enabled|disabled> in current buffer`` message, adding
the ``Fill`` modeline lighter, and (when on) breaking lines past
fill-column during typing.
"""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


def _type(ed: Editor, s: str) -> None:
    for ch in s:
        ed.process_key(ch)


class TestAutoFillModeToggle:
    def test_enable_message_and_state(self) -> None:
        ed = make_editor("")
        ed.execute_command("auto-fill-mode")
        assert ed.message == "Auto-Fill mode enabled in current buffer"
        assert ed.get_variable("auto-fill") is True
        assert any(m.name == "auto-fill-mode" for m in ed.buffer.minor_modes)

    def test_disable_message_and_state(self) -> None:
        ed = make_editor("")
        ed.execute_command("auto-fill-mode")
        ed.execute_command("auto-fill-mode")
        assert ed.message == "Auto-Fill mode disabled in current buffer"
        assert ed.get_variable("auto-fill") is False
        assert not any(m.name == "auto-fill-mode" for m in ed.buffer.minor_modes)

    def test_fill_lighter_indicator(self) -> None:
        ed = make_editor("")
        ed.execute_command("auto-fill-mode")
        m = next(m for m in ed.buffer.minor_modes if m.name == "auto-fill-mode")
        assert m.indicator == "Fill"


class TestAutoFillDefaultOff:
    def test_text_mode_does_not_enable_auto_fill(self) -> None:
        ed = make_editor("")
        ed.set_major_mode("text-mode")
        assert ed.get_variable("auto-fill") is False


class TestAutoFillBreak:
    def test_breaks_past_fill_column_when_enabled(self) -> None:
        ed = make_editor("")
        ed.execute_command("auto-fill-mode")
        _type(ed, " ".join(["word"] * 20))  # well past column 70
        ed.process_key(" ")
        assert "\n" in ed.buffer.text  # auto-fill broke the line

    def test_no_break_when_disabled(self) -> None:
        ed = make_editor("")  # fundamental, auto-fill off
        _type(ed, " ".join(["word"] * 20))
        ed.process_key(" ")
        assert "\n" not in ed.buffer.text
