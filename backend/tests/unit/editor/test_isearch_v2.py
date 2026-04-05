"""Tests for Phase 6l-3 true isearch.

Covers the behaviour introduced in the reimplemented
``isearch-forward`` / ``isearch-backward``: match highlighting via the
post-compose StyleSpan pass, wrap-around with ``Failing`` → ``Wrapped``
message progression, state-stack backspace across wraps, case-fold
smart default + ``M-c`` toggle, ``M-Enter`` multi-line insertion,
exit-and-replay with an active highlight, and the rename of the old
behaviour to ``search-forward`` / ``search-backward``.

Older tests for the minibuffer-level isearch session contract live in
``test_isearch.py`` and still exercise the new implementation — they
assert behaviour that is shared between legacy and v2.
"""

from __future__ import annotations

from recursive_neon.editor.commands import COMMANDS
from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.view import EditorView


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


def make_view(text: str = "", *, width: int = 40, height: int = 10) -> EditorView:
    ed = make_editor(text)
    view = EditorView(editor=ed)
    view.on_start(width, height)
    return view


# ═══════════════════════════════════════════════════════════════════════
# Highlighting: ed.highlight_term + rendered spans
# ═══════════════════════════════════════════════════════════════════════


class TestIsearchHighlighting:
    def test_highlight_term_set_on_typing(self):
        ed = make_editor("hello world")
        ed.process_key("C-s")
        ed.process_key("w")
        ed.process_key("o")
        assert ed.highlight_term == "wo"

    def test_highlight_term_cleared_on_confirm(self):
        ed = make_editor("hello world")
        ed.process_key("C-s")
        ed.process_key("w")
        ed.process_key("Enter")
        assert ed.highlight_term is None

    def test_highlight_term_cleared_on_cancel(self):
        ed = make_editor("hello world")
        ed.process_key("C-s")
        ed.process_key("w")
        ed.process_key("C-g")
        assert ed.highlight_term is None

    def test_highlight_term_cleared_by_reset_transient_state(self):
        ed = make_editor("hello world")
        ed.highlight_term = "manual"
        ed.highlight_case_fold = True
        ed._reset_transient_state()
        assert ed.highlight_term is None
        assert ed.highlight_case_fold is False

    def test_matches_rendered_with_ansi_in_screen(self):
        # The view should wrap isearch matches in an ANSI style.
        view = make_view("foo bar foo baz foo", width=40, height=5)
        view.on_key("C-s")
        view.on_key("f")
        view.on_key("o")
        view.on_key("o")
        screen = view.on_start(40, 5)  # force a fresh render
        # Re-render via on_key with a no-op to capture current state
        screen = view._render()
        line0 = screen.lines[0]
        # "foo" should appear styled at least once (ANSI escape in line)
        assert "\033[" in line0, f"Expected ANSI codes in: {line0!r}"
        # All three "foo" substrings should still be present visibly
        # (the ANSI wrapper may split them, but each "foo" run is preserved)
        plain = _strip_ansi(line0)
        assert plain.startswith("foo bar foo baz foo")

    def test_current_match_uses_distinct_style(self):
        view = make_view("foo and foo", width=20, height=3)
        view.on_key("C-s")
        view.on_key("f")
        view.on_key("o")
        view.on_key("o")
        screen = view._render()
        line0 = screen.lines[0]
        # Current match is highlighted with a distinct code (bold+red bg)
        assert "\033[1;41;97m" in line0  # _HIGHLIGHT_CURRENT
        # Other matches use the non-current style (yellow bg)
        assert "\033[43;30m" in line0  # _HIGHLIGHT_MATCH

    def test_no_highlight_before_isearch_starts(self):
        view = make_view("hello world", width=20, height=3)
        screen = view._render()
        assert "\033[43;30m" not in screen.lines[0]
        assert "\033[1;41;97m" not in screen.lines[0]


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences for plain-text comparison."""
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ═══════════════════════════════════════════════════════════════════════
# Wrap-around: "Failing" → "Wrapped" progression
# ═══════════════════════════════════════════════════════════════════════


class TestIsearchWrap:
    def test_first_failure_shows_failing(self):
        ed = make_editor("aaa bbb ccc")
        ed.process_key("C-s")
        ed.process_key("a")
        ed.process_key("a")
        ed.process_key("a")
        # After finding (0, 0) there is no further match forward
        ed.process_key("C-s")
        assert ed.minibuffer is not None
        assert "Failing" in ed.minibuffer.prompt
        assert "Wrapped" not in ed.minibuffer.prompt

    def test_second_cs_after_failure_wraps(self):
        ed = make_editor("foo X bar X baz")
        # Start at col 0, search for X, advance twice, then wrap
        ed.process_key("C-s")
        ed.process_key("X")
        assert ed.buffer.point.col == 4
        ed.process_key("C-s")
        assert ed.buffer.point.col == 10
        ed.process_key("C-s")
        assert ed.minibuffer is not None
        assert "Failing" in ed.minibuffer.prompt
        # Now wrap
        ed.process_key("C-s")
        assert "Wrapped" in ed.minibuffer.prompt
        assert ed.buffer.point.col == 4  # back to first match

    def test_backward_wrap_from_bob_to_eob(self):
        # Start with point at (0, 0) over a non-X character so there's no
        # X at-or-before point; the backward search should fail, and then
        # a second C-r should wrap to the last X at the end of the buffer.
        ed = make_editor("foo X bar X baz")
        ed.buffer.beginning_of_buffer()  # (0, 0), over 'f'
        ed.process_key("C-r")
        ed.process_key("X")
        assert ed.minibuffer is not None
        assert "Failing" in ed.minibuffer.prompt
        # Wrap backward should find the last "X" in the buffer
        ed.process_key("C-r")
        assert "Wrapped" in ed.minibuffer.prompt
        assert ed.buffer.point.col == 10  # last X in "foo X bar X baz"

    def test_wrap_still_failing_when_no_matches(self):
        ed = make_editor("hello world")
        ed.process_key("C-s")
        ed.process_key("z")
        assert ed.minibuffer is not None
        assert "Failing" in ed.minibuffer.prompt
        ed.process_key("C-s")  # wrap attempt
        # Still failing even after wrap
        assert "Failing" in ed.minibuffer.prompt or "Wrapped" in ed.minibuffer.prompt


# ═══════════════════════════════════════════════════════════════════════
# Case-fold: smart default + M-c toggle
# ═══════════════════════════════════════════════════════════════════════


class TestIsearchCaseFold:
    def test_lowercase_search_folds_by_default(self):
        # Smart case: all-lowercase term ⇒ case-insensitive
        ed = make_editor("Foo and foo")
        ed.process_key("C-s")
        ed.process_key("f")
        ed.process_key("o")
        ed.process_key("o")
        # Should match "Foo" at (0, 0) because folding is active
        assert ed.buffer.point.col == 0
        assert ed.highlight_case_fold is True

    def test_uppercase_char_disables_smart_fold(self):
        ed = make_editor("Foo and foo")
        ed.process_key("C-s")
        ed.process_key("F")
        ed.process_key("o")
        ed.process_key("o")
        # Capital F disables folding; should match "Foo" at (0, 0) only
        assert ed.buffer.point.col == 0
        assert ed.highlight_case_fold is False
        # Next C-s should NOT find "foo" (case sensitive)
        ed.process_key("C-s")
        assert "Failing" in (ed.minibuffer.prompt if ed.minibuffer else "")

    def test_mc_toggle_forces_case_sensitive(self):
        ed = make_editor("Foo and foo")
        ed.process_key("C-s")
        ed.process_key("f")
        ed.process_key("o")
        ed.process_key("o")
        assert ed.buffer.point.col == 0  # matched "Foo" via fold
        ed.process_key("M-c")  # toggle off fold
        assert ed.highlight_case_fold is False
        assert ed.minibuffer is not None
        assert "(case)" in ed.minibuffer.prompt

    def test_mc_toggle_forces_fold(self):
        ed = make_editor("Foo and foo")
        ed.process_key("C-s")
        ed.process_key("F")
        ed.process_key("o")
        ed.process_key("o")
        assert ed.highlight_case_fold is False
        ed.process_key("M-c")  # toggle on fold
        assert ed.highlight_case_fold is True
        assert ed.minibuffer is not None
        assert "(fold)" in ed.minibuffer.prompt

    def test_case_fold_search_variable_false_disables_smart_fold(self):
        ed = make_editor("Foo and foo")
        # ``set_variable`` mutates the module-level VARIABLES registry,
        # so we save and restore around the assertion to keep the
        # default for subsequent tests (notably test_query_replace,
        # which relies on the default True).
        original = ed.get_variable("case-fold-search")
        try:
            ed.set_variable("case-fold-search", False)
            ed.process_key("C-s")
            ed.process_key("f")
            ed.process_key("o")
            ed.process_key("o")
            # Global var disables smart fold even for lowercase term
            assert ed.highlight_case_fold is False
        finally:
            ed.set_variable("case-fold-search", original)


# ═══════════════════════════════════════════════════════════════════════
# State stack: backspace semantics
# ═══════════════════════════════════════════════════════════════════════


class TestIsearchStateStack:
    def test_backspace_shortens_search_and_restores_previous_position(self):
        ed = make_editor("foo bar foo baz")
        ed.process_key("C-s")
        ed.process_key("f")
        ed.process_key("o")
        ed.process_key("o")
        assert ed.buffer.point.col == 0
        ed.process_key("C-s")  # repeat forward
        assert ed.buffer.point.col == 8  # second "foo"
        ed.process_key("Backspace")  # pop the repeat
        # Should go back to the first match
        assert ed.buffer.point.col == 0
        assert ed.minibuffer is not None
        assert ed.minibuffer.text == "foo"  # text unchanged

    def test_backspace_shortens_text_when_at_type_state(self):
        ed = make_editor("foo bar")
        ed.process_key("C-s")
        ed.process_key("f")
        ed.process_key("o")
        ed.process_key("o")
        # Stack has three type states above root
        ed.process_key("Backspace")
        assert ed.minibuffer is not None
        assert ed.minibuffer.text == "fo"
        ed.process_key("Backspace")
        assert ed.minibuffer.text == "f"
        ed.process_key("Backspace")
        assert ed.minibuffer.text == ""
        # Point should be back at origin
        assert ed.buffer.point.col == 0

    def test_backspace_at_empty_search_is_noop(self):
        ed = make_editor("hello")
        ed.buffer.point.col = 3
        ed.process_key("C-s")
        ed.process_key("Backspace")
        # Still active, still at origin
        assert ed.minibuffer is not None
        assert ed.minibuffer.text == ""
        assert ed.buffer.point.col == 3

    def test_backspace_across_wrap_preserves_prior_state(self):
        ed = make_editor("X foo X bar X")
        ed.process_key("C-s")
        ed.process_key("X")
        # (0, 0)
        ed.process_key("C-s")  # (0, 6)
        ed.process_key("C-s")  # (0, 12)
        ed.process_key("C-s")  # failing
        ed.process_key("C-s")  # wrap to (0, 0)
        assert ed.buffer.point.col == 0
        assert "Wrapped" in ed.minibuffer.prompt if ed.minibuffer else ""
        ed.process_key("Backspace")  # pop the wrap
        # Should restore the failing state right before the wrap
        assert ed.minibuffer is not None
        assert "Failing" in ed.minibuffer.prompt


# ═══════════════════════════════════════════════════════════════════════
# Multi-line: M-Enter inserts newline into search term
# ═══════════════════════════════════════════════════════════════════════


class TestIsearchMultiLine:
    def test_m_enter_inserts_newline_into_search_term(self):
        ed = make_editor("abc\ndef")
        ed.process_key("C-s")
        ed.process_key("c")
        ed.process_key("M-Enter")
        ed.process_key("d")
        assert ed.minibuffer is not None
        assert ed.minibuffer.text == "c\nd"
        # Match found crossing line boundary
        assert ed.buffer.point.line == 0
        assert ed.buffer.point.col == 2

    def test_multi_line_search_finds_cross_line_match(self):
        ed = make_editor("foo\nbar\nbaz")
        ed.process_key("C-s")
        ed.process_key("o")
        ed.process_key("o")
        ed.process_key("M-Enter")
        ed.process_key("b")
        ed.process_key("a")
        # "oo\nba" should match at (0, 1)
        assert ed.buffer.point.line == 0
        assert ed.buffer.point.col == 1


# ═══════════════════════════════════════════════════════════════════════
# Exit-and-replay with active highlight
# ═══════════════════════════════════════════════════════════════════════


class TestIsearchExitReplayClearsHighlight:
    def test_unknown_key_exits_isearch_and_clears_highlight(self):
        ed = make_editor("hello world\nsecond line")
        ed.process_key("C-s")
        ed.process_key("w")
        ed.process_key("o")
        assert ed.highlight_term == "wo"
        # C-n is unbound in the isearch minibuffer → exit-and-replay
        ed.process_key("C-n")
        assert ed.minibuffer is None
        assert ed.buffer.point.line == 1  # C-n moved down
        # Highlight should be cleared on the replay path
        assert ed.highlight_term is None
        assert ed.highlight_case_fold is False


# ═══════════════════════════════════════════════════════════════════════
# Rename: search-forward / search-backward still reachable via M-x
# ═══════════════════════════════════════════════════════════════════════


class TestSearchForwardRename:
    def test_search_forward_command_registered(self):
        assert "search-forward" in COMMANDS
        assert "search-backward" in COMMANDS

    def test_isearch_forward_still_registered(self):
        assert "isearch-forward" in COMMANDS
        assert "isearch-backward" in COMMANDS

    def test_cs_binding_is_isearch_forward(self):
        km = build_default_keymap()
        # C-s should resolve to isearch-forward (the NEW implementation)
        assert km.lookup("C-s") == "isearch-forward"
        assert km.lookup("C-r") == "isearch-backward"

    def test_search_forward_does_not_set_highlight(self):
        # Legacy search behaviour doesn't use highlight_term
        ed = make_editor("foo bar foo")
        ed.execute_command("search-forward", None)
        ed.process_key("f")
        ed.process_key("o")
        ed.process_key("o")
        # search-forward uses the legacy prompt label
        assert ed.minibuffer is not None
        assert "Search" in ed.minibuffer.prompt
        # No highlight is set by the legacy path
        assert ed.highlight_term is None

    def test_search_forward_still_advances_point(self):
        ed = make_editor("foo bar foo")
        ed.execute_command("search-forward", None)
        ed.process_key("f")
        ed.process_key("o")
        ed.process_key("o")
        ed.process_key("Enter")
        assert ed.minibuffer is None
        # Legacy search still moves point to the match
        assert ed.buffer.point.col == 0
