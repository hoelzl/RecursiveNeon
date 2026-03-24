"""Tests for the command-line tokenizer."""

import pytest

from recursive_neon.shell.parser import tokenize


@pytest.mark.unit
class TestTokenize:
    def test_empty_string(self):
        assert tokenize("") == []

    def test_whitespace_only(self):
        assert tokenize("   ") == []

    def test_single_word(self):
        assert tokenize("ls") == ["ls"]

    def test_multiple_words(self):
        assert tokenize("ls -l /Documents") == ["ls", "-l", "/Documents"]

    def test_double_quotes(self):
        assert tokenize('cat "my file.txt"') == ["cat", "my file.txt"]

    def test_single_quotes(self):
        assert tokenize("echo 'hello world'") == ["echo", "hello world"]

    def test_backslash_escape(self):
        assert tokenize("cat my\\ file.txt") == ["cat", "my file.txt"]

    def test_mixed_quotes(self):
        assert tokenize("""echo "hello" 'world'""") == ["echo", "hello", "world"]

    def test_empty_double_quotes(self):
        assert tokenize('echo ""') == ["echo", ""]

    def test_empty_single_quotes(self):
        assert tokenize("echo ''") == ["echo", ""]

    def test_backslash_in_double_quotes(self):
        assert tokenize('echo "hello\\"world"') == ["echo", 'hello"world']

    def test_adjacent_quoted_strings(self):
        assert tokenize('echo "hello""world"') == ["echo", "helloworld"]

    def test_tabs_as_whitespace(self):
        assert tokenize("ls\t-l") == ["ls", "-l"]

    def test_multiple_spaces_between_words(self):
        assert tokenize("ls    -l") == ["ls", "-l"]

    def test_unterminated_double_quote(self):
        with pytest.raises(ValueError, match="Unterminated double quote"):
            tokenize('echo "hello')

    def test_unterminated_single_quote(self):
        with pytest.raises(ValueError, match="Unterminated single quote"):
            tokenize("echo 'hello")

    def test_quoted_path_with_spaces(self):
        assert tokenize('cat "My Folder/another file.txt"') == [
            "cat",
            "My Folder/another file.txt",
        ]

    def test_backslash_at_end_of_line(self):
        # Trailing backslash with no next char — treated as literal
        assert tokenize("echo hello\\") == ["echo", "hello\\"]

    def test_special_characters_unquoted(self):
        assert tokenize("cat file.txt") == ["cat", "file.txt"]

    def test_file_with_quotes_in_name(self):
        assert tokenize("cat \"file with 'quotes'.txt\"") == [
            "cat",
            "file with 'quotes'.txt",
        ]
