"""
Utility programs: help, clear, echo, env, whoami, hostname, date.
"""

from __future__ import annotations

from datetime import datetime

from recursive_neon.shell.output import BOLD, CYAN
from recursive_neon.shell.programs import ProgramContext, ProgramRegistry


async def prog_help(ctx: ProgramContext) -> int:
    """List available commands or show help for a specific command."""
    builtin_help = ctx.builtin_help or {}
    program_help = ctx.program_help or {}

    if len(ctx.args) > 1:
        name = ctx.args[1]
        if name in builtin_help:
            first, _, rest = builtin_help[name].partition("\n")
            ctx.stdout.writeln(f"{ctx.stdout.styled(name, BOLD)} (builtin): {first}")
            if rest:
                ctx.stdout.writeln(rest)
            return 0
        if name in program_help:
            first, _, rest = program_help[name].partition("\n")
            ctx.stdout.writeln(f"{ctx.stdout.styled(name, BOLD)}: {first}")
            if rest:
                ctx.stdout.writeln(rest)
            return 0
        ctx.stderr.error(f"help: no help for '{name}'")
        return 1

    ctx.stdout.writeln(ctx.stdout.styled("Shell builtins:", BOLD))
    for name in sorted(builtin_help):
        short = builtin_help[name].split("\n", 1)[0]
        ctx.stdout.writeln(f"  {ctx.stdout.styled(name, CYAN):20s} {short}")

    ctx.stdout.writeln()
    ctx.stdout.writeln(ctx.stdout.styled("Programs:", BOLD))
    for name in sorted(program_help):
        if not name.startswith("_"):
            short = program_help[name].split("\n", 1)[0]
            ctx.stdout.writeln(f"  {ctx.stdout.styled(name, CYAN):20s} {short}")

    return 0


async def prog_clear(ctx: ProgramContext) -> int:
    """Clear the terminal screen."""
    ctx.stdout.write("\033[2J\033[H")
    return 0


async def prog_echo(ctx: ProgramContext) -> int:
    """Print arguments to stdout."""
    parts = ctx.args[1:]
    # Simple $VAR expansion
    expanded = []
    for part in parts:
        if part.startswith("$"):
            var_name = part[1:]
            expanded.append(ctx.env.get(var_name, ""))
        else:
            expanded.append(part)
    ctx.stdout.writeln(" ".join(expanded))
    return 0


async def prog_env(ctx: ProgramContext) -> int:
    """Print all environment variables."""
    for key in sorted(ctx.env):
        # Skip internal help data
        if key.startswith("_"):
            continue
        ctx.stdout.writeln(f"{key}={ctx.env[key]}")
    return 0


async def prog_whoami(ctx: ProgramContext) -> int:
    """Print current username."""
    ctx.stdout.writeln(ctx.env.get("USER", "unknown"))
    return 0


async def prog_hostname(ctx: ProgramContext) -> int:
    """Print system hostname."""
    ctx.stdout.writeln(ctx.env.get("HOSTNAME", "unknown"))
    return 0


async def prog_date(ctx: ProgramContext) -> int:
    """Print current date and time."""
    ctx.stdout.writeln(datetime.now().strftime("%a %b %d %H:%M:%S %Y"))
    return 0


async def prog_save(ctx: ProgramContext) -> int:
    """Save game state to disk."""
    data_dir = ctx.env.get("_data_dir", "")
    if not data_dir:
        ctx.stderr.error("save: no data directory configured")
        return 1
    try:
        ctx.services.app_service.save_all_to_disk(data_dir)
        ctx.services.npc_manager.save_npcs_to_disk(data_dir)
        ctx.stdout.writeln("Game state saved.")
        return 0
    except Exception as e:
        ctx.stderr.error(f"save: {e}")
        return 1


def register_utility_programs(
    registry: ProgramRegistry,
) -> None:
    """Register all utility programs."""
    registry.register_fn(
        "help",
        prog_help,
        "Show available commands\n"
        "\n"
        "Usage: help [COMMAND]\n"
        "\n"
        "With no argument, list all commands. With COMMAND, show its help.",
    )
    registry.register_fn("clear", prog_clear, "Clear the terminal screen")
    registry.register_fn(
        "echo",
        prog_echo,
        "Print text to stdout\n"
        "\n"
        "Usage: echo [TEXT...]\n"
        "\n"
        "Print arguments separated by spaces. Supports $VAR expansion.",
    )
    registry.register_fn("env", prog_env, "Print environment variables")
    registry.register_fn("whoami", prog_whoami, "Print current username")
    registry.register_fn("hostname", prog_hostname, "Print system hostname")
    registry.register_fn("date", prog_date, "Print current date and time")
    registry.register_fn(
        "save",
        prog_save,
        "Save game state to disk\n"
        "\n"
        "Usage: save\n"
        "\n"
        "Saves filesystem, notes, tasks, and NPC state.",
    )
