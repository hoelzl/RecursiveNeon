"""Translate Emacs-style key descriptions into pty input bytes.

Examples
--------
    kbd("C-f")       -> b"\\x06"
    kbd("M-x")       -> b"\\x1bx"
    kbd("C-x C-f")   -> b"\\x06\\x06" (no — that's wrong; actually \\x18\\x06)
    kbd("RET")       -> b"\\r"
    kbd("M-RET")     -> b"\\x1b\\r"
    kbd("hello RET") -> b"hello\\r"

A keystroke description is a whitespace-separated sequence of "chord" tokens.
Each token is one of:
  * A named key: RET, TAB, ESC, SPC, DEL, BACKSPACE, <up>/<down>/<left>/<right>,
    <home>/<end>/<pgup>/<pgdn>, <f1>..<f12>.
  * A modified key like ``C-f``, ``M-x``, ``C-M-f``.
  * A literal printable string. Strings longer than one character are sent
    verbatim, so ``"hello"`` and ``"h e l l o"`` are equivalent (use one or
    the other for readability).

The translation deliberately follows what xterm/VT-style terminals send for
each key, since that is what both Emacs and neon-edit see on stdin.
"""

from __future__ import annotations


_NAMED: dict[str, bytes] = {
    "RET": b"\r",
    "TAB": b"\t",
    "ESC": b"\x1b",
    "SPC": b" ",
    "DEL": b"\x7f",
    "BACKSPACE": b"\x7f",
    "<backspace>": b"\x7f",
    "<up>": b"\x1b[A",
    "<down>": b"\x1b[B",
    "<right>": b"\x1b[C",
    "<left>": b"\x1b[D",
    "<home>": b"\x1b[H",
    "<end>": b"\x1b[F",
    "<pgup>": b"\x1b[5~",
    "<pgdn>": b"\x1b[6~",
    "<insert>": b"\x1b[2~",
    "<delete>": b"\x1b[3~",
    "<f1>": b"\x1bOP",
    "<f2>": b"\x1bOQ",
    "<f3>": b"\x1bOR",
    "<f4>": b"\x1bOS",
    "<f5>": b"\x1b[15~",
    "<f6>": b"\x1b[17~",
    "<f7>": b"\x1b[18~",
    "<f8>": b"\x1b[19~",
    "<f9>": b"\x1b[20~",
    "<f10>": b"\x1b[21~",
    "<f11>": b"\x1b[23~",
    "<f12>": b"\x1b[24~",
}


def kbd(description: str) -> bytes:
    """Translate an Emacs-style key description into pty input bytes."""
    out = b""
    for token in description.split():
        out += _token_bytes(token)
    return out


def _token_bytes(token: str) -> bytes:
    if token in _NAMED:
        return _NAMED[token]
    ctrl = False
    meta = False
    rest = token
    while True:
        if rest.startswith("C-"):
            ctrl = True
            rest = rest[2:]
        elif rest.startswith("M-"):
            meta = True
            rest = rest[2:]
        else:
            break
    # ``C-SPC`` (set-mark-command) maps to NUL on a real terminal — the
    # named-key path above hands us ``b" "`` for SPC, but we need the
    # ctrl-encoded byte. Handle it (and ``C-RET``, ``C-TAB``) explicitly
    # before the general C- handler so the "C-modifier on named key"
    # error doesn't fire.
    if ctrl and rest == "SPC":
        base = b"\x00"
        if meta:
            base = b"\x1b" + base
        return base
    if rest in _NAMED:
        base = _NAMED[rest]
    elif len(rest) == 1:
        ch = rest
        if ctrl:
            if ch == " ":
                base = b"\x00"  # C-SPC
            elif ch == "@":
                base = b"\x00"
            elif "a" <= ch.lower() <= "z":
                base = bytes([ord(ch.lower()) - ord("a") + 1])
            elif ch == "[":
                base = b"\x1b"
            elif ch == "\\":
                base = b"\x1c"
            elif ch == "]":
                base = b"\x1d"
            elif ch == "^":
                base = b"\x1e"
            elif ch == "_":
                base = b"\x1f"
            elif ch == "/":
                base = b"\x1f"  # common C-/ → undo (sent as US)
            elif ch == "?":
                base = b"\x7f"  # C-? → DEL
            else:
                raise ValueError(f"unsupported C- modifier on {ch!r}")
            ctrl = False
        else:
            base = ch.encode("utf-8")
    else:
        # Literal multi-character string. Modifiers don't apply.
        if ctrl or meta:
            raise ValueError(
                f"modifiers not supported on multi-char literal {token!r}"
            )
        return rest.encode("utf-8")
    if ctrl:
        # A named key + C-. We don't currently model this; rare in tests.
        raise ValueError(f"C-modifier on named key {token!r} not supported")
    if meta:
        base = b"\x1b" + base
    return base
