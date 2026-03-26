"""
Command-line tokenizer and pipeline parser for the shell.

Splits a raw input line into argv-style tokens, handling:
- Double quotes: "hello world" → hello world
- Single quotes: 'hello world' → hello world
- Backslash escapes: hello\\ world → hello world
- Pipes: cmd1 | cmd2
- Output redirection: cmd > file, cmd >> file
"""

from __future__ import annotations

from dataclasses import dataclass, field


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


# ---------------------------------------------------------------------------
# Pipeline parsing — pipes and output redirection
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Redirect:
    """Output redirection target."""

    mode: str  # ">" or ">>"
    target: str  # Filename (after tokenization)


@dataclass(slots=True)
class PipelineSegment:
    """One command in a pipeline."""

    raw: str  # Raw text of this segment
    tokens: list[Token] = field(default_factory=list)


@dataclass(slots=True)
class Pipeline:
    """A parsed command line that may contain pipes and/or redirection."""

    segments: list[PipelineSegment]
    redirect: Redirect | None = None


def parse_pipeline(line: str) -> Pipeline:
    """Parse a command line into pipe segments and optional redirection.

    Splits *line* at unquoted ``|``, ``>``, and ``>>`` operators.
    Each segment is tokenized independently via :func:`tokenize_ext`.

    Args:
        line: Raw input string.

    Returns:
        A :class:`Pipeline` with one or more segments and an optional
        :class:`Redirect`.

    Raises:
        ValueError: On syntax errors (empty segments, missing redirect
            target, unterminated quotes).
    """
    # Walk the line, tracking quote state, to find unquoted operators
    segments_raw: list[str] = []
    redirect: Redirect | None = None
    current_start = 0
    i = 0
    n = len(line)

    while i < n:
        ch = line[i]

        if ch == "\\" and i + 1 < n:
            i += 2  # skip escaped char

        elif ch == '"':
            i += 1
            while i < n and line[i] != '"':
                if line[i] == "\\" and i + 1 < n:
                    i += 2
                else:
                    i += 1
            if i >= n:
                raise ValueError("Unterminated double quote")
            i += 1  # skip closing

        elif ch == "'":
            i += 1
            while i < n and line[i] != "'":
                i += 1
            if i >= n:
                raise ValueError("Unterminated single quote")
            i += 1  # skip closing

        elif ch == "|":
            if redirect is not None:
                raise ValueError("Cannot pipe after redirection")
            segment_text = line[current_start:i]
            if not segment_text.strip():
                raise ValueError("Empty command before |")
            segments_raw.append(segment_text)
            i += 1
            current_start = i

        elif ch == ">":
            if redirect is not None:
                raise ValueError("Multiple redirections")
            segment_text = line[current_start:i]
            if not segment_text.strip():
                raise ValueError("Empty command before >")
            segments_raw.append(segment_text)

            # Check for >> (append)
            if i + 1 < n and line[i + 1] == ">":
                mode = ">>"
                i += 2
            else:
                mode = ">"
                i += 1

            # Everything after the redirect operator is the target
            target_text = line[i:].strip()
            if not target_text:
                raise ValueError("Missing redirect target")
            target_tokens = tokenize(target_text)
            if len(target_tokens) != 1:
                raise ValueError("Redirect target must be a single filename")
            redirect = Redirect(mode=mode, target=target_tokens[0])
            # Consumed the rest of the line
            current_start = n
            break

        else:
            i += 1

    # Grab the last segment (if not consumed by redirect)
    remaining = line[current_start:].strip()
    if remaining:
        segments_raw.append(line[current_start:])
    elif segments_raw and redirect is None:
        # We had pipe(s) but nothing after the last one
        raise ValueError("Empty command after |")
    elif not segments_raw:
        # Completely empty line
        return Pipeline(segments=[PipelineSegment(raw="", tokens=[])])

    # Tokenize each segment
    segments: list[PipelineSegment] = []
    for raw in segments_raw:
        tokens = tokenize_ext(raw.strip())
        if not tokens:
            raise ValueError("Empty command in pipeline")
        segments.append(PipelineSegment(raw=raw, tokens=tokens))

    return Pipeline(segments=segments, redirect=redirect)
