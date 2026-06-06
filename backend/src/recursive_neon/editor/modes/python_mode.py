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


def _python_indent_levels(buf: Buffer) -> list[int]:
    """Candidate indentation columns for the current line, deepest first.

    A simplified ``python-indent-calculate-levels``: the deepest level is the
    nearest previous non-blank line's indent + 4 when it ends with ``:``
    (opening a block), else that line's own indent; the cycle then dedents by
    4 down to 0. The full Emacs heuristics (brackets, continuation lines,
    dedenting keywords like ``else``/``except``) are **not** replicated, so
    repeated TAB after a non-``:`` line is best-effort — see the module note.
    """
    cur = buf.point.line
    prev_indent = 0
    opens_block = False
    for ln in range(cur - 1, -1, -1):
        line = buf.lines[ln]
        if line.strip():
            prev_indent = len(line) - len(line.lstrip(" "))
            opens_block = line.rstrip().endswith(":")
            break
    calculated = prev_indent + _INDENT if opens_block else prev_indent
    return list(range(calculated, -1, -_INDENT))


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
