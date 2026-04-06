"""
Markdown major mode — syntax highlighting for .md / .markdown files.

Registers ``markdown-mode`` in the global mode table.
"""

from __future__ import annotations

import re

from recursive_neon.editor.modes import AUTO_MODE_ALIST, SyntaxRule, defmode

_RULES: list[SyntaxRule] = [
    # Headings (ATX-style: # through ######)
    SyntaxRule(re.compile(r"^#{1,6}\s.*$", re.MULTILINE), "heading"),
    # Inline code (backtick spans)
    SyntaxRule(re.compile(r"`[^`\n]+`"), "code"),
    # Fenced code block delimiters
    SyntaxRule(re.compile(r"^```.*$", re.MULTILINE), "code"),
    # Bold (**text** or __text__)
    SyntaxRule(re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__"), "bold"),
    # Italic (*text* or _text_ — avoid matching inside bold/underscores)
    SyntaxRule(
        re.compile(r"(?<!\*)\*(?!\*)[^*\n]+\*(?!\*)|(?<!_)_(?!_)[^_\n]+_(?!_)"),
        "italic",
    ),
    # Links [text](url)
    SyntaxRule(re.compile(r"\[[^\]\n]*\]\([^)\n]*\)"), "link"),
    # Reference links [text][ref]
    SyntaxRule(re.compile(r"\[[^\]\n]*\]\[[^\]\n]*\]"), "link"),
    # HTML comments
    SyntaxRule(re.compile(r"<!--.*?-->", re.DOTALL), "comment"),
]

markdown_mode = defmode(
    "markdown-mode",
    variables={"auto-fill": True},
    doc="Major mode for editing Markdown files.",
    syntax_rules=_RULES,
)

AUTO_MODE_ALIST[".md"] = "markdown-mode"
AUTO_MODE_ALIST[".markdown"] = "markdown-mode"
