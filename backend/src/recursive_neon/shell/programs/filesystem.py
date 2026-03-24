"""
Filesystem programs: ls, pwd, cat, mkdir, touch, rm, cp, mv, grep, find, write.

All operate on the virtual filesystem via ProgramContext.
"""

from __future__ import annotations

import re
from fnmatch import fnmatch

from recursive_neon.models.app_models import FileNode
from recursive_neon.shell.output import CYAN, DIM, GREEN, MAGENTA
from recursive_neon.shell.path_resolver import get_node_path
from recursive_neon.shell.programs import ProgramContext, ProgramRegistry


async def prog_pwd(ctx: ProgramContext) -> int:
    """Print current working directory."""
    path = get_node_path(ctx.cwd_id, ctx.services.app_service)
    ctx.stdout.writeln(path)
    return 0


async def prog_ls(ctx: ProgramContext) -> int:
    """List directory contents."""
    args = ctx.args[1:]
    long_format = False
    show_all = False
    paths: list[str] = []

    for arg in args:
        if arg.startswith("-"):
            for ch in arg[1:]:
                if ch == "l":
                    long_format = True
                elif ch == "a":
                    show_all = True
                else:
                    ctx.stderr.error(f"ls: unknown option: -{ch}")
                    return 1
        else:
            paths.append(arg)

    if not paths:
        paths = ["."]

    for i, path in enumerate(paths):
        try:
            node = ctx.resolve_path(path)
        except (FileNotFoundError, NotADirectoryError) as e:
            ctx.stderr.error(f"ls: {e}")
            return 1

        if node.type == "file":
            _print_entry(ctx, node, long_format)
            continue

        if len(paths) > 1:
            if i > 0:
                ctx.stdout.writeln()
            ctx.stdout.writeln(f"{path}:")

        children = ctx.services.app_service.list_directory(node.id)
        if not show_all:
            children = [c for c in children if not c.name.startswith(".")]

        # Sort: directories first, then files, alphabetical within each
        dirs = sorted(
            [c for c in children if c.type == "directory"], key=lambda n: n.name.lower()
        )
        files = sorted(
            [c for c in children if c.type == "file"], key=lambda n: n.name.lower()
        )

        if long_format:
            for entry in dirs + files:
                _print_entry_long(ctx, entry)
        else:
            names: list[str] = []
            for entry in dirs + files:
                if entry.type == "directory":
                    names.append(ctx.stdout.styled(entry.name + "/", CYAN))
                else:
                    names.append(entry.name)
            if names:
                ctx.stdout.writeln("  ".join(names))

    return 0


def _print_entry(ctx: ProgramContext, node, long_format: bool = False) -> None:
    if long_format:
        _print_entry_long(ctx, node)
    else:
        if node.type == "directory":
            ctx.stdout.writeln(ctx.stdout.styled(node.name + "/", CYAN))
        else:
            ctx.stdout.writeln(node.name)


def _print_entry_long(ctx: ProgramContext, node) -> None:
    type_char = "d" if node.type == "directory" else "-"
    perms = "rwx" if node.type == "directory" else "rw-"
    timestamp = ""
    if node.updated_at:
        # Show just the date and time portion
        timestamp = node.updated_at[:16].replace("T", " ")
    name = node.name
    if node.type == "directory":
        name = ctx.stdout.styled(name + "/", CYAN)
    line = f"{type_char}{perms}  {ctx.stdout.styled(timestamp, DIM)}  {name}"
    ctx.stdout.writeln(line)


async def prog_cat(ctx: ProgramContext) -> int:
    """Print file contents."""
    if len(ctx.args) < 2:
        ctx.stderr.error("cat: missing file operand")
        return 1

    exit_code = 0
    for path in ctx.args[1:]:
        try:
            node = ctx.resolve_path(path)
        except (FileNotFoundError, NotADirectoryError) as e:
            ctx.stderr.error(f"cat: {e}")
            exit_code = 1
            continue

        if node.type == "directory":
            ctx.stderr.error(f"cat: {path}: Is a directory")
            exit_code = 1
            continue

        content = node.content or ""
        ctx.stdout.write(content)
        # Add trailing newline if content doesn't end with one
        if content and not content.endswith("\n"):
            ctx.stdout.writeln()

    return exit_code


async def prog_mkdir(ctx: ProgramContext) -> int:
    """Create directories."""
    args = ctx.args[1:]
    make_parents = False
    paths: list[str] = []

    for arg in args:
        if arg == "-p":
            make_parents = True
        elif arg.startswith("-"):
            ctx.stderr.error(f"mkdir: unknown option: {arg}")
            return 1
        else:
            paths.append(arg)

    if not paths:
        ctx.stderr.error("mkdir: missing operand")
        return 1

    for path in paths:
        try:
            if make_parents:
                _mkdir_parents(ctx, path)
            else:
                parent, name = ctx.resolve_parent_and_name(path)
                # Check if already exists
                children = ctx.services.app_service.list_directory(parent.id)
                for child in children:
                    if child.name == name:
                        ctx.stderr.error(
                            f"mkdir: cannot create directory '{path}': File exists"
                        )
                        return 1
                ctx.services.app_service.create_directory(
                    {"name": name, "parent_id": parent.id}
                )
        except (FileNotFoundError, NotADirectoryError, ValueError) as e:
            ctx.stderr.error(f"mkdir: {e}")
            return 1

    return 0


def _mkdir_parents(ctx: ProgramContext, path: str) -> None:
    """Create directory and all parent directories as needed."""
    if path.startswith("/"):
        root_id = ctx.services.app_service.game_state.filesystem.root_id
        if root_id is None:
            raise FileNotFoundError("Filesystem has no root directory")
        current_id = root_id
        segments = [s for s in path.split("/") if s]
    else:
        current_id = ctx.cwd_id
        segments = [s for s in path.split("/") if s]

    for segment in segments:
        children = ctx.services.app_service.list_directory(current_id)
        found = None
        for child in children:
            if child.name == segment:
                found = child
                break
        if found is not None:
            if found.type != "directory":
                raise NotADirectoryError(f"Not a directory: {segment}")
            current_id = found.id
        else:
            new_dir = ctx.services.app_service.create_directory(
                {"name": segment, "parent_id": current_id}
            )
            current_id = new_dir.id


async def prog_touch(ctx: ProgramContext) -> int:
    """Create empty files or update timestamps."""
    if len(ctx.args) < 2:
        ctx.stderr.error("touch: missing file operand")
        return 1

    for path in ctx.args[1:]:
        try:
            # If file exists, update timestamp
            node = ctx.resolve_path(path)
            ctx.services.app_service.update_file(node.id, {})
        except FileNotFoundError:
            # Create new empty file
            try:
                parent, name = ctx.resolve_parent_and_name(path)
                ctx.services.app_service.create_file(
                    {"name": name, "parent_id": parent.id, "content": ""}
                )
            except (FileNotFoundError, NotADirectoryError, ValueError) as e:
                ctx.stderr.error(f"touch: {e}")
                return 1
        except NotADirectoryError as e:
            ctx.stderr.error(f"touch: {e}")
            return 1

    return 0


async def prog_rm(ctx: ProgramContext) -> int:
    """Remove files or directories."""
    args = ctx.args[1:]
    recursive = False
    paths: list[str] = []

    for arg in args:
        if arg in ("-r", "-rf", "-R"):
            recursive = True
        elif arg.startswith("-"):
            ctx.stderr.error(f"rm: unknown option: {arg}")
            return 1
        else:
            paths.append(arg)

    if not paths:
        ctx.stderr.error("rm: missing operand")
        return 1

    for path in paths:
        try:
            node = ctx.resolve_path(path)
        except (FileNotFoundError, NotADirectoryError) as e:
            ctx.stderr.error(f"rm: {e}")
            return 1

        # Don't allow removing root
        root_id = ctx.services.app_service.game_state.filesystem.root_id
        if node.id == root_id:
            ctx.stderr.error("rm: cannot remove root directory")
            return 1

        if node.type == "directory" and not recursive:
            ctx.stderr.error(f"rm: cannot remove '{path}': Is a directory (use -r)")
            return 1

        ctx.services.app_service.delete_file(node.id)

    return 0


async def prog_cp(ctx: ProgramContext) -> int:
    """Copy files or directories."""
    if len(ctx.args) < 3:
        ctx.stderr.error("cp: missing operand")
        return 1

    src_path = ctx.args[1]
    dest_path = ctx.args[2]

    try:
        src_node = ctx.resolve_path(src_path)
    except (FileNotFoundError, NotADirectoryError) as e:
        ctx.stderr.error(f"cp: {e}")
        return 1

    # Determine destination: existing directory or new name
    try:
        dest_node = ctx.resolve_path(dest_path)
        if dest_node.type == "directory":
            # Copy into the directory with original name
            ctx.services.app_service.copy_file(src_node.id, dest_node.id)
        else:
            # Destination exists and is a file — copy with rename
            parent, name = ctx.resolve_parent_and_name(dest_path)
            ctx.services.app_service.copy_file(src_node.id, parent.id, name)
    except FileNotFoundError:
        # Destination doesn't exist — resolve parent and use as new name
        try:
            parent, name = ctx.resolve_parent_and_name(dest_path)
            ctx.services.app_service.copy_file(src_node.id, parent.id, name)
        except (FileNotFoundError, NotADirectoryError, ValueError) as e:
            ctx.stderr.error(f"cp: {e}")
            return 1

    return 0


async def prog_mv(ctx: ProgramContext) -> int:
    """Move or rename files and directories."""
    if len(ctx.args) < 3:
        ctx.stderr.error("mv: missing operand")
        return 1

    src_path = ctx.args[1]
    dest_path = ctx.args[2]

    try:
        src_node = ctx.resolve_path(src_path)
    except (FileNotFoundError, NotADirectoryError) as e:
        ctx.stderr.error(f"mv: {e}")
        return 1

    # Don't allow moving root
    root_id = ctx.services.app_service.game_state.filesystem.root_id
    if src_node.id == root_id:
        ctx.stderr.error("mv: cannot move root directory")
        return 1

    try:
        dest_node = ctx.resolve_path(dest_path)
        if dest_node.type == "directory":
            # Move into the directory
            ctx.services.app_service.move_file(src_node.id, dest_node.id)
        else:
            # Destination is a file — rename (move to same parent with new name)
            parent, name = ctx.resolve_parent_and_name(dest_path)
            ctx.services.app_service.move_file(src_node.id, parent.id)
            ctx.services.app_service.update_file(src_node.id, {"name": name})
    except FileNotFoundError:
        # Destination doesn't exist — treat as rename
        try:
            parent, name = ctx.resolve_parent_and_name(dest_path)
            ctx.services.app_service.move_file(src_node.id, parent.id)
            ctx.services.app_service.update_file(src_node.id, {"name": name})
        except (FileNotFoundError, NotADirectoryError, ValueError) as e:
            ctx.stderr.error(f"mv: {e}")
            return 1
    except ValueError as e:
        ctx.stderr.error(f"mv: {e}")
        return 1

    return 0


async def prog_grep(ctx: ProgramContext) -> int:
    """Search file contents for a pattern."""
    args = ctx.args[1:]
    case_insensitive = False
    paths: list[str] = []
    pattern_str: str | None = None

    for arg in args:
        if arg.startswith("-") and not pattern_str:
            for ch in arg[1:]:
                if ch == "i":
                    case_insensitive = True
                elif ch in ("r", "R", "n"):
                    pass  # -r and -n are on by default
                else:
                    ctx.stderr.error(f"grep: unknown option: -{ch}")
                    return 1
        elif pattern_str is None:
            pattern_str = arg
        else:
            paths.append(arg)

    if pattern_str is None:
        ctx.stderr.error("grep: missing pattern")
        return 1

    flags = re.IGNORECASE if case_insensitive else 0
    try:
        pattern = re.compile(pattern_str, flags)
    except re.error as e:
        ctx.stderr.error(f"grep: invalid pattern: {e}")
        return 1

    if not paths:
        paths = ["."]

    results: list[tuple[str, int, str]] = []
    for path in paths:
        try:
            node = ctx.resolve_path(path)
        except (FileNotFoundError, NotADirectoryError) as e:
            ctx.stderr.error(f"grep: {e}")
            return 1
        file_path = get_node_path(node.id, ctx.services.app_service)
        _grep_node(ctx, pattern, node, file_path, results)

    for file_path, lineno, line in results:
        prefix = ctx.stdout.styled(f"{file_path}:", MAGENTA)
        num = ctx.stdout.styled(f"{lineno}:", GREEN)
        ctx.stdout.writeln(f"{prefix}{num}{line}")

    return 0 if results else 1


def _grep_node(
    ctx: ProgramContext,
    pattern: re.Pattern[str],
    node: FileNode,
    file_path: str,
    results: list[tuple[str, int, str]],
) -> None:
    """Recursively search a node for pattern matches."""
    if node.type == "directory":
        children = ctx.services.app_service.list_directory(node.id)
        for child in sorted(children, key=lambda n: n.name.lower()):
            child_path = (
                f"{file_path}/{child.name}" if file_path != "/" else f"/{child.name}"
            )
            _grep_node(ctx, pattern, child, child_path, results)
    elif node.type == "file" and node.content:
        for lineno, line in enumerate(node.content.splitlines(), 1):
            if pattern.search(line):
                results.append((file_path, lineno, line))


async def prog_find(ctx: ProgramContext) -> int:
    """Find files by name pattern."""
    args = ctx.args[1:]
    start_path = "."
    name_pattern: str | None = None

    i = 0
    while i < len(args):
        if args[i] == "-name" and i + 1 < len(args):
            name_pattern = args[i + 1]
            i += 2
        elif not args[i].startswith("-"):
            start_path = args[i]
            i += 1
        else:
            ctx.stderr.error(f"find: unknown option: {args[i]}")
            return 1

    if name_pattern is None:
        ctx.stderr.error("find: missing -name pattern")
        return 1

    try:
        start_node = ctx.resolve_path(start_path)
    except (FileNotFoundError, NotADirectoryError) as e:
        ctx.stderr.error(f"find: {e}")
        return 1

    base_path = get_node_path(start_node.id, ctx.services.app_service)
    results: list[str] = []
    _find_node(ctx, start_node, base_path, name_pattern, results)

    for path in results:
        ctx.stdout.writeln(path)

    return 0


def _find_node(
    ctx: ProgramContext,
    node: FileNode,
    current_path: str,
    pattern: str,
    results: list[str],
) -> None:
    """Recursively find files matching a name pattern."""
    if fnmatch(node.name, pattern):
        results.append(current_path)

    if node.type == "directory":
        children = ctx.services.app_service.list_directory(node.id)
        for child in sorted(children, key=lambda n: n.name.lower()):
            child_path = (
                f"{current_path}/{child.name}"
                if current_path != "/"
                else f"/{child.name}"
            )
            _find_node(ctx, child, child_path, pattern, results)


async def prog_write(ctx: ProgramContext) -> int:
    """Write content to a file (reads lines from args or creates empty)."""
    if len(ctx.args) < 2:
        ctx.stderr.error("write: missing file operand")
        return 1

    file_path = ctx.args[1]

    content = " ".join(ctx.args[2:]) if len(ctx.args) > 2 else ""

    # Try to update existing file, or create new one
    try:
        node = ctx.resolve_path(file_path)
        if node.type == "directory":
            ctx.stderr.error(f"write: {file_path}: Is a directory")
            return 1
        ctx.services.app_service.update_file(node.id, {"content": content})
    except FileNotFoundError:
        try:
            parent, name = ctx.resolve_parent_and_name(file_path)
            ctx.services.app_service.create_file(
                {"name": name, "parent_id": parent.id, "content": content}
            )
        except (FileNotFoundError, NotADirectoryError, ValueError) as e:
            ctx.stderr.error(f"write: {e}")
            return 1

    ctx.stdout.writeln(f"Wrote {file_path}")
    return 0


def register_filesystem_programs(registry: ProgramRegistry) -> None:
    """Register all filesystem programs."""
    registry.register_fn("pwd", prog_pwd, "Print current working directory")
    registry.register_fn(
        "ls",
        prog_ls,
        "List directory contents\n"
        "\n"
        "Usage: ls [-la] [PATH...]\n"
        "\n"
        "Options:\n"
        "  -l    Long listing format (type, permissions, timestamp)\n"
        "  -a    Show hidden entries (names starting with .)",
    )
    registry.register_fn(
        "cat",
        prog_cat,
        "Print file contents\n"
        "\n"
        "Usage: cat FILE...\n"
        "\n"
        "Concatenate and print the contents of one or more files.",
    )
    registry.register_fn(
        "mkdir",
        prog_mkdir,
        "Create directories\n"
        "\n"
        "Usage: mkdir [-p] DIR...\n"
        "\n"
        "Options:\n"
        "  -p    Create parent directories as needed",
    )
    registry.register_fn(
        "touch",
        prog_touch,
        "Create empty files or update timestamps\n"
        "\n"
        "Usage: touch FILE...\n"
        "\n"
        "Create each FILE if it does not exist, or update its timestamp.",
    )
    registry.register_fn(
        "rm",
        prog_rm,
        "Remove files or directories\n"
        "\n"
        "Usage: rm [-r] FILE...\n"
        "\n"
        "Options:\n"
        "  -r, -R    Remove directories and their contents recursively",
    )
    registry.register_fn(
        "cp",
        prog_cp,
        "Copy files or directories\n"
        "\n"
        "Usage: cp SOURCE DEST\n"
        "\n"
        "Copy SOURCE to DEST. If DEST is a directory, copy into it.",
    )
    registry.register_fn(
        "mv",
        prog_mv,
        "Move or rename files and directories\n"
        "\n"
        "Usage: mv SOURCE DEST\n"
        "\n"
        "Move SOURCE to DEST. If DEST is a directory, move into it.",
    )
    registry.register_fn(
        "grep",
        prog_grep,
        "Search file contents for a pattern\n"
        "\n"
        "Usage: grep [-i] PATTERN [PATH...]\n"
        "\n"
        "Search files for lines matching PATTERN (regex). Recurses into\n"
        "directories. Defaults to searching from current directory.\n"
        "\n"
        "Options:\n"
        "  -i    Case-insensitive matching",
    )
    registry.register_fn(
        "find",
        prog_find,
        "Find files by name pattern\n"
        "\n"
        "Usage: find [PATH] -name PATTERN\n"
        "\n"
        "Find files whose name matches PATTERN (glob). Searches recursively\n"
        "from PATH (default: current directory).",
    )
    registry.register_fn(
        "write",
        prog_write,
        "Write content to a file\n"
        "\n"
        "Usage: write FILE [CONTENT...]\n"
        "\n"
        "Write CONTENT to FILE (creates if needed, overwrites if exists).\n"
        "Without CONTENT, creates an empty file.",
    )
