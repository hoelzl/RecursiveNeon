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


def _skip_double_quoted(text: str, i: int) -> tuple[int, bool]:
    """Advance index past a ``"..."`` section starting after the opening ``"``.

    Handles backslash escapes inside double quotes.  Returns ``(new_i, closed)``
    where *new_i* is the index just past the closing ``"`` and *closed* is
    ``True`` if a closing quote was found.

    This is the single source of truth for double-quote skipping.  Used by
    ``_last_pipe_segment``, ``parse_pipeline``, and ``get_current_argument``.
    """
    n = len(text)
    while i < n and text[i] != '"':
        if text[i] == "\\" and i + 1 < n:
            i += 2
        else:
            i += 1
    if i < n:
        return i + 1, True  # skip closing quote
    return i, False


def _skip_single_quoted(text: str, i: int) -> tuple[int, bool]:
    """Advance index past a ``'...'`` section starting after the opening ``'``.

    Returns ``(new_i, closed)`` where *new_i* is the index just past the
    closing ``'`` and *closed* is ``True`` if a closing quote was found.
    """
    n = len(text)
    while i < n and text[i] != "'":
        i += 1
    if i < n:
        return i + 1, True  # skip closing quote
    return i, False


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
    """Output redirection target.

    Attributes:
        mode: ``">"`` (overwrite) or ``">>"`` (append).
        target: Filename (after tokenization), or ``"&1"`` for fd merging.
        fd: File descriptor being redirected: ``1`` for stdout,
            ``2`` for stderr.
    """

    mode: str  # ">" or ">>"
    target: str  # Filename (after tokenization), or "&1" for merge
    fd: int = 1  # 1 = stdout, 2 = stderr


@dataclass(slots=True)
class PipelineSegment:
    """One command in a pipeline."""

    raw: str  # Raw text of this segment
    tokens: list[Token] = field(default_factory=list)


@dataclass(slots=True)
class Pipeline:
    """A parsed command line that may contain pipes and/or redirection.

    Attributes:
        segments: One or more pipe-separated commands.
        redirect: Stdout redirection (fd=1), if any.
        stderr_redirect: Stderr redirection (fd=2), if any.  When the
            target is ``"&1"`` this means "merge stderr into stdout".
    """

    segments: list[PipelineSegment]
    redirect: Redirect | None = None
    stderr_redirect: Redirect | None = None


def parse_pipeline(line: str) -> Pipeline:
    """Parse a command line into pipe segments and optional redirection.

    Splits *line* at unquoted ``|``, ``>``, ``>>``, ``2>``, ``2>>``,
    and ``2>&1`` operators.  Each segment is tokenized independently
    via :func:`tokenize_ext`.

    Args:
        line: Raw input string.

    Returns:
        A :class:`Pipeline` with one or more segments, an optional
        stdout :class:`Redirect`, and an optional stderr
        :class:`Redirect`.

    Raises:
        ValueError: On syntax errors (empty segments, missing redirect
            target, unterminated quotes).
    """
    # Walk the line, tracking quote state, to find unquoted operators
    segments_raw: list[str] = []
    redirect: Redirect | None = None
    stderr_redirect: Redirect | None = None
    current_start = 0
    i = 0
    n = len(line)

    while i < n:
        ch = line[i]

        if ch == "\\" and i + 1 < n:
            i += 2  # skip escaped char

        elif ch == '"':
            i, closed = _skip_double_quoted(line, i + 1)
            if not closed:
                raise ValueError("Unterminated double quote")

        elif ch == "'":
            i, closed = _skip_single_quoted(line, i + 1)
            if not closed:
                raise ValueError("Unterminated single quote")

        elif ch == "|":
            if redirect is not None:
                raise ValueError("Cannot pipe after redirection")
            segment_text = line[current_start:i]
            if not segment_text.strip() and not segments_raw:
                raise ValueError("Empty command before |")
            if segment_text.strip():
                segments_raw.append(segment_text)
            i += 1
            current_start = i

        elif ch == "2" and i + 1 < n and line[i + 1] == ">":
            # stderr redirection: 2>, 2>>, 2>&1
            if stderr_redirect is not None:
                raise ValueError("Multiple stderr redirections")
            segment_text = line[current_start:i]
            if not segment_text.strip() and not segments_raw:
                raise ValueError("Empty command before 2>")
            if segment_text.strip():
                segments_raw.append(segment_text)

            i += 2  # skip "2>"

            # Check for 2>> (append)
            if i < n and line[i] == ">":
                mode = ">>"
                i += 1
            else:
                mode = ">"

            # Check for 2>&1 (merge stderr into stdout)
            remaining_after = line[i:].lstrip()
            if remaining_after.startswith("&1"):
                stderr_redirect = Redirect(mode=mode, target="&1", fd=2)
                i = line.index("&1", i) + 2
                current_start = i
                continue

            # Everything up to the next operator is the target
            target_text, consumed = _extract_redirect_target(line, i)
            if not target_text:
                raise ValueError("Missing stderr redirect target")
            stderr_redirect = Redirect(mode=mode, target=target_text, fd=2)
            i += consumed
            current_start = i

        elif ch == ">":
            if redirect is not None:
                raise ValueError("Multiple stdout redirections")
            segment_text = line[current_start:i]
            if not segment_text.strip() and not segments_raw:
                raise ValueError("Empty command before >")
            if segment_text.strip():
                segments_raw.append(segment_text)

            # Check for >> (append)
            if i + 1 < n and line[i + 1] == ">":
                mode = ">>"
                i += 2
            else:
                mode = ">"
                i += 1

            # Everything up to the next operator is the target
            target_text, consumed = _extract_redirect_target(line, i)
            if not target_text:
                raise ValueError("Missing redirect target")
            redirect = Redirect(mode=mode, target=target_text, fd=1)
            i += consumed
            current_start = i

        else:
            i += 1

    # Grab the last segment (if not consumed by redirect)
    remaining = line[current_start:].strip()
    if remaining:
        segments_raw.append(line[current_start:])
    elif segments_raw and redirect is None and stderr_redirect is None:
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

    return Pipeline(
        segments=segments,
        redirect=redirect,
        stderr_redirect=stderr_redirect,
    )


def _extract_redirect_target(line: str, start: int) -> tuple[str, int]:
    """Extract a redirect target starting at *start* in *line*.

    Reads a single token (respecting quotes), stopping at whitespace
    or a redirect/pipe operator.  The remainder of the line after the
    target is left for the main ``parse_pipeline`` loop to process.

    Returns:
        ``(target, chars_consumed)`` where *target* is the unquoted
        filename and *chars_consumed* is how far past *start* we read.

    Raises:
        ValueError: If the target is empty or contains multiple tokens.
    """
    # Skip leading whitespace
    i = start
    n = len(line)
    while i < n and line[i] in (" ", "\t"):
        i += 1

    if i >= n:
        return "", i - start

    # Find end of the target token
    token_start = i
    in_dq = False
    in_sq = False
    while i < n:
        ch = line[i]
        if in_dq:
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == '"':
                in_dq = False
            i += 1
            continue
        if in_sq:
            if ch == "'":
                in_sq = False
            i += 1
            continue
        if ch == '"':
            in_dq = True
            i += 1
            continue
        if ch == "'":
            in_sq = True
            i += 1
            continue
        if ch in (" ", "\t"):
            break
        i += 1

    token_text = line[token_start:i].strip()
    if not token_text:
        return "", i - start

    # Tokenize to strip quotes
    tokens = tokenize(token_text)
    if len(tokens) != 1:
        raise ValueError("Redirect target must be a single filename")

    # Check that what follows is either EOL, whitespace + another
    # operator, or another redirect — NOT another plain word.
    j = i
    while j < n and line[j] in (" ", "\t"):
        j += 1
    if (
        j < n
        and line[j] not in ("|", ">")
        and not (j + 1 < n and line[j] == "2" and line[j + 1] == ">")
    ):
        # There's another token after the target that isn't an operator
        raise ValueError("Redirect target must be a single filename")

    return tokens[0], i - start
