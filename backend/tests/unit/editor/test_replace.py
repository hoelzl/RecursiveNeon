"""Tests for replace-string command (Phase 6h)."""

from __future__ import annotations

from tests.unit.editor.harness import EditorHarness, make_harness


class TestReplaceString:
    """replace-string via M-x or direct command dispatch."""

    def _do_replace(self, h: EditorHarness, search: str, replacement: str) -> None:
        """Trigger replace-string and provide both prompts."""
        h.send_keys("M-x")
        h.type_string("replace-string")
        h.send_keys("Enter")
        h.type_string(search)
        h.send_keys("Enter")
        h.type_string(replacement)
        h.send_keys("Enter")

    def test_basic_replacement(self) -> None:
        h = make_harness("foo bar foo baz foo")
        self._do_replace(h, "foo", "qux")
        assert h.buffer_text() == "qux bar qux baz qux"

    def test_reports_count(self) -> None:
        h = make_harness("aaa aaa aaa")
        self._do_replace(h, "aaa", "b")
        assert "3 occurrences" in h.message_line()

    def test_single_occurrence_message(self) -> None:
        h = make_harness("hello world")
        self._do_replace(h, "world", "earth")
        assert "1 occurrence" in h.message_line()
        assert "occurrences" not in h.message_line()

    def test_no_matches(self) -> None:
        h = make_harness("hello world")
        self._do_replace(h, "xyz", "abc")
        assert "No matches" in h.message_line()
        assert h.buffer_text() == "hello world"

    def test_replaces_from_point_only(self) -> None:
        """Replacements should only happen from point forward."""
        h = make_harness("foo bar foo baz foo")
        # Move point past first "foo"
        h.send_keys("M-f")  # forward-word to end of "foo"
        self._do_replace(h, "foo", "qux")
        # First "foo" should be untouched
        assert h.buffer_text() == "foo bar qux baz qux"

    def test_undoable_as_single_group(self) -> None:
        h = make_harness("aa bb aa cc aa")
        self._do_replace(h, "aa", "xx")
        assert h.buffer_text() == "xx bb xx cc xx"
        # Single undo should revert all replacements
        h.send_keys("C-/")
        assert h.buffer_text() == "aa bb aa cc aa"

    def test_replace_with_empty_string(self) -> None:
        h = make_harness("hello world hello")
        self._do_replace(h, "hello", "")
        assert h.buffer_text() == " world "

    def test_replace_with_longer_string(self) -> None:
        h = make_harness("ab cd ab")
        self._do_replace(h, "ab", "XYZ")
        assert h.buffer_text() == "XYZ cd XYZ"

    def test_multiline_buffer(self) -> None:
        h = make_harness("foo\nbar\nfoo\nbaz")
        self._do_replace(h, "foo", "qux")
        assert h.buffer_text() == "qux\nbar\nqux\nbaz"

    def test_cancel_search_prompt(self) -> None:
        """C-g on search prompt cancels without changes."""
        h = make_harness("foo bar")
        h.send_keys("M-x")
        h.type_string("replace-string")
        h.send_keys("Enter")
        h.send_keys("C-g")
        assert h.buffer_text() == "foo bar"

    def test_cancel_replacement_prompt(self) -> None:
        """C-g on replacement prompt cancels without changes."""
        h = make_harness("foo bar")
        h.send_keys("M-x")
        h.type_string("replace-string")
        h.send_keys("Enter")
        h.type_string("foo")
        h.send_keys("Enter")
        h.send_keys("C-g")
        assert h.buffer_text() == "foo bar"

    def test_empty_search_does_nothing(self) -> None:
        h = make_harness("foo bar")
        h.send_keys("M-x")
        h.type_string("replace-string")
        h.send_keys("Enter")
        h.send_keys("Enter")  # empty search
        assert h.buffer_text() == "foo bar"

    def test_adjacent_matches(self) -> None:
        h = make_harness("aaaa")
        self._do_replace(h, "aa", "b")
        assert h.buffer_text() == "bb"
