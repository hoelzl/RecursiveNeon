"""Tests for Python syntax highlighting mode."""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.modes import (
    AUTO_MODE_ALIST,
    MODES,
    detect_mode,
    register_language_modes,
)
from recursive_neon.editor.view import EditorView

# Ensure language modes are registered
register_language_modes()


def _spans_for_line(line: str) -> list[tuple[int, int, str]]:
    """Return syntax highlight spans for a line under python-mode."""
    mode = MODES["python-mode"]
    return EditorView._match_syntax_rules(line, mode.syntax_rules)


def _face_at(spans: list[tuple[int, int, str]], col: int) -> str | None:
    """Return the face name covering *col*, or None."""
    for start, width, face in spans:
        if start <= col < start + width:
            return face
    return None


class TestPythonModeRegistration:
    def test_python_mode_registered(self):
        assert "python-mode" in MODES

    def test_python_mode_has_syntax_rules(self):
        assert len(MODES["python-mode"].syntax_rules) > 0

    def test_auto_mode_py(self):
        assert AUTO_MODE_ALIST.get(".py") == "python-mode"

    def test_auto_mode_pyi(self):
        assert AUTO_MODE_ALIST.get(".pyi") == "python-mode"

    def test_detect_mode_py(self):
        assert detect_mode("foo.py") == "python-mode"

    def test_detect_mode_unknown(self):
        assert detect_mode("foo.xyz") == "fundamental-mode"


class TestPythonKeywords:
    def test_def_highlighted(self):
        spans = _spans_for_line("def foo():")
        assert _face_at(spans, 0) == "keyword"

    def test_class_highlighted(self):
        spans = _spans_for_line("class Bar:")
        assert _face_at(spans, 0) == "keyword"

    def test_return_highlighted(self):
        spans = _spans_for_line("    return x")
        assert _face_at(spans, 4) == "keyword"

    def test_if_elif_else(self):
        for kw in ("if", "elif", "else"):
            spans = _spans_for_line(f"{kw} x:")
            assert _face_at(spans, 0) == "keyword", f"Expected keyword for {kw}"

    def test_import_highlighted(self):
        spans = _spans_for_line("import os")
        assert _face_at(spans, 0) == "keyword"

    def test_for_while_highlighted(self):
        for kw in ("for", "while"):
            spans = _spans_for_line(f"{kw} x:")
            assert _face_at(spans, 0) == "keyword"

    def test_true_false_none(self):
        for kw in ("True", "False", "None"):
            spans = _spans_for_line(f"x = {kw}")
            assert _face_at(spans, 4) == "keyword", f"Expected keyword for {kw}"


class TestPythonStrings:
    def test_double_quoted(self):
        spans = _spans_for_line('x = "hello"')
        assert _face_at(spans, 4) == "string"

    def test_single_quoted(self):
        spans = _spans_for_line("x = 'world'")
        assert _face_at(spans, 4) == "string"

    def test_fstring(self):
        spans = _spans_for_line('x = f"hello {name}"')
        assert _face_at(spans, 4) == "string"

    def test_escaped_quote(self):
        spans = _spans_for_line(r'x = "he said \"hi\""')
        assert _face_at(spans, 4) == "string"


class TestPythonComments:
    def test_full_line_comment(self):
        spans = _spans_for_line("# this is a comment")
        assert _face_at(spans, 0) == "comment"
        assert _face_at(spans, 10) == "comment"

    def test_inline_comment(self):
        spans = _spans_for_line("x = 1  # inline")
        assert _face_at(spans, 7) == "comment"
        # The "1" should be a number, not a comment
        assert _face_at(spans, 4) != "comment"


class TestPythonNumbers:
    def test_integer(self):
        spans = _spans_for_line("x = 42")
        assert _face_at(spans, 4) == "number"

    def test_float(self):
        spans = _spans_for_line("x = 3.14")
        assert _face_at(spans, 4) == "number"

    def test_hex(self):
        spans = _spans_for_line("x = 0xFF")
        assert _face_at(spans, 4) == "number"


class TestPythonDecorators:
    def test_decorator(self):
        spans = _spans_for_line("@property")
        assert _face_at(spans, 0) == "decorator"

    def test_dotted_decorator(self):
        spans = _spans_for_line("@app.route")
        assert _face_at(spans, 0) == "decorator"


class TestPythonBuiltins:
    def test_print_highlighted(self):
        spans = _spans_for_line("print(x)")
        assert _face_at(spans, 0) == "builtin"

    def test_len_highlighted(self):
        spans = _spans_for_line("len(xs)")
        assert _face_at(spans, 0) == "builtin"

    def test_range_highlighted(self):
        spans = _spans_for_line("range(10)")
        assert _face_at(spans, 0) == "builtin"


class TestPythonFunctionClass:
    def test_function_name(self):
        spans = _spans_for_line("def my_func():")
        assert _face_at(spans, 4) == "function-name"

    def test_class_name(self):
        spans = _spans_for_line("class MyClass:")
        assert _face_at(spans, 6) == "type"


class TestPythonFirstMatchWins:
    def test_string_beats_keyword(self):
        """Keywords inside strings should not be highlighted as keywords."""
        spans = _spans_for_line('x = "return value"')
        # "return" at col 5 is inside a string
        assert _face_at(spans, 5) == "string"

    def test_comment_beats_keyword(self):
        """Keywords in comments should not be highlighted as keywords."""
        spans = _spans_for_line("# if True: pass")
        assert _face_at(spans, 2) == "comment"


class TestSyntaxCacheIntegration:
    """Verify the syntax cache in EditorView works."""

    def test_cache_hit_on_unchanged_line(self):
        """Same line content should reuse cached spans."""
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(
            name="test.py", text="def foo():\n    pass\n", filepath="test.py"
        )
        ed.set_major_mode("python-mode")
        view = EditorView(editor=ed)

        # First render populates cache
        view.on_start(80, 24)
        cache_size_1 = len(view._syntax_cache)
        assert cache_size_1 > 0

        # Second render should hit cache (same content)
        view.on_resize(80, 24)
        cache_size_2 = len(view._syntax_cache)
        assert cache_size_2 == cache_size_1

    def test_syntax_spans_appear_in_screen(self):
        """Verify that syntax highlighting actually shows up in rendered output."""
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(
            name="test.py", text="def foo():\n    pass\n", filepath="test.py"
        )
        ed.set_major_mode("python-mode")
        view = EditorView(editor=ed)
        screen = view.on_start(80, 24)

        # The first line should contain ANSI escape codes from syntax highlighting
        # "def" should be highlighted as keyword, "foo" as function-name
        line0 = screen.lines[0]
        assert "\033[" in line0, "Expected ANSI codes in syntax-highlighted line"
