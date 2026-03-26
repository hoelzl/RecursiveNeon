"""
Shell-level glob expansion against the virtual filesystem.

Expands unquoted tokens containing ``*``, ``?``, or ``[`` against the
virtual filesystem *before* dispatching to programs, just like a real
Unix shell.

Rules:
- Quoted tokens are never expanded.
- The command name (first token) is never expanded.
- Unmatched globs pass through as literals (POSIX behavior).
- Only single-level patterns are supported (no ``**`` recursion).
"""

from __future__ import annotations

from fnmatch import fnmatch

from recursive_neon.services.app_service import AppService
from recursive_neon.shell.parser import Token
from recursive_neon.shell.path_resolver import resolve_path

_GLOB_CHARS = frozenset("*?[")


def has_glob_chars(s: str) -> bool:
    """Return True if *s* contains unescaped glob metacharacters."""
    return any(ch in _GLOB_CHARS for ch in s)


def expand_globs(
    tokens: list[Token],
    cwd_id: str,
    app_service: AppService,
) -> list[str]:
    """Expand glob patterns in unquoted tokens.

    Args:
        tokens: Parsed tokens from :func:`tokenize_ext`.
        cwd_id: UUID of the current working directory.
        app_service: AppService for filesystem access.

    Returns:
        Plain list of strings ready for dispatch.  Expanded globs are
        sorted alphabetically; non-glob tokens pass through unchanged.
    """
    if not tokens:
        return []

    # Command name is always literal
    result: list[str] = [tokens[0].value]

    for tok in tokens[1:]:
        if tok.quoted or not has_glob_chars(tok.value):
            result.append(tok.value)
        else:
            matches = _match_glob(tok.value, cwd_id, app_service)
            if matches:
                result.extend(sorted(matches))
            else:
                # No match — pass through as literal (POSIX behavior)
                result.append(tok.value)

    return result


def _match_glob(
    pattern: str,
    cwd_id: str,
    app_service: AppService,
) -> list[str]:
    """Match a glob pattern against the virtual filesystem.

    Supports patterns like:
    - ``*.txt``             — match in cwd
    - ``Documents/*.txt``   — match in Documents/
    - ``/Documents/*.txt``  — absolute path match
    - ``?.txt``             — character wildcards
    - ``[abc].txt``         — character classes
    """
    # Split into directory prefix and filename pattern
    if "/" in pattern:
        last_slash = pattern.rfind("/")
        dir_part = pattern[: last_slash + 1]  # includes trailing /
        file_pattern = pattern[last_slash + 1 :]
    else:
        dir_part = ""
        file_pattern = pattern

    # If the filename part has no glob chars, nothing to expand
    if not has_glob_chars(file_pattern):
        return []

    # Resolve the directory
    try:
        if dir_part:
            dir_node = resolve_path(dir_part, cwd_id, app_service)
        else:
            dir_node = app_service.get_file(cwd_id)
    except (FileNotFoundError, NotADirectoryError, ValueError):
        return []

    if dir_node.type != "directory":
        return []

    # Match children against the pattern
    children = app_service.list_directory(dir_node.id)
    results: list[str] = []
    for child in children:
        if fnmatch(child.name, file_pattern):
            suffix = "/" if child.type == "directory" else ""
            results.append(dir_part + child.name + suffix)

    return results
