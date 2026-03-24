"""
Task program — manage task lists and tasks from the shell.

Subcommands: lists, list, add, done, undone, delete.
"""

from __future__ import annotations

from recursive_neon.models.app_models import TaskList
from recursive_neon.shell.output import BOLD, CYAN, DIM, GREEN, RED, YELLOW
from recursive_neon.shell.programs import ProgramContext, ProgramRegistry

DEFAULT_LIST_NAME = "default"


async def prog_task(ctx: ProgramContext) -> int:
    """Dispatch task subcommands."""
    if len(ctx.args) < 2:
        ctx.stderr.error(
            "task: missing subcommand (lists, list, add, done, undone, delete)"
        )
        return 1

    sub = ctx.args[1]
    dispatch = {
        "lists": _task_lists,
        "list": _task_list,
        "ls": _task_list,
        "add": _task_add,
        "new": _task_add,
        "done": _task_done,
        "undone": _task_undone,
        "delete": _task_delete,
        "rm": _task_delete,
    }
    handler = dispatch.get(sub)
    if handler is None:
        ctx.stderr.error(f"task: unknown subcommand '{sub}'")
        return 1
    return await handler(ctx)


def _get_default_list(ctx: ProgramContext) -> TaskList | None:
    """Get the single/default task list, or None if ambiguous."""
    lists = ctx.services.app_service.get_task_lists()
    if len(lists) == 1:
        return lists[0]
    # Look for one named "default"
    for tl in lists:
        if tl.name.lower() == DEFAULT_LIST_NAME:
            return tl
    return None


def _find_list_by_name(ctx: ProgramContext, name: str) -> TaskList | None:
    """Find a task list by name (case-insensitive)."""
    for tl in ctx.services.app_service.get_task_lists():
        if tl.name.lower() == name.lower():
            return tl
    return None


def _resolve_list(ctx: ProgramContext, args: list[str]) -> TaskList | None:
    """Resolve --list flag or fall back to default list."""
    # Check for --list / -l flag
    for i, arg in enumerate(args):
        if arg in ("--list", "-l") and i + 1 < len(args):
            return _find_list_by_name(ctx, args[i + 1])
    return _get_default_list(ctx)


def _ensure_default_list(ctx: ProgramContext) -> TaskList:
    """Get or auto-create the default task list."""
    tl = _get_default_list(ctx)
    if tl is not None:
        return tl
    return ctx.services.app_service.create_task_list({"name": DEFAULT_LIST_NAME})


async def _task_lists(ctx: ProgramContext) -> int:
    """List all task lists."""
    lists = ctx.services.app_service.get_task_lists()
    if not lists:
        ctx.stdout.writeln("No task lists.")
        return 0

    for tl in lists:
        total = len(tl.tasks)
        done = sum(1 for t in tl.tasks if t.completed)
        name = ctx.stdout.styled(tl.name, BOLD)
        count = ctx.stdout.styled(f"({done}/{total})", DIM)
        ctx.stdout.writeln(f"  {name} {count}")
    return 0


async def _task_list(ctx: ProgramContext) -> int:
    """List tasks in a specific list."""
    # task list [name]
    if len(ctx.args) > 2:
        tl = _find_list_by_name(ctx, ctx.args[2])
        if tl is None:
            ctx.stderr.error(f"task list: list '{ctx.args[2]}' not found")
            return 1
    else:
        tl = _get_default_list(ctx)
        if tl is None:
            lists = ctx.services.app_service.get_task_lists()
            if not lists:
                ctx.stdout.writeln("No task lists. Use 'task add <title>' to create one.")
                return 0
            ctx.stderr.error(
                "task list: multiple lists exist, specify a name or use 'task lists'"
            )
            return 1

    if not tl.tasks:
        ctx.stdout.writeln(
            f"{ctx.stdout.styled(tl.name, BOLD)}: no tasks"
        )
        return 0

    ctx.stdout.writeln(ctx.stdout.styled(tl.name, BOLD))
    for i, task in enumerate(tl.tasks, 1):
        if task.completed:
            marker = ctx.stdout.styled("[x]", GREEN)
            title = ctx.stdout.styled(task.title, DIM)
        else:
            marker = ctx.stdout.styled("[ ]", RED)
            title = task.title
        idx = ctx.stdout.styled(f"{i}.", YELLOW)
        ctx.stdout.writeln(f"  {idx} {marker} {title}")
    return 0


async def _task_add(ctx: ProgramContext) -> int:
    """Add a new task."""
    # task add <title> [--list <name>]
    args = ctx.args[2:]
    if not args:
        ctx.stderr.error("task add: missing title")
        return 1

    title_parts: list[str] = []
    list_name: str | None = None
    i = 0
    while i < len(args):
        if args[i] in ("--list", "-l") and i + 1 < len(args):
            list_name = args[i + 1]
            i += 2
        else:
            title_parts.append(args[i])
            i += 1

    title = " ".join(title_parts)
    if not title:
        ctx.stderr.error("task add: missing title")
        return 1

    if list_name:
        tl = _find_list_by_name(ctx, list_name)
        if tl is None:
            ctx.stderr.error(f"task add: list '{list_name}' not found")
            return 1
    else:
        tl = _ensure_default_list(ctx)

    task = ctx.services.app_service.create_task(
        tl.id, {"title": title, "completed": False}
    )
    ctx.stdout.writeln(
        f"Added to {ctx.stdout.styled(tl.name, CYAN)}: {task.title}"
    )
    return 0


def _resolve_task(ctx: ProgramContext, ref: str, tl: TaskList):
    """Resolve a task reference (1-based index or UUID prefix) within a list."""
    try:
        idx = int(ref)
        if 1 <= idx <= len(tl.tasks):
            return tl.tasks[idx - 1]
    except ValueError:
        pass
    for task in tl.tasks:
        if task.id.startswith(ref):
            return task
    return None


async def _task_done(ctx: ProgramContext) -> int:
    """Mark a task as done."""
    if len(ctx.args) < 3:
        ctx.stderr.error("task done: missing task reference")
        return 1

    tl = _resolve_list(ctx, ctx.args[3:])
    if tl is None:
        ctx.stderr.error("task done: could not determine task list")
        return 1

    task = _resolve_task(ctx, ctx.args[2], tl)
    if task is None:
        ctx.stderr.error(f"task done: task '{ctx.args[2]}' not found")
        return 1

    ctx.services.app_service.update_task(tl.id, task.id, {"completed": True})
    ctx.stdout.writeln(
        f"{ctx.stdout.styled('[x]', GREEN)} {task.title}"
    )
    return 0


async def _task_undone(ctx: ProgramContext) -> int:
    """Mark a task as not done."""
    if len(ctx.args) < 3:
        ctx.stderr.error("task undone: missing task reference")
        return 1

    tl = _resolve_list(ctx, ctx.args[3:])
    if tl is None:
        ctx.stderr.error("task undone: could not determine task list")
        return 1

    task = _resolve_task(ctx, ctx.args[2], tl)
    if task is None:
        ctx.stderr.error(f"task undone: task '{ctx.args[2]}' not found")
        return 1

    ctx.services.app_service.update_task(tl.id, task.id, {"completed": False})
    ctx.stdout.writeln(
        f"{ctx.stdout.styled('[ ]', RED)} {task.title}"
    )
    return 0


async def _task_delete(ctx: ProgramContext) -> int:
    """Delete a task."""
    if len(ctx.args) < 3:
        ctx.stderr.error("task delete: missing task reference")
        return 1

    tl = _resolve_list(ctx, ctx.args[3:])
    if tl is None:
        ctx.stderr.error("task delete: could not determine task list")
        return 1

    task = _resolve_task(ctx, ctx.args[2], tl)
    if task is None:
        ctx.stderr.error(f"task delete: task '{ctx.args[2]}' not found")
        return 1

    ctx.services.app_service.delete_task(tl.id, task.id)
    ctx.stdout.writeln(f"Deleted task: {task.title}")
    return 0


def register_task_program(registry: ProgramRegistry) -> None:
    """Register the task program."""
    registry.register_fn(
        "task",
        prog_task,
        "Manage tasks\n"
        "\n"
        "Usage: task <subcommand> [args...]\n"
        "\n"
        "Subcommands:\n"
        "  lists              List all task lists\n"
        "  list [name]        Show tasks in a list\n"
        "  add <title>        Add a task (--list <name>)\n"
        "  done <ref>         Mark task as complete\n"
        "  undone <ref>       Mark task as incomplete\n"
        "  delete <ref>       Delete a task",
    )
