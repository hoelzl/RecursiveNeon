"""
Python major mode — syntax highlighting for .py files.

Registers ``python-mode`` in the global mode table and maps ``.py``
to it in ``AUTO_MODE_ALIST``.
"""

from __future__ import annotations

import re

from recursive_neon.editor.modes import AUTO_MODE_ALIST, SyntaxRule, defmode

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

python_mode = defmode(
    "python-mode",
    doc="Major mode for editing Python source files.",
    syntax_rules=_RULES,
)

AUTO_MODE_ALIST[".py"] = "python-mode"
AUTO_MODE_ALIST[".pyi"] = "python-mode"
