"""Tests for Markdown syntax highlighting mode."""

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

register_language_modes()


def _spans_for_line(line: str) -> list[tuple[int, int, str]]:
    mode = MODES["markdown-mode"]
    return EditorView._match_syntax_rules(line, mode.syntax_rules)


def _face_at(spans: list[tuple[int, int, str]], col: int) -> str | None:
    for start, width, face in spans:
        if start <= col < start + width:
            return face
    return None


class TestMarkdownModeRegistration:
    def test_markdown_mode_registered(self):
        assert "markdown-mode" in MODES

    def test_has_syntax_rules(self):
        assert len(MODES["markdown-mode"].syntax_rules) > 0

    def test_auto_mode_md(self):
        assert AUTO_MODE_ALIST.get(".md") == "markdown-mode"

    def test_auto_mode_markdown(self):
        assert AUTO_MODE_ALIST.get(".markdown") == "markdown-mode"

    def test_detect_mode_md(self):
        assert detect_mode("README.md") == "markdown-mode"

    def test_auto_fill_enabled(self):
        assert MODES["markdown-mode"].variables.get("auto-fill") is True


class TestMarkdownHeadings:
    def test_h1(self):
        spans = _spans_for_line("# Heading 1")
        assert _face_at(spans, 0) == "heading"
        assert _face_at(spans, 5) == "heading"

    def test_h2(self):
        spans = _spans_for_line("## Heading 2")
        assert _face_at(spans, 0) == "heading"

    def test_h3(self):
        spans = _spans_for_line("### Heading 3")
        assert _face_at(spans, 0) == "heading"

    def test_h6(self):
        spans = _spans_for_line("###### Heading 6")
        assert _face_at(spans, 0) == "heading"

    def test_not_heading_without_space(self):
        spans = _spans_for_line("#notaheading")
        assert _face_at(spans, 0) != "heading"


class TestMarkdownInlineCode:
    def test_backtick_span(self):
        spans = _spans_for_line("Use `foo()` here")
        assert _face_at(spans, 4) == "code"
        assert _face_at(spans, 10) == "code"

    def test_text_outside_code_not_highlighted(self):
        spans = _spans_for_line("Use `foo()` here")
        assert _face_at(spans, 0) is None
        assert _face_at(spans, 12) is None


class TestMarkdownFencedCode:
    def test_fence_delimiter(self):
        spans = _spans_for_line("```python")
        assert _face_at(spans, 0) == "code"

    def test_closing_fence(self):
        spans = _spans_for_line("```")
        assert _face_at(spans, 0) == "code"


class TestMarkdownBoldItalic:
    def test_bold_asterisks(self):
        spans = _spans_for_line("This is **bold** text")
        assert _face_at(spans, 8) == "bold"

    def test_bold_underscores(self):
        spans = _spans_for_line("This is __bold__ text")
        assert _face_at(spans, 8) == "bold"

    def test_italic_asterisk(self):
        spans = _spans_for_line("This is *italic* text")
        assert _face_at(spans, 8) == "italic"

    def test_italic_underscore(self):
        spans = _spans_for_line("This is _italic_ text")
        assert _face_at(spans, 8) == "italic"


class TestMarkdownLinks:
    def test_inline_link(self):
        spans = _spans_for_line("[text](https://example.com)")
        assert _face_at(spans, 0) == "link"

    def test_reference_link(self):
        spans = _spans_for_line("[text][ref]")
        assert _face_at(spans, 0) == "link"


class TestMarkdownRendering:
    def test_syntax_spans_in_screen(self):
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(
            name="readme.md",
            text="# Title\n\nSome **bold** text.\n",
            filepath="readme.md",
        )
        ed.set_major_mode("markdown-mode")
        view = EditorView(editor=ed)
        screen = view.on_start(80, 24)
        # Heading line should have ANSI codes
        assert "\033[" in screen.lines[0]
