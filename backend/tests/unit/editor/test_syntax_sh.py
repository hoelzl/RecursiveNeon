"""Tests for shell-script syntax highlighting mode."""

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
    mode = MODES["sh-mode"]
    return EditorView._match_syntax_rules(line, mode.syntax_rules)


def _face_at(spans: list[tuple[int, int, str]], col: int) -> str | None:
    for start, width, face in spans:
        if start <= col < start + width:
            return face
    return None


class TestShModeRegistration:
    def test_sh_mode_registered(self):
        assert "sh-mode" in MODES

    def test_has_syntax_rules(self):
        assert len(MODES["sh-mode"].syntax_rules) > 0

    def test_auto_mode_sh(self):
        assert AUTO_MODE_ALIST.get(".sh") == "sh-mode"

    def test_auto_mode_bash(self):
        assert AUTO_MODE_ALIST.get(".bash") == "sh-mode"

    def test_auto_mode_zsh(self):
        assert AUTO_MODE_ALIST.get(".zsh") == "sh-mode"

    def test_detect_mode_sh(self):
        assert detect_mode("script.sh") == "sh-mode"


class TestShComments:
    def test_full_line_comment(self):
        spans = _spans_for_line("# comment here")
        assert _face_at(spans, 0) == "comment"
        assert _face_at(spans, 5) == "comment"

    def test_inline_comment(self):
        spans = _spans_for_line("echo hello  # inline")
        assert _face_at(spans, 12) == "comment"


class TestShKeywords:
    def test_if(self):
        spans = _spans_for_line("if [ -f file ]; then")
        assert _face_at(spans, 0) == "keyword"

    def test_then(self):
        spans = _spans_for_line("if [ -f file ]; then")
        assert _face_at(spans, 16) == "keyword"

    def test_fi(self):
        spans = _spans_for_line("fi")
        assert _face_at(spans, 0) == "keyword"

    def test_for(self):
        spans = _spans_for_line("for x in 1 2 3; do")
        assert _face_at(spans, 0) == "keyword"

    def test_while(self):
        spans = _spans_for_line("while true; do")
        assert _face_at(spans, 0) == "keyword"

    def test_case_esac(self):
        for kw in ("case", "esac"):
            spans = _spans_for_line(f"{kw} x")
            assert _face_at(spans, 0) == "keyword", f"Expected keyword for {kw}"


class TestShBuiltins:
    def test_echo(self):
        spans = _spans_for_line("echo hello")
        assert _face_at(spans, 0) == "builtin"

    def test_cd(self):
        spans = _spans_for_line("cd /tmp")
        assert _face_at(spans, 0) == "builtin"

    def test_export(self):
        spans = _spans_for_line("export FOO=bar")
        assert _face_at(spans, 0) == "builtin"

    def test_exit(self):
        spans = _spans_for_line("exit 0")
        assert _face_at(spans, 0) == "builtin"


class TestShStrings:
    def test_double_quoted(self):
        spans = _spans_for_line('echo "hello world"')
        assert _face_at(spans, 5) == "string"

    def test_single_quoted(self):
        spans = _spans_for_line("echo 'hello world'")
        assert _face_at(spans, 5) == "string"

    def test_keyword_in_string_not_highlighted(self):
        spans = _spans_for_line('echo "if then fi"')
        # "if" at col 6 is inside a string
        assert _face_at(spans, 6) == "string"


class TestShVariables:
    def test_dollar_var(self):
        spans = _spans_for_line("echo $HOME")
        assert _face_at(spans, 5) == "sh-variable"

    def test_braced_var(self):
        spans = _spans_for_line("echo ${HOME}")
        assert _face_at(spans, 5) == "sh-variable"

    def test_special_vars(self):
        for var in ("$@", "$#", "$?", "$!"):
            spans = _spans_for_line(f"echo {var}")
            assert _face_at(spans, 5) == "sh-variable", (
                f"Expected sh-variable for {var}"
            )

    def test_positional_param(self):
        spans = _spans_for_line("echo $1")
        assert _face_at(spans, 5) == "sh-variable"


class TestShRedirections:
    def test_output_redirect(self):
        spans = _spans_for_line("echo hello > file.txt")
        assert _face_at(spans, 11) == "sh-redirect"

    def test_append_redirect(self):
        spans = _spans_for_line("echo hello >> file.txt")
        assert _face_at(spans, 11) == "sh-redirect"


class TestShNumbers:
    def test_integer(self):
        spans = _spans_for_line("exit 42")
        assert _face_at(spans, 5) == "number"


class TestShRendering:
    def test_syntax_spans_in_screen(self):
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(
            name="test.sh",
            text="#!/bin/bash\necho hello\n",
            filepath="test.sh",
        )
        ed.set_major_mode("sh-mode")
        view = EditorView(editor=ed)
        screen = view.on_start(80, 24)
        # The shebang line has a comment; echo line has builtins
        assert "\033[" in screen.lines[0] or "\033[" in screen.lines[1]
