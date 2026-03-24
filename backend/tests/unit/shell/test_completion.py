"""Tests for shell completion helpers."""

import pytest

from recursive_neon.shell.shell import _get_current_argument, _quote_path


@pytest.mark.unit
class TestGetCurrentArgument:
    """Test the quoting-aware argument parser for tab completion."""

    def test_simple_word(self):
        pos, raw = _get_current_argument("cat f")
        assert pos == 4
        assert raw == "f"

    def test_first_word(self):
        pos, raw = _get_current_argument("ls")
        assert pos == 0
        assert raw == "ls"

    def test_empty(self):
        pos, raw = _get_current_argument("")
        assert pos == 0
        assert raw == ""

    def test_after_space(self):
        """Cursor right after a space — new empty argument."""
        pos, raw = _get_current_argument("cat ")
        assert pos == 4
        assert raw == ""

    def test_double_quoted_path(self):
        pos, raw = _get_current_argument('cat "My Folder"/a')
        assert pos == 4
        assert raw == "My Folder/a"

    def test_single_quoted_path(self):
        pos, raw = _get_current_argument("cat 'My Folder'/a")
        assert pos == 4
        assert raw == "My Folder/a"

    def test_unclosed_double_quote(self):
        pos, raw = _get_current_argument('cat "My Fol')
        assert pos == 4
        assert raw == "My Fol"

    def test_closed_quoted_dir(self):
        pos, raw = _get_current_argument('cat "My Folder"/')
        assert pos == 4
        assert raw == "My Folder/"

    def test_backslash_escape(self):
        pos, raw = _get_current_argument("cat My\\ Folder/a")
        assert pos == 4
        assert raw == "My Folder/a"

    def test_absolute_path(self):
        pos, raw = _get_current_argument("cat /Documents/r")
        assert pos == 4
        assert raw == "/Documents/r"

    def test_multiple_spaces_between_args(self):
        pos, raw = _get_current_argument("cat   foo")
        assert pos == 6
        assert raw == "foo"

    def test_multiple_args_returns_last(self):
        pos, raw = _get_current_argument("cp /src /dest")
        assert pos == 8
        assert raw == "/dest"

    def test_arg_text_length(self):
        """The replace length = len(text) - arg_start."""
        text = 'cat "My Folder"/a'
        pos, raw = _get_current_argument(text)
        replace_len = len(text) - pos
        assert replace_len == 13  # len('"My Folder"/a')


@pytest.mark.unit
class TestQuotePath:
    """Test per-segment path quoting."""

    def test_no_quoting_needed(self):
        assert _quote_path("Documents/readme.txt") == "Documents/readme.txt"

    def test_quote_single_segment(self):
        assert (
            _quote_path("Documents/my test file.txt") == 'Documents/"my test file.txt"'
        )

    def test_quote_both_segments(self):
        assert (
            _quote_path("My Folder/another file.txt")
            == '"My Folder"/"another file.txt"'
        )

    def test_trailing_slash_preserved(self):
        assert _quote_path("My Folder/") == '"My Folder"/'

    def test_absolute_path(self):
        assert _quote_path("/Documents/readme.txt") == "/Documents/readme.txt"

    def test_absolute_path_with_spaces(self):
        assert (
            _quote_path("/My Folder/another file.txt")
            == '/"My Folder"/"another file.txt"'
        )

    def test_no_segments_need_quoting(self):
        assert _quote_path("Documents/") == "Documents/"

    def test_root_path(self):
        assert _quote_path("/") == "/"

    def test_segment_with_single_quote(self):
        assert _quote_path("file with 'quotes'.txt") == "\"file with 'quotes'.txt\""

    def test_segment_with_double_quote(self):
        assert _quote_path('file"name.txt') == '"file\\"name.txt"'
