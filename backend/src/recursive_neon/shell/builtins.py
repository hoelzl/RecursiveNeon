"""
Shell builtins — commands that must modify shell session state.

Only commands that need to mutate the ShellSession belong here.
Everything else should be a program in shell/programs/.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Awaitable, Callable

from recursive_neon.shell.completion import CompletionFn, complete_paths
from recursive_neon.shell.output import Output

if TYPE_CHECKING:
    from recursive_neon.shell.session import ShellSession

# Builtin function signature
BuiltinFn = Callable[["ShellSession", list[str], Output], Awaitable[int]]


async def builtin_cd(session: ShellSession, args: list[str], output: Output) -> int:
    """Change the current working directory."""
    path = session.env.get("HOME", "/") if len(args) < 2 else args[1]

    try:
        node = session.resolve_path(path)
    except FileNotFoundError as e:
        output.error(f"cd: {e}")
        return 1
    except NotADirectoryError as e:
        output.error(f"cd: {e}")
        return 1

    if node.type != "directory":
        output.error(f"cd: not a directory: {path}")
        return 1

    session.cwd_id = node.id
    return 0


async def builtin_exit(session: ShellSession, args: list[str], output: Output) -> int:
    """Exit the shell.

    Returns the special exit code -1 which the REPL loop uses as a
    signal to terminate. The actual exit code passed to the OS is
    taken from the first argument (default 0).
    """
    # The REPL checks for this sentinel value
    if len(args) > 1:
        try:
            session.last_exit_code = int(args[1])
        except ValueError:
            output.error(f"exit: numeric argument required: {args[1]}")
            return 1
    else:
        session.last_exit_code = 0
    return -1  # Sentinel: REPL should exit


async def builtin_export(session: ShellSession, args: list[str], output: Output) -> int:
    """Set environment variables. Usage: export VAR=value"""
    if len(args) < 2:
        # export with no args → print all env vars (same as env program)
        for key in sorted(session.env):
            output.writeln(f"{key}={session.env[key]}")
        return 0

    for arg in args[1:]:
        if "=" in arg:
            key, _, value = arg.partition("=")
            if not key:
                output.error(f"export: invalid variable name: {arg}")
                return 1
            session.env[key] = value
        else:
            # export VAR (without value) — just ensure it's exported
            # In our simple model this is a no-op if it exists
            if arg not in session.env:
                session.env[arg] = ""

    return 0


def get_builtins() -> dict[str, BuiltinFn]:
    """Return the builtin command table."""
    return {
        "cd": builtin_cd,
        "exit": builtin_exit,
        "export": builtin_export,
    }


# Completion callbacks for builtins that need context-sensitive completion.
BUILTIN_COMPLETERS: dict[str, CompletionFn] = {
    "cd": lambda ctx: complete_paths(ctx, dirs_only=True),
}


# Help text for builtins (used by the help program).
# First line is the short description; subsequent lines are usage details.
BUILTIN_HELP: dict[str, str] = {
    "cd": (
        "Change the current working directory\n"
        "\n"
        "Usage: cd [DIR]\n"
        "\n"
        "Navigate to DIR. With no argument, go to HOME."
    ),
    "exit": (
        "Exit the shell\n"
        "\n"
        "Usage: exit [CODE]\n"
        "\n"
        "Terminate the shell session. Exit code defaults to 0."
    ),
    "export": (
        "Set environment variables\n"
        "\n"
        "Usage: export [VAR=value ...]\n"
        "\n"
        "Set one or more environment variables. With no arguments,\n"
        "print all exported variables."
    ),
}
