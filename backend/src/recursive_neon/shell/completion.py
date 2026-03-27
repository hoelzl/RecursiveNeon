"""
Context-sensitive tab completion framework.

Completers are callbacks that receive a CompletionContext and return
candidate strings.  Each program/builtin can register its own completer
via the ProgramRegistry or BUILTIN_COMPLETERS dict.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from recursive_neon.shell.path_resolver import resolve_path

if TYPE_CHECKING:
    from recursive_neon.dependencies import ServiceContainer
    from recursive_neon.services.app_service import AppService


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


@dataclass
class CompletionContext:
    """Everything a completer callback needs.

    Attributes:
        args: Completed tokens before the cursor (first element is the
            command name, e.g. ``["note", "show"]``).
        current: Partial (unquoted) text of the argument being completed.
        arg_index: Position of the argument being completed in the full
            argv.  0 = command name, 1 = first argument, etc.
        services: The DI container for dynamic lookups.
        cwd_id: UUID of the current working directory.
    """

    args: list[str]
    current: str
    arg_index: int
    services: ServiceContainer
    cwd_id: str


CompletionFn = Callable[[CompletionContext], list[str]]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def complete_paths(ctx: CompletionContext, *, dirs_only: bool = False) -> list[str]:
    """Complete filesystem paths relative to cwd."""
    return _path_completions(
        ctx.current,
        ctx.cwd_id,
        ctx.services.app_service,
        dirs_only=dirs_only,
    )


def complete_choices(choices: list[str], current: str) -> list[str]:
    """Filter a static list by prefix match."""
    return sorted(c for c in choices if c.startswith(current))


def complete_flags_or_paths(
    flags: list[str],
    ctx: CompletionContext,
    *,
    dirs_only: bool = False,
) -> list[str]:
    """If *current* starts with ``-``, complete flags; otherwise paths."""
    if ctx.current.startswith("-"):
        return sorted(f for f in flags if f.startswith(ctx.current))
    return complete_paths(ctx, dirs_only=dirs_only)


# ---------------------------------------------------------------------------
# Cursor / quoting helpers  (used by both ShellCompleter and get_completions_ext)
# ---------------------------------------------------------------------------

# Characters that require quoting when they appear in a filename
_SHELL_SPECIAL = set(" \t'\"\\")


def quote_path(path: str) -> str:
    """Quote a path for shell insertion, quoting individual segments as needed.

    Only segments containing special characters get quoted.  The ``/``
    separators stay unquoted so the path looks natural::

        My Folder/another file.txt  ->  "My Folder"/"another file.txt"
        Documents/readme.txt        ->  Documents/readme.txt
    """
    trailing_slash = path.endswith("/")
    segments = [s for s in path.split("/") if s]
    quoted: list[str] = []
    for seg in segments:
        if any(ch in _SHELL_SPECIAL for ch in seg):
            escaped = seg.replace("\\", "\\\\").replace('"', '\\"')
            quoted.append(f'"{escaped}"')
        else:
            quoted.append(seg)
    result = "/".join(quoted)
    if path.startswith("/"):
        result = "/" + result
    if trailing_slash and not result.endswith("/"):
        result += "/"
    return result or "/"


def get_current_argument(text_before_cursor: str) -> tuple[int, str]:
    """Parse text before the cursor to find the current incomplete argument.

    Walks the text using the same quoting rules as the tokenizer (see
    ``parser._skip_double_quoted`` / ``parser._skip_single_quoted``),
    tracking where each argument starts.  Unlike the skip helpers, this
    function must also collect the unquoted content, so it uses inline
    loops instead of the shared helpers.

    Returns:
        ``(arg_start_pos, unquoted_content)`` where *arg_start_pos* is the
        index in *text_before_cursor* where the current argument starts,
        and *unquoted_content* is the argument with quotes/escapes resolved.
    """
    i = 0
    n = len(text_before_cursor)
    arg_start = 0
    current_raw: list[str] = []

    while i < n:
        ch = text_before_cursor[i]

        if ch == "\\" and i + 1 < n:
            current_raw.append(text_before_cursor[i + 1])
            i += 2

        elif ch == '"':
            i += 1
            while i < n and text_before_cursor[i] != '"':
                if text_before_cursor[i] == "\\" and i + 1 < n:
                    current_raw.append(text_before_cursor[i + 1])
                    i += 2
                else:
                    current_raw.append(text_before_cursor[i])
                    i += 1
            if i < n:
                i += 1  # skip closing quote

        elif ch == "'":
            i += 1
            while i < n and text_before_cursor[i] != "'":
                current_raw.append(text_before_cursor[i])
                i += 1
            if i < n:
                i += 1  # skip closing quote

        elif ch in (" ", "\t"):
            current_raw = []
            i += 1
            while i < n and text_before_cursor[i] in (" ", "\t"):
                i += 1
            arg_start = i

        else:
            current_raw.append(ch)
            i += 1

    return arg_start, "".join(current_raw)


# ---------------------------------------------------------------------------
# Path completion internals
# ---------------------------------------------------------------------------


def _path_completions(
    raw_path: str,
    cwd_id: str,
    app_service: AppService,
    *,
    dirs_only: bool = False,
    quote: bool = True,
) -> list[str]:
    """Return matching path strings for a partial path.

    When *quote* is True (the default), path segments containing spaces
    or other shell-special characters are wrapped in double quotes.  Set
    *quote* to False for contexts where quoting is unwanted (e.g. the
    editor minibuffer, where the entire input is a single path).
    """
    if "/" in raw_path:
        last_slash = raw_path.rfind("/")
        dir_part = raw_path[: last_slash + 1] or "/"
        prefix = raw_path[last_slash + 1 :]
    else:
        dir_part = ""
        prefix = raw_path

    try:
        if dir_part:
            dir_node = resolve_path(dir_part, cwd_id, app_service)
        else:
            dir_node = app_service.get_file(cwd_id)
    except (FileNotFoundError, NotADirectoryError, ValueError):
        return []

    if dir_node.type != "directory":
        return []

    children = app_service.list_directory(dir_node.id)
    results: list[str] = []
    for child in sorted(children, key=lambda n: n.name.lower()):
        if child.name.lower().startswith(prefix.lower()):
            if dirs_only and child.type != "directory":
                continue
            suffix = "/" if child.type == "directory" else ""
            full_path = dir_part + child.name + suffix
            results.append(quote_path(full_path) if quote else full_path)
    return results
