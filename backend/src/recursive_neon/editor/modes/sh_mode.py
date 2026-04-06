"""
Shell-script major mode — syntax highlighting for .sh / .bash files.

This is for *file content* highlighting, distinct from the interactive
``shell-mode`` major mode used by M-x shell.

Registers ``sh-mode`` in the global mode table.
"""

from __future__ import annotations

import re

from recursive_neon.editor.modes import AUTO_MODE_ALIST, SyntaxRule, defmode

_SH_KEYWORDS = (
    r"\b(?:if|then|else|elif|fi|case|esac|for|while|until|do|done|"
    r"in|function|select|time|coproc)\b"
)

_SH_BUILTINS = (
    r"\b(?:echo|read|printf|cd|pwd|exit|return|export|unset|local|"
    r"source|alias|unalias|set|shift|test|eval|exec|trap|wait|"
    r"true|false|break|continue)\b"
)

_RULES: list[SyntaxRule] = [
    # Double-quoted strings (with escapes)
    SyntaxRule(re.compile(r'"(?:[^"\\]|\\.)*"'), "string"),
    # Single-quoted strings (no escapes)
    SyntaxRule(re.compile(r"'[^']*'"), "string"),
    # Heredoc delimiters (simplified — just the marker lines)
    SyntaxRule(re.compile(r"<<-?\s*['\"]?\w+['\"]?"), "string"),
    # Variable references ($VAR, ${VAR}, $1, $@, $#, etc.)
    # Must precede comments so $# doesn't get captured as a comment.
    SyntaxRule(re.compile(r"\$\{[^}]+\}|\$[\w@#?!\-*$0-9]+"), "sh-variable"),
    # Comments
    SyntaxRule(re.compile(r"#.*$", re.MULTILINE), "comment"),
    # Keywords
    SyntaxRule(re.compile(_SH_KEYWORDS), "keyword"),
    # Builtins
    SyntaxRule(re.compile(_SH_BUILTINS), "builtin"),
    # Redirections
    SyntaxRule(re.compile(r"[0-9]*>>?|[0-9]*<<?|[0-9]*>&[0-9]*|&>"), "sh-redirect"),
    # Numbers
    SyntaxRule(re.compile(r"\b\d+\b"), "number"),
]

sh_mode = defmode(
    "sh-mode",
    doc="Major mode for editing shell scripts.",
    syntax_rules=_RULES,
)

AUTO_MODE_ALIST[".sh"] = "sh-mode"
AUTO_MODE_ALIST[".bash"] = "sh-mode"
AUTO_MODE_ALIST[".zsh"] = "sh-mode"
