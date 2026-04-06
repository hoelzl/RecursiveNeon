"""
ANSI parser — convert ANSI-encoded text to plain text + attributes.

Handles SGR (Select Graphic Rendition) escape sequences.  Non-SGR
sequences are silently stripped.
"""

from __future__ import annotations

import re

from recursive_neon.editor.text_attr import TextAttr

# Matches any CSI sequence: ESC [ <params> <final byte>
_CSI_RE = re.compile(r"\033\[([0-9;]*)([a-zA-Z])")

# Standard colour indices (SGR 30-37 / 40-47)
_STANDARD_FG_BASE = 30
_STANDARD_BG_BASE = 40
_BRIGHT_FG_BASE = 90
_BRIGHT_BG_BASE = 100


def parse_ansi(text: str) -> list[tuple[str, TextAttr | None]]:
    """Parse ANSI-encoded text into a list of (text, attr) runs.

    Each run is a ``(plain_text, attr)`` pair.  ``attr`` is ``None``
    when the text uses default terminal styling.

    Example::

        parse_ansi("\\033[31mhello\\033[0m world")
        # → [("hello", TextAttr(fg=1)), (" world", None)]
    """
    runs: list[tuple[str, TextAttr | None]] = []
    current_attr = _DEFAULT_ATTR
    pos = 0
    buf: list[str] = []

    while pos < len(text):
        m = _CSI_RE.search(text, pos)
        if m is None:
            # No more escape sequences — rest is plain text
            buf.append(text[pos:])
            break

        # Text before the escape sequence
        if m.start() > pos:
            buf.append(text[pos : m.start()])

        # Process the escape sequence
        params_str = m.group(1)
        final_byte = m.group(2)
        pos = m.end()

        if final_byte != "m":
            # Not an SGR sequence — skip it
            continue

        # Flush current buffer before changing attributes
        if buf:
            chunk = "".join(buf)
            if chunk:
                attr = current_attr if current_attr != _DEFAULT_ATTR else None
                runs.append((chunk, attr))
            buf.clear()

        # Parse SGR parameters
        current_attr = _apply_sgr(current_attr, params_str)

    # Flush remaining text
    if buf:
        chunk = "".join(buf)
        if chunk:
            attr = current_attr if current_attr != _DEFAULT_ATTR else None
            runs.append((chunk, attr))

    return runs if runs else [("", None)]


def parse_ansi_to_text_and_attrs(
    text: str,
) -> tuple[str, list[list[TextAttr | None]]]:
    """Parse ANSI text into plain text + per-line attr lists.

    Returns ``(plain_text, line_attrs)`` where ``line_attrs[i]`` has
    the same length as ``plain_text.split('\\n')[i]``.
    """
    runs = parse_ansi(text)
    # Build flat text and flat attrs
    plain_parts: list[str] = []
    flat_attrs: list[TextAttr | None] = []
    for chunk, attr in runs:
        plain_parts.append(chunk)
        flat_attrs.extend([attr] * len(chunk))
    plain = "".join(plain_parts)

    # Split into lines
    lines = plain.split("\n")
    line_attrs: list[list[TextAttr | None]] = []
    offset = 0
    for line in lines:
        line_attrs.append(flat_attrs[offset : offset + len(line)])
        offset += len(line) + 1  # +1 for the '\n'
    return plain, line_attrs


# Sentinel for "no styling"
_DEFAULT_ATTR = TextAttr()


def _apply_sgr(current: TextAttr, params_str: str) -> TextAttr:
    """Apply SGR parameter codes to the current attribute."""
    if not params_str:
        # ESC[m is equivalent to ESC[0m (reset)
        return _DEFAULT_ATTR

    codes = [int(c) if c else 0 for c in params_str.split(";")]
    fg = current.fg
    bg = current.bg
    bold = current.bold
    dim = current.dim
    italic = current.italic
    underline = current.underline
    reverse = current.reverse

    i = 0
    while i < len(codes):
        c = codes[i]
        if c == 0:
            # Reset all
            return _DEFAULT_ATTR
        elif c == 1:
            bold = True
        elif c == 2:
            dim = True
        elif c == 3:
            italic = True
        elif c == 4:
            underline = True
        elif c == 7:
            reverse = True
        elif c == 22:
            bold = False
            dim = False
        elif c == 23:
            italic = False
        elif c == 24:
            underline = False
        elif c == 27:
            reverse = False
        elif 30 <= c <= 37:
            fg = c - _STANDARD_FG_BASE
        elif c == 38:
            # Extended foreground: 38;5;N (256-colour)
            if i + 2 < len(codes) and codes[i + 1] == 5:
                fg = codes[i + 2]
                i += 2
        elif c == 39:
            fg = None  # default fg
        elif 40 <= c <= 47:
            bg = c - _STANDARD_BG_BASE
        elif c == 48:
            # Extended background: 48;5;N (256-colour)
            if i + 2 < len(codes) and codes[i + 1] == 5:
                bg = codes[i + 2]
                i += 2
        elif c == 49:
            bg = None  # default bg
        elif 90 <= c <= 97:
            fg = c - _BRIGHT_FG_BASE + 8  # bright colours are 8-15
        elif 100 <= c <= 107:
            bg = c - _BRIGHT_BG_BASE + 8
        i += 1

    return TextAttr(
        fg=fg,
        bg=bg,
        bold=bold,
        dim=dim,
        italic=italic,
        underline=underline,
        reverse=reverse,
    )
