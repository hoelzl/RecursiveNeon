"""
Command-line tokenizer for the shell.

Splits a raw input line into argv-style tokens, handling:
- Double quotes: "hello world" → hello world
- Single quotes: 'hello world' → hello world
- Backslash escapes: hello\\ world → hello world
"""

from __future__ import annotations


def tokenize(line: str) -> list[str]:
    """Tokenize a command line into argv-style arguments.

    Args:
        line: Raw input string.

    Returns:
        List of tokens. Empty list if line is blank or only whitespace.

    Raises:
        ValueError: If quotes are not properly closed.
    """
    tokens: list[str] = []
    current: list[str] = []
    in_token = False  # Tracks whether we've started a token (for empty quotes)
    i = 0
    n = len(line)

    while i < n:
        ch = line[i]

        if ch == "\\" and i + 1 < n:
            # Escaped character — take the next char literally
            current.append(line[i + 1])
            in_token = True
            i += 2

        elif ch == '"':
            # Double-quoted string — take everything until closing quote
            in_token = True  # Even empty quotes produce a token
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
                tokens.append("".join(current))
                current = []
                in_token = False
            i += 1

        else:
            current.append(ch)
            in_token = True
            i += 1

    # Don't forget the last token
    if in_token:
        tokens.append("".join(current))

    return tokens
