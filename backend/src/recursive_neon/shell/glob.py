"""
Shell-level glob expansion against the virtual filesystem.

Expands unquoted tokens containing ``*``, ``?``, or ``[`` against the
virtual filesystem *before* dispatching to programs, just like a real
Unix shell.

Rules:
- Quoted tokens are never expanded.
- The command name (first token) is never expanded.
- Unmatched globs pass through as literals (POSIX behavior).
- Supports ``**`` for recursive directory matching.
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
    - ``*.txt``              — match in cwd
    - ``Documents/*.txt``    — match in Documents/
    - ``/Documents/*.txt``   — absolute path match
    - ``?.txt``              — character wildcards
    - ``[abc].txt``          — character classes
    - ``**/*.txt``           — recursive match
    - ``Documents/**``       — everything under Documents/
    - ``**/notes.md``        — notes.md at any depth
    """
    # Split pattern into path segments
    segments = pattern.split("/")

    # Determine the starting directory and prefix for results
    if pattern.startswith("/"):
        # Absolute path — resolve from root
        root_id = app_service.game_state.filesystem.root_id
        if root_id is None:
            return []
        start_id = root_id
        prefix = "/"
        # Remove empty first segment from leading /
        segments = segments[1:]
    else:
        start_id = cwd_id
        prefix = ""

    if not segments:
        return []

    # Check if this pattern uses ** at all
    if "**" not in segments:
        # No recursive glob — use the faster single-level path
        return _match_simple(pattern, cwd_id, app_service)

    # Recursive glob: walk segments
    return _match_recursive(segments, start_id, prefix, app_service)


def _match_simple(
    pattern: str,
    cwd_id: str,
    app_service: AppService,
) -> list[str]:
    """Match a non-recursive glob pattern (no ``**``).

    This is the original single-level matching logic.
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


def _match_recursive(
    segments: list[str],
    dir_id: str,
    prefix: str,
    app_service: AppService,
) -> list[str]:
    """Match a glob pattern containing ``**`` segments.

    Walks the segment list left to right.  When a ``**`` segment is
    encountered, it matches zero or more intermediate directories.

    Args:
        segments: Path segments (already split on ``/``).
        dir_id: UUID of the directory to start matching in.
        prefix: String prefix to prepend to results (e.g. ``"/"`` for
            absolute paths, ``"Documents/"`` for intermediate results).
        app_service: AppService for filesystem access.

    Returns:
        List of matching paths.
    """
    if not segments:
        return []

    results: list[str] = []
    seg = segments[0]
    rest = segments[1:]

    if seg == "**":
        # ** matches zero or more directories.
        #
        # "Zero directories" means we try matching `rest` right here
        # in the current directory.
        #
        # "One or more directories" means we recurse into every child
        # directory and try `["**"] + rest` from there.

        if not rest:
            # Pattern is just "**" (or ends with "**") — match everything
            # under this directory recursively.
            _collect_all(dir_id, prefix, app_service, results)
        else:
            # Try matching rest in current dir (zero-directory case)
            results.extend(_match_recursive(rest, dir_id, prefix, app_service))

            # Try matching ["**"] + rest in every child directory
            try:
                dir_node = app_service.get_file(dir_id)
            except (FileNotFoundError, ValueError):
                return results
            if dir_node.type != "directory":
                return results

            children = app_service.list_directory(dir_id)
            for child in children:
                if child.type == "directory":
                    child_prefix = prefix + child.name + "/"
                    results.extend(
                        _match_recursive(segments, child.id, child_prefix, app_service)
                    )
    else:
        # Normal segment (may contain *, ?, [...] but not **)
        try:
            dir_node = app_service.get_file(dir_id)
        except (FileNotFoundError, ValueError):
            return results
        if dir_node.type != "directory":
            return results

        children = app_service.list_directory(dir_id)
        for child in children:
            if fnmatch(child.name, seg):
                suffix = "/" if child.type == "directory" else ""
                child_path = prefix + child.name + suffix
                if rest:
                    # More segments to match — recurse into this child
                    if child.type == "directory":
                        results.extend(
                            _match_recursive(
                                rest,
                                child.id,
                                prefix + child.name + "/",
                                app_service,
                            )
                        )
                else:
                    # Last segment — this is a match
                    results.append(child_path)

    return results


def _collect_all(
    dir_id: str,
    prefix: str,
    app_service: AppService,
    results: list[str],
) -> None:
    """Collect all files and directories recursively under *dir_id*."""
    try:
        children = app_service.list_directory(dir_id)
    except (FileNotFoundError, ValueError):
        return

    for child in children:
        suffix = "/" if child.type == "directory" else ""
        child_path = prefix + child.name + suffix
        results.append(child_path)
        if child.type == "directory":
            _collect_all(child.id, prefix + child.name + "/", app_service, results)
