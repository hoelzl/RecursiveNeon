"""
Python major mode — syntax highlighting for .py files.

Registers ``python-mode`` in the global mode table and maps ``.py``
to it in ``AUTO_MODE_ALIST``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from recursive_neon.editor.mark import Mark
from recursive_neon.editor.modes import AUTO_MODE_ALIST, MODES, SyntaxRule, defmode

if TYPE_CHECKING:
    from recursive_neon.editor.buffer import Buffer
    from recursive_neon.editor.editor import Editor

# ── Syntax rules (order matters: first match on a character wins) ────

_KEYWORDS = (
    r"\b(?:False|None|True|and|as|assert|async|await|break|class|continue|"
    r"def|del|elif|else|except|finally|for|from|global|if|import|in|is|"
    r"lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b"
)

_BUILTINS = (
    r"\b(?:print|len|range|int|str|float|list|dict|set|tuple|bool|type|"
    r"isinstance|issubclass|super|property|staticmethod|classmethod|"
    r"enumerate|zip|map|filter|sorted|reversed|any|all|min|max|sum|"
    r"abs|round|hash|id|repr|open|input|format|getattr|setattr|"
    r"hasattr|delattr|callable|iter|next|vars|dir|help)\b"
)

_RULES: list[SyntaxRule] = [
    # Triple-quoted strings (must precede single-quoted)
    SyntaxRule(re.compile(r'""".*?"""|\'\'\'.*?\'\'\'', re.DOTALL), "string"),
    # Prefixed strings (f/b/r/u — must precede plain strings so the prefix
    # is claimed before the bare quote rule matches the inner "...")
    SyntaxRule(
        re.compile(
            r'[fFbBrRuU]{1,2}"(?:[^"\\]|\\.)*"'
            r"|[fFbBrRuU]{1,2}'(?:[^'\\]|\\.)*'"
        ),
        "string",
    ),
    # Single/double-quoted strings (non-greedy, single line)
    SyntaxRule(re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''), "string"),
    # Comments
    SyntaxRule(re.compile(r"#.*$", re.MULTILINE), "comment"),
    # Decorators
    SyntaxRule(re.compile(r"@[\w.]+"), "decorator"),
    # Keywords
    SyntaxRule(re.compile(_KEYWORDS), "keyword"),
    # Builtins
    SyntaxRule(re.compile(_BUILTINS), "builtin"),
    # Numbers (int, float, hex, oct, bin, underscored)
    SyntaxRule(
        re.compile(
            r"\b(?:0[xXoObB][\da-fA-F_]+|\d[\d_]*(?:\.[\d_]*)?(?:[eE][+-]?\d+)?)\b"
        ),
        "number",
    ),
    # Function/class names after def/class keyword
    SyntaxRule(re.compile(r"(?<=\bdef\s)\w+"), "function-name"),
    SyntaxRule(re.compile(r"(?<=\bclass\s)\w+"), "type"),
]

# ── Indentation (Emacs's python-indent-line) ────────────────────────

_INDENT = 4  # python-indent-offset
_DEF_BLOCK_SCALE = 2  # python-indent-def-block-scale

# Statements that open a block (python-rx block-start).
_BLOCK_START_RE = re.compile(
    r"^\s*(?:async\s+)?"
    r"(?:def|class|if|elif|else|try|except|finally|for|while|with)\b"
)
# Dedenter statements and the openers each can attach to
# (python-info-dedenter-opening-block-positions' pairing table).
_DEDENTER_RE = re.compile(r"^\s*(else|elif|except|finally)\b")
_DEDENTER_PAIRS = {
    "elif": ("elif", "if"),
    "else": ("if", "elif", "except", "for", "while"),
    "except": ("except", "try"),
    "finally": ("else", "except", "try"),
}
_OPENER_KEYWORD_RE = re.compile(
    r"^\s*(?:async\s+)?(def|class|if|elif|else|try|except|finally|for|while|with)\b"
)
# Statements that end a block (the :after-block-end context).
_BLOCK_END_RE = re.compile(r"^\s*(?:return|break|continue|pass|raise)\b")


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _code_part(line: str) -> str:
    """The code portion of *line*: everything before a real ``#`` comment,
    with single-line string contents respected (a ``#`` inside quotes is
    not a comment)."""
    i = 0
    while i < len(line):
        ch = line[i]
        if ch in "\"'":
            j = i + 1
            while j < len(line):
                if line[j] == "\\":
                    j += 2
                    continue
                if line[j] == ch:
                    break
                j += 1
            i = j + 1
            continue
        if ch == "#":
            return line[:i]
        i += 1
    return line


def _open_bracket_stack(buf: Buffer, upto_line: int) -> list[tuple[int, int]]:
    """Positions of unclosed ``([{`` before line *upto_line*.

    A small lexer over the preceding lines: bracket characters inside
    strings (single-line or triple-quoted) and comments don't count.
    The triple-quote tracking is naive (no mixed ``'''``-inside-``\"\"\"``
    handling) — adequate for indentation purposes.
    """
    stack: list[tuple[int, int]] = []
    triple: str | None = None
    for ln in range(upto_line):
        line = buf.lines[ln]
        i = 0
        while i < len(line):
            if triple is not None:
                if line.startswith(triple, i):
                    triple = None
                    i += 3
                else:
                    i += 1
                continue
            ch = line[i]
            if line.startswith('"""', i) or line.startswith("'''", i):
                triple = line[i : i + 3]
                i += 3
                continue
            if ch in "\"'":
                j = i + 1
                while j < len(line):
                    if line[j] == "\\":
                        j += 2
                        continue
                    if line[j] == ch:
                        break
                    j += 1
                i = j + 1
                continue
            if ch == "#":
                break
            if ch in "([{":
                stack.append((ln, i))
            elif ch in ")]}" and stack:
                stack.pop()
            i += 1
    return stack


def _dedenter_candidates(buf: Buffer, cur: int, keyword: str) -> list[tuple[int, int]]:
    """``(indent, line)`` of the opening blocks the dedenter could attach to.

    Walks back over block-start lines, collecting matching openers at
    strictly decreasing indentation (each candidate is one valid column
    for the ``else``/``elif``/``except``/``finally`` line), descending —
    the deepest candidate is offered first, like Emacs.
    """
    pairs = _DEDENTER_PAIRS[keyword]
    out: list[tuple[int, int]] = []
    bar = float("inf")
    for ln in range(cur - 1, -1, -1):
        line = buf.lines[ln]
        if not line.strip():
            continue
        m = _OPENER_KEYWORD_RE.match(line)
        if m is None:
            continue
        ind = _indent_of(line)
        if ind < bar:
            # Every block start lowers the bar — a *non*-matching opener
            # (e.g. a ``with`` between an ``else`` and its ``if``) shadows
            # matching openers at its own indent, exactly as Emacs's
            # backward block walk collects indentations.
            if m.group(1) in pairs:
                out.append((ind, ln))
            bar = ind
            if ind == 0:
                break
    return out


def _python_calculate_indent(buf: Buffer) -> int | list[int]:
    """Emacs's ``python-indent-calculate-indentation`` for the point line.

    Returns the calculated column, or a list of candidate columns for a
    dedenter line (``else``/``elif``/``except``/``finally``). Context
    rules verified against GNU Emacs 29.3 via the parity probe battery
    (see scenario 29 and ``test_python_indent_full.py``):

    * inside an unclosed bracket with content after the opener → align
      with the first non-blank char after the bracket;
    * bracket followed by newline → opening line's indent + 4, or + 8
      when the opening line is itself a block start (``def foo(`` —
      python-indent-def-block-scale);
    * a closing bracket starting the line → the opening line's indent;
    * backslash continuations → previous line's indent + 4 (first
      continuation), the previous continuation's own indent (later
      lines), or — for block statements — the column right after the
      keyword (``if aaa and \\`` → column 3);
    * after a block-ending statement (return/break/continue/pass/raise)
      → previous indent − 4;
    * after a ``:`` block opener → previous indent + 4;
    * otherwise → previous non-blank line's indent.

    Known approximations (documented deviations): ``:inside-string`` is
    not special-cased (TAB inside a multi-line string re-indents as
    code), and the dedenter walk pairs keywords lexically rather than by
    real block navigation.
    """
    cur = buf.point.line
    if cur == 0:
        return 0
    prev = next((ln for ln in range(cur - 1, -1, -1) if buf.lines[ln].strip()), None)
    if prev is None:
        return 0

    stripped = buf.lines[cur].lstrip()

    ded = _DEDENTER_RE.match(stripped)
    if ded is not None:
        candidates = _dedenter_candidates(buf, cur, ded.group(1))
        if candidates:
            return [ind for ind, _ in candidates]

    stack = _open_bracket_stack(buf, cur)
    if stack:
        oline, ocol = stack[-1]
        open_line = buf.lines[oline]
        if stripped[:1] in ")]}":
            return _indent_of(open_line)
        after = _code_part(open_line)[ocol + 1 :]
        if after.strip():
            return ocol + 1 + (len(after) - len(after.lstrip()))
        base = _indent_of(open_line)
        scale = _DEF_BLOCK_SCALE if _BLOCK_START_RE.match(open_line) else 1
        return base + scale * _INDENT

    prev_line = buf.lines[prev]
    prev_code = _code_part(prev_line)
    if prev_code.rstrip().endswith("\\"):
        if prev >= 1 and _code_part(buf.lines[prev - 1]).rstrip().endswith("\\"):
            return _indent_of(prev_line)
        m = _BLOCK_START_RE.match(prev_line)
        if m is not None:
            rest = prev_line[m.end() :]
            return m.end() + (len(rest) - len(rest.lstrip()))
        return _indent_of(prev_line) + _INDENT
    if _BLOCK_END_RE.match(prev_code):
        return max(_indent_of(prev_line) - _INDENT, 0)
    if prev_code.rstrip().endswith(":"):
        return _indent_of(prev_line) + _INDENT
    return _indent_of(prev_line)


def _python_indent_levels(buf: Buffer) -> list[int]:
    """Candidate indentation columns for the current line, deepest first.

    For a regular context the levels are the calculated column plus
    every multiple of 4 below it (``calc=7`` → ``[7, 4, 0]`` — verified
    against Emacs: the chain restarts at the offset multiples, not at
    ``calc - 4``). For a dedenter line the levels are exactly the
    matching open blocks' columns.
    """
    calc = _python_calculate_indent(buf)
    if isinstance(calc, list):
        return calc
    first_multiple = (calc - 1) // _INDENT * _INDENT if calc > 0 else -1
    return [calc] + list(range(first_multiple, -1, -_INDENT))


def python_indent_line(ed: Editor) -> None:
    """python-mode TAB: indent to the calculated level, cycling through the
    candidates on repeated TAB (GNU Emacs's ``python-indent-line``)."""
    buf = ed.buffer
    levels = _python_indent_levels(buf)
    cur = buf.point.line
    line = buf.lines[cur]
    cur_indent = len(line) - len(line.lstrip(" "))
    # A fresh TAB indents to the deepest (calculated) level; a repeated TAB
    # (the previous command was also this one) cycles to the next candidate.
    if ed._last_command_name == "indent-for-tab-command" and cur_indent in levels:
        target = levels[(levels.index(cur_indent) + 1) % len(levels)]
    else:
        target = levels[0]
    if target != cur_indent:
        buf.delete_region(Mark(cur, 0), Mark(cur, cur_indent))
        buf.point.move_to(cur, 0)
        if target:
            buf.insert_string(" " * target)
    buf.point.move_to(cur, target)
    # Indenting a dedenter line reports which block that column attaches
    # to — GNU Emacs's "Closes if c:" echo
    # (python-info-dedenter-opening-block-message).
    ded = _DEDENTER_RE.match(line.lstrip())
    if ded is not None:
        for ind, ln in _dedenter_candidates(buf, cur, ded.group(1)):
            if ind == target:
                ed.message = f"Closes {buf.lines[ln].strip()}"
                break


def _python_on_enter(ed: Editor) -> None:
    """Activate the ElDoc lighter, like GNU Emacs's python-mode."""
    eldoc = MODES.get("eldoc-mode")
    buf = ed.buffer
    if eldoc is not None and not any(m.name == "eldoc-mode" for m in buf.minor_modes):
        buf.minor_modes.append(eldoc)


def _python_on_exit(ed: Editor) -> None:
    """Drop the ElDoc lighter when leaving python-mode, so it doesn't leak
    into the next major mode's modeline."""
    buf = ed.buffer
    buf.minor_modes[:] = [m for m in buf.minor_modes if m.name != "eldoc-mode"]


python_mode = defmode(
    "python-mode",
    doc="Major mode for editing Python source files.",
    syntax_rules=_RULES,
    on_enter=_python_on_enter,
    on_exit=_python_on_exit,
    indent_line_function=python_indent_line,
)

AUTO_MODE_ALIST[".py"] = "python-mode"
AUTO_MODE_ALIST[".pyi"] = "python-mode"
