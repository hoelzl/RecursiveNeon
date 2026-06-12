"""Tests for the full python-indent-calculate-indentation port.

Every expectation here was first observed in GNU Emacs 29.3 via the
parity probe battery (TAB-cycle columns per construct) and is verified
end-to-end in parity scenario 29. Levels are listed deepest-first, the
order ``python-indent-line`` cycles them.
"""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.modes import register_language_modes
from recursive_neon.editor.modes.python_mode import _python_indent_levels

register_language_modes()


def levels_for(text: str) -> list[int]:
    """The indent levels for the *last* line of *text*."""
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    ed.set_major_mode("python-mode")
    ed.buffer.point.move_to(ed.buffer.line_count - 1, 0)
    return _python_indent_levels(ed.buffer)


class TestBasicContexts:
    def test_after_plain_line(self) -> None:
        assert levels_for("if x:\n    a = 1\nb") == [4, 0]

    def test_after_block_start(self) -> None:
        assert levels_for("if x:\nb") == [4, 0]

    def test_after_block_end_return(self) -> None:
        assert levels_for("if x:\n    return 1\nb") == [0]

    def test_after_block_end_pass(self) -> None:
        assert levels_for("if x:\n    pass\nb") == [0]

    def test_after_comment_uses_comment_indent(self) -> None:
        assert levels_for("if x:\n    # hey\nb") == [4, 0]

    def test_first_line_is_zero(self) -> None:
        assert levels_for("b") == [0]

    def test_colon_in_comment_does_not_open_block(self) -> None:
        assert levels_for("a = 1  # note:\nb") == [0]


class TestBrackets:
    def test_content_after_bracket_aligns_to_it(self) -> None:
        # "foobar(" puts the first arg at col 7; chain restarts at the
        # offset multiples below (7 -> 4 -> 0), as Emacs cycles it.
        assert levels_for("foobar(a,\nb") == [7, 4, 0]

    def test_newline_after_bracket_indents_plus_four(self) -> None:
        assert levels_for("foo = bar(\nb") == [4, 0]

    def test_newline_after_def_bracket_indents_plus_eight(self) -> None:
        # python-indent-def-block-scale: block-start opening lines double
        # the offset so arguments don't align with the body.
        assert levels_for("def foo(\nx") == [8, 4, 0]

    def test_indented_opening_line(self) -> None:
        assert levels_for("if q:\n    foo = bar(\nb") == [8, 4, 0]

    def test_closing_bracket_aligns_to_opening_line(self) -> None:
        assert levels_for("foo = [\n    1,\n]") == [0]
        assert levels_for("if q:\n    foo = [\n        1,\n]") == [4, 0]

    def test_nested_brackets_use_innermost(self) -> None:
        assert levels_for("foo(bar(a,\nb") == [8, 4, 0]

    def test_bracket_in_string_does_not_count(self) -> None:
        assert levels_for('a = "("\nb') == [0]

    def test_bracket_in_comment_does_not_count(self) -> None:
        assert levels_for("foo = 1  # bar(\nb") == [0]

    def test_closed_bracket_does_not_count(self) -> None:
        assert levels_for("foo(a, b)\nc") == [0]

    def test_bracket_inside_triple_quoted_string(self) -> None:
        assert levels_for('x = """\n(\n"""\nb') == [0]


class TestBackslashContinuations:
    def test_first_continuation_plus_four(self) -> None:
        assert levels_for("abcd = 1 + \\\ny") == [4, 0]
        assert levels_for("foo(a) \\\ny") == [4, 0]
        assert levels_for("abcd = \\\ny") == [4, 0]

    def test_later_continuation_aligns_with_previous(self) -> None:
        assert levels_for("x = 1 + \\\n    2 + \\\ny") == [4, 0]

    def test_block_statement_continuation_after_keyword(self) -> None:
        # "if aaa and \" -> the continuation sits right after "if ".
        assert levels_for("if aaa and \\\ny") == [3, 0]


class TestDedenterClosesMessage:
    def test_tab_on_dedenter_echoes_closes(self) -> None:
        """Emacs messages "Closes <opener line>" when a dedenter line is
        indented to a candidate column."""
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(text="try:\n    if c:\n        pass\nelse:")
        ed.set_major_mode("python-mode")
        ed.buffer.point.move_to(3, 0)
        ed.process_key("Tab")
        assert ed.buffer.lines[3] == "    else:"
        assert ed.message == "Closes if c:"


class TestDedenters:
    def test_else_matches_enclosing_ifs(self) -> None:
        assert levels_for("if a:\n    x = 1\nelse:") == [0]
        assert levels_for("if a:\n    if b:\n        x = 1\nelse:") == [4, 0]

    def test_three_deep(self) -> None:
        text = "if a:\n    if b:\n        if c:\n            x = 1\nelse:"
        assert levels_for(text) == [8, 4, 0]

    def test_elif_matches_if_only(self) -> None:
        # The while at indent 4 cannot take an elif: only the if matches.
        assert levels_for("if a:\n    while t:\n        pass\nelif b:") == [0]

    def test_except_and_finally_match_try(self) -> None:
        assert levels_for("try:\n    x = 1\nexcept ValueError:") == [0]
        assert levels_for("try:\n    x = 1\nfinally:") == [0]

    def test_else_matches_for_and_while(self) -> None:
        assert levels_for("for i in x:\n    if a:\n        pass\nelse:") == [4, 0]

    def test_non_matching_opener_shadows_deeper_candidates(self) -> None:
        # The with at indent 4 is nearer than the inner if at the same
        # indent: an else placed at 4 would attach to the with (invalid),
        # so only the outer if remains a candidate. Emacs's backward
        # block walk lowers the indent bar on every block start.
        text = "if a:\n    if b:\n        pass\n    with w:\n        pass\nelse:"
        assert levels_for(text) == [0]

    def test_candidates_are_not_a_contiguous_chain(self) -> None:
        # Candidates are the real opener columns, not offset multiples:
        # with an (unconventional) 8-indented inner if, the levels skip 4.
        text = "if a:\n        if b:\n                pass\nelse:"
        assert levels_for(text) == [8, 0]
