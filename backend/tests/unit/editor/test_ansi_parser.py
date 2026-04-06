"""Tests for the ANSI parser (Phase 7a-2)."""

from recursive_neon.editor.ansi_parser import parse_ansi, parse_ansi_to_text_and_attrs
from recursive_neon.editor.text_attr import TextAttr


class TestParseAnsi:
    def test_plain_text(self):
        runs = parse_ansi("hello world")
        assert runs == [("hello world", None)]

    def test_empty(self):
        runs = parse_ansi("")
        assert runs == [("", None)]

    def test_single_color(self):
        runs = parse_ansi("\033[31mred\033[0m")
        assert len(runs) == 1
        text, attr = runs[0]
        assert text == "red"
        assert attr is not None
        assert attr.fg == 1  # 31 - 30

    def test_color_then_reset(self):
        runs = parse_ansi("\033[31mred\033[0m normal")
        assert len(runs) == 2
        assert runs[0][0] == "red"
        assert runs[0][1] is not None and runs[0][1].fg == 1
        assert runs[1][0] == " normal"
        assert runs[1][1] is None

    def test_bold(self):
        runs = parse_ansi("\033[1mbold\033[0m")
        assert runs[0][1] is not None
        assert runs[0][1].bold

    def test_combined_codes(self):
        runs = parse_ansi("\033[1;31mbold red\033[0m")
        attr = runs[0][1]
        assert attr is not None
        assert attr.bold
        assert attr.fg == 1

    def test_bright_colors(self):
        runs = parse_ansi("\033[91mbright red\033[0m")
        attr = runs[0][1]
        assert attr is not None
        assert attr.fg == 9  # 91 - 90 + 8

    def test_256_color(self):
        runs = parse_ansi("\033[38;5;196mext red\033[0m")
        attr = runs[0][1]
        assert attr is not None
        assert attr.fg == 196

    def test_bg_color(self):
        runs = parse_ansi("\033[44mblue bg\033[0m")
        attr = runs[0][1]
        assert attr is not None
        assert attr.bg == 4

    def test_256_bg_color(self):
        runs = parse_ansi("\033[48;5;220myellow bg\033[0m")
        attr = runs[0][1]
        assert attr is not None
        assert attr.bg == 220

    def test_multiple_segments(self):
        runs = parse_ansi("\033[31mred\033[32mgreen\033[0mnormal")
        assert len(runs) == 3
        assert runs[0][0] == "red"
        assert runs[0][1].fg == 1  # type: ignore[union-attr]
        assert runs[1][0] == "green"
        assert runs[1][1].fg == 2  # type: ignore[union-attr]
        assert runs[2][0] == "normal"
        assert runs[2][1] is None

    def test_non_sgr_stripped(self):
        # ESC[2J is clear screen — should be stripped, not parsed as SGR
        runs = parse_ansi("\033[2Jhello")
        assert runs == [("hello", None)]

    def test_bare_reset(self):
        # ESC[m is equivalent to ESC[0m
        runs = parse_ansi("\033[1mbold\033[mnormal")
        assert runs[0][1] is not None and runs[0][1].bold
        assert runs[1][1] is None

    def test_underline_and_reverse(self):
        runs = parse_ansi("\033[4;7mfancy\033[0m")
        attr = runs[0][1]
        assert attr is not None
        assert attr.underline
        assert attr.reverse

    def test_default_fg_reset(self):
        runs = parse_ansi("\033[31mred\033[39mdefault")
        assert runs[0][1] is not None and runs[0][1].fg == 1
        assert runs[1][1] is None  # fg=None → default attr


class TestParseAnsiToTextAndAttrs:
    def test_plain_text(self):
        text, attrs = parse_ansi_to_text_and_attrs("hello")
        assert text == "hello"
        assert attrs == [[None, None, None, None, None]]

    def test_single_line_colored(self):
        text, attrs = parse_ansi_to_text_and_attrs("\033[31mhey\033[0m")
        assert text == "hey"
        assert len(attrs) == 1
        assert all(a is not None and a.fg == 1 for a in attrs[0])

    def test_multiline(self):
        text, attrs = parse_ansi_to_text_and_attrs("abc\ndef")
        assert text == "abc\ndef"
        assert len(attrs) == 2
        assert len(attrs[0]) == 3
        assert len(attrs[1]) == 3

    def test_multiline_with_color(self):
        text, attrs = parse_ansi_to_text_and_attrs("\033[31mab\ncd\033[0m")
        assert text == "ab\ncd"
        assert len(attrs) == 2
        red = TextAttr(fg=1)
        assert attrs[0] == [red, red]
        assert attrs[1] == [red, red]
