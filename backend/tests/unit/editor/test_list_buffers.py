"""Tests for list-buffers (C-x C-b) and kill-buffer's modified confirm.

Both behaviours are pinned against GNU Emacs 29 via parity scenarios 27
(kill confirm) and 28 (*Buffer List*).
"""

from __future__ import annotations

from .harness import EditorHarness, make_harness


def _buffer_list_text(h: EditorHarness) -> str:
    return h.buffer_text_named("*Buffer List*")


class TestListBuffers:
    def test_pops_up_in_other_window_without_selecting(self) -> None:
        h = make_harness("alpha\nbeta\n", width=80, height=24)
        h.editor.buffer.name = "file.txt"
        h.editor.buffer.filepath = "file.txt"
        h.send_keys("C-x", "C-b")
        # Focus stays in the original window: cursor in the top window.
        assert h.cursor_position() == (0, 0)
        # Two windows: the bottom one shows *Buffer List* (its modeline
        # carries the name and the Buffer Menu mode).
        lines = h.screen_lines()
        assert any("*Buffer List*" in ln and "Buffer Menu" in ln for ln in lines)

    def test_table_layout_matches_emacs_columns(self) -> None:
        h = make_harness("alpha\nbeta\n", width=80, height=24)
        h.editor.buffer.name = "file.txt"
        h.editor.buffer.filepath = "file.txt"
        h.editor.set_major_mode("text-mode")
        h.send_keys("C-x", "C-b")
        text = _buffer_list_text(h).split("\n")
        assert text[0] == "CRM Buffer                 Size Mode             File"
        # Current buffer row: "." flag, name at col 4, size right-aligned
        # ending col 30, mode at col 32, file at col 49.
        row = text[1]
        assert row.startswith(".   file.txt")
        assert row[28:31] == " 11"  # len("alpha\nbeta\n") == 11
        assert row[32:36] == "Text"
        assert row[49:] == "file.txt"

    def test_flags_readonly_and_modified(self) -> None:
        h = make_harness("alpha\n", width=80, height=24)
        h.editor.buffer.name = "file.txt"
        h.editor.buffer.filepath = "file.txt"
        h.editor.create_buffer(name="other", text="x")
        h.editor.buffer.read_only = True
        h.editor.switch_to_buffer("file.txt")
        h.type_string("z")  # modify the current buffer
        h.send_keys("C-x", "C-b")
        rows = _buffer_list_text(h).split("\n")
        assert rows[1].startswith(". * file.txt")  # current + modified
        other_row = next(r for r in rows if "other" in r)
        assert other_row.startswith(" %  other")  # read-only, not current

    def test_excludes_itself_and_orders_mru(self) -> None:
        h = make_harness("a", width=80, height=24)
        h.editor.buffer.name = "first"
        h.editor.create_buffer(name="second", text="bb")
        h.editor.switch_to_buffer("first")
        h.send_keys("C-x", "C-b")
        rows = _buffer_list_text(h).split("\n")
        assert not any("*Buffer List*" in r for r in rows)
        # Current ("first") first, then "second" by recency.
        assert rows[1].lstrip(". %*").lstrip().startswith("first")
        assert "second" in rows[2]

    def test_long_name_spills_then_truncates_with_ellipsis(self) -> None:
        h = make_harness("a", width=80, height=24)
        h.editor.buffer.name = "x" * 30
        h.send_keys("C-x", "C-b")
        rows = _buffer_list_text(h).split("\n")
        row = rows[1]
        # Size "1" right-aligned at col 30; the name may run to col 27
        # (two cells short of the size), i.e. 24 chars, then "…".
        assert row[4:28] == "x" * 23 + "…"
        assert row[30] == "1"


class TestKillBufferConfirm:
    def _modified_file_harness(self) -> EditorHarness:
        h = make_harness("alpha\n", width=80, height=24)
        h.editor.buffer.name = "file.txt"
        h.editor.buffer.filepath = "file.txt"
        h.type_string("z")
        return h

    def _open_confirm(self, h: EditorHarness) -> None:
        h.send_keys("C-x", "k", "Enter")  # default: current buffer

    def test_confirm_prompt_text(self) -> None:
        h = self._modified_file_harness()
        self._open_confirm(h)
        assert h.editor.minibuffer is not None
        assert h.editor.minibuffer.prompt == (
            "Buffer file.txt modified; kill anyway? (yes/no/save and then kill) "
        )

    def test_yes_kills(self) -> None:
        h = self._modified_file_harness()
        self._open_confirm(h)
        h.type_string("yes")
        h.send_keys("Enter")
        assert all(b.name != "file.txt" for b in h.editor.buffers)

    def test_unique_prefix_y_completes_to_yes(self) -> None:
        """Emacs's long-form read-multiple-choice reads via completion
        with require-match: RET on a unique prefix completes ("y" → yes)."""
        h = self._modified_file_harness()
        self._open_confirm(h)
        h.type_string("y")
        h.send_keys("Enter")
        assert all(b.name != "file.txt" for b in h.editor.buffers)

    def test_no_keeps_the_buffer(self) -> None:
        h = self._modified_file_harness()
        self._open_confirm(h)
        h.type_string("no")
        h.send_keys("Enter")
        assert any(b.name == "file.txt" for b in h.editor.buffers)
        assert h.editor.minibuffer is None

    def test_invalid_answer_reprompts(self) -> None:
        h = self._modified_file_harness()
        self._open_confirm(h)
        h.type_string("x")
        h.send_keys("Enter")
        assert h.editor.minibuffer is not None  # still asking
        assert any(b.name == "file.txt" for b in h.editor.buffers)

    def test_save_and_then_kill(self) -> None:
        h = self._modified_file_harness()
        saved: list[str] = []
        h.editor.save_callback = lambda buf: (saved.append(buf.name), True)[1]
        self._open_confirm(h)
        h.type_string("s")
        h.send_keys("Enter")
        assert saved == ["file.txt"]
        assert all(b.name != "file.txt" for b in h.editor.buffers)
        assert h.editor.message == "Wrote file.txt"

    def test_modified_non_file_buffer_kills_silently(self) -> None:
        h = make_harness("alpha\n", width=80, height=24)
        # Switch through the TUI so the window shows the new buffer.
        h.send_keys("C-x", "b")
        h.type_string("extra")
        h.send_keys("Enter")
        h.type_string("z")  # modify "extra" (current), no filepath
        self._open_confirm(h)
        assert all(b.name != "extra" for b in h.editor.buffers)
        assert h.editor.minibuffer is None

    def test_unmodified_file_buffer_kills_silently(self) -> None:
        h = make_harness("alpha\n", width=80, height=24)
        h.editor.buffer.name = "file.txt"
        h.editor.buffer.filepath = "file.txt"
        self._open_confirm(h)
        assert all(b.name != "file.txt" for b in h.editor.buffers)
