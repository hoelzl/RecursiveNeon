"""
Command-line tokenizer for the shell.

Splits a raw input line into argv-style tokens, handling:
- Double quotes: "hello world" → hello world
- Single quotes: 'hello world' → hello world
- Backslash escapes: hello\\ world → hello world
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Token:
    """A parsed token with quoting metadata.

    Attributes:
        value: The unquoted/unescaped string value.
        quoted: True if any part of the token was inside quotes or
            preceded by a backslash escape.  Quoted tokens should not
            undergo glob expansion.
    """

    value: str
    quoted: bool


def tokenize(line: str) -> list[str]:
    """Tokenize a command line into argv-style arguments.

    This is a convenience wrapper around :func:`tokenize_ext` that
    returns plain strings (discarding quoting metadata).

    Args:
        line: Raw input string.

    Returns:
        List of token strings. Empty list if line is blank or only whitespace.

    Raises:
        ValueError: If quotes are not properly closed.
    """
    return [t.value for t in tokenize_ext(line)]


def tokenize_ext(line: str) -> list[Token]:
    """Tokenize a command line, preserving quoting metadata.

    Each returned :class:`Token` carries a ``quoted`` flag that is
    ``True`` when any part of the token was inside quotes or preceded
    by a backslash escape.  The shell uses this to suppress glob
    expansion on quoted tokens.

    Args:
        line: Raw input string.

    Returns:
        List of :class:`Token` objects.

    Raises:
        ValueError: If quotes are not properly closed.
    """
    tokens: list[Token] = []
    current: list[str] = []
    in_token = False  # Tracks whether we've started a token (for empty quotes)
    is_quoted = False  # Any part of this token was quoted/escaped
    i = 0
    n = len(line)

    while i < n:
        ch = line[i]

        if ch == "\\" and i + 1 < n:
            # Escaped character — take the next char literally
            current.append(line[i + 1])
            in_token = True
            is_quoted = True
            i += 2

        elif ch == '"':
            # Double-quoted string — take everything until closing quote
            in_token = True  # Even empty quotes produce a token
            is_quoted = True
            i += 1
            while i < n and line[i] != '"':
                if line[i] == "\\" and i + 1 < n:
                    # Backslash escapes inside double quotes
                    current.append(line[i + 1])
                    i += 2
                else:
                    current.append(line[i])
                    i += 1
            if i >= n:
                raise ValueError("Unterminated double quote")
            i += 1  # Skip closing quote

        elif ch == "'":
            # Single-quoted string — take everything literally until closing quote
            in_token = True  # Even empty quotes produce a token
            is_quoted = True
            i += 1
            while i < n and line[i] != "'":
                current.append(line[i])
                i += 1
            if i >= n:
                raise ValueError("Unterminated single quote")
            i += 1  # Skip closing quote

        elif ch in (" ", "\t"):
            # Whitespace — end current token
            if in_token:
                tokens.append(Token(value="".join(current), quoted=is_quoted))
                current = []
                in_token = False
                is_quoted = False
            i += 1

        else:
            current.append(ch)
            in_token = True
            i += 1

    # Don't forget the last token
    if in_token:
        tokens.append(Token(value="".join(current), quoted=is_quoted))

    return tokens
