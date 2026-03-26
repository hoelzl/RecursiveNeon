"""
Shell REPL — the main interactive loop.

The Shell class is transport-agnostic: it receives input lines via an
InputSource protocol and writes output via an Output object.  The default
PromptToolkitInput drives the shell from a real terminal; other
implementations (e.g. WebSocket) can supply lines from any source.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Protocol

from recursive_neon.shell.builtins import BUILTIN_COMPLETERS, BUILTIN_HELP, get_builtins
from recursive_neon.shell.completion import (
    CompletionContext,
    CompletionFn,
    complete_choices,
    complete_paths,
    get_current_argument,
    quote_path,
)
from recursive_neon.shell.glob import expand_globs
from recursive_neon.shell.output import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    MAGENTA,
    RED,
    RESET,
    CapturedOutput,
    Output,
)
from recursive_neon.shell.parser import (
    Redirect,
    _skip_double_quoted,
    _skip_single_quoted,
    parse_pipeline,
    tokenize,
)
from recursive_neon.shell.programs import ProgramContext, ProgramRegistry
from recursive_neon.shell.programs.chat import register_chat_program
from recursive_neon.shell.programs.codebreaker import register_codebreaker_program
from recursive_neon.shell.programs.filesystem import register_filesystem_programs
from recursive_neon.shell.programs.notes import register_note_program
from recursive_neon.shell.programs.tasks import register_task_program
from recursive_neon.shell.programs.utility import register_utility_programs
from recursive_neon.shell.session import ShellSession

if TYPE_CHECKING:
    from recursive_neon.dependencies import ServiceContainer
    from recursive_neon.shell.tui import TuiApp

# Backward-compatible aliases — tests import these from here.
_get_current_argument = get_current_argument
_quote_path = quote_path

# A factory that creates a ``run_tui`` callback for a ProgramContext.
# Set by the terminal session or local CLI to enable TUI apps.
RunTuiFactory = Callable[[], Callable[["TuiApp"], Awaitable[int]]]

# ---------------------------------------------------------------------------
# InputSource protocol — how the shell receives command lines
# ---------------------------------------------------------------------------


class InputSource(Protocol):
    """Provides command lines to the shell REPL.

    Implementations must be async and raise ``EOFError`` when no more input
    is available (e.g. the user closed the connection).
    """

    async def get_line(
        self,
        prompt: str,
        *,
        complete: bool = True,
        history_id: str | None = None,
    ) -> str:
        """Read one line from the user.

        Args:
            prompt: The prompt string (may contain ANSI codes).
            complete: Whether to offer tab-completion. Defaults to True.
            history_id: If given, use a separate input history keyed by this
                string instead of the main shell history. This prevents
                program input (e.g. chat messages) from polluting the
                shell's command history and vice versa.

        Returns:
            The raw line entered by the user.

        Raises:
            EOFError: No more input available.
            KeyboardInterrupt: User pressed Ctrl-C (skip this line).
        """
        ...


logger = logging.getLogger(__name__)


WELCOME_BANNER = """\
\033[36m╔══════════════════════════════════════════════════╗
║  Recursive://Neon                                ║
║  Connection established to neon-proxy            ║
║  Type 'help' for available commands              ║
╚══════════════════════════════════════════════════╝\033[0m
"""


def _last_pipe_segment(text: str) -> str:
    """Return text after the last unquoted ``|``.

    Used by completion to scope to the current pipeline segment.
    Uses shared quote-skipping helpers from ``parser.py``.
    """
    last_pipe = -1
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\\" and i + 1 < n:
            i += 2
        elif ch == '"':
            i, _ = _skip_double_quoted(text, i + 1)
        elif ch == "'":
            i, _ = _skip_single_quoted(text, i + 1)
        elif ch == "|":
            last_pipe = i
            i += 1
        else:
            i += 1
    if last_pipe >= 0:
        return text[last_pipe + 1 :]
    return text


def _make_shell_completer(shell: Shell):
    """Create a prompt_toolkit Completer for the shell.

    Factory function so the prompt_toolkit import stays lazy — only
    pulled in when the local CLI is actually used.
    """
    from prompt_toolkit.completion import Completer, Completion

    class ShellCompleter(Completer):
        """Tab completion for the shell.

        Delegates to per-command completers registered on the Shell.
        Falls back to filesystem path completion for unknown commands.
        """

        def get_completions(self, document, complete_event):
            items, replace_len = shell.get_completions_ext(document.text_before_cursor)
            for item in items:
                yield Completion(item, start_position=-replace_len)

    return ShellCompleter()


class Shell:
    """The main shell REPL.

    Transport-agnostic: call ``run()`` with a ``PromptToolkitInput`` for
    the local CLI, or supply any other ``InputSource`` implementation
    (e.g. a WebSocket adapter) to drive the shell remotely.
    """

    def __init__(
        self,
        container: ServiceContainer,
        output: Output | None = None,
        data_dir: str | None = None,
    ) -> None:
        self.output = output or Output()
        self.session = ShellSession(container)
        self.data_dir = data_dir
        self.builtins = get_builtins()
        self.programs = ProgramRegistry()
        self._input_source: InputSource | None = None
        self._run_tui_factory: RunTuiFactory | None = None

        # Register all system programs
        register_filesystem_programs(self.programs)
        register_utility_programs(self.programs)
        register_chat_program(self.programs)
        register_note_program(self.programs)
        register_task_program(self.programs)
        register_codebreaker_program(self.programs)

        # Cache help dicts — program registry is immutable after init
        self._program_help: dict[str, str] = {
            name: self.programs.get_help(name) or ""
            for name in self.programs.list_programs()
        }
        self._builtin_help: dict[str, str] = dict(BUILTIN_HELP)

        # Builtin completers
        self._builtin_completers: dict[str, CompletionFn] = dict(BUILTIN_COMPLETERS)

        # Register `help` completer now that all command names are known
        all_cmd_names = sorted(set(list(self.builtins) + self.programs.list_programs()))

        def _complete_help(ctx: CompletionContext) -> list[str]:
            if ctx.arg_index == 1:
                return complete_choices(all_cmd_names, ctx.current)
            return []

        self.programs.set_completer("help", _complete_help)

    async def run(self, input_source: InputSource | None = None) -> None:
        """Main REPL loop.

        Args:
            input_source: Where to read command lines from.  When *None*,
                creates a ``PromptToolkitInput`` for local terminal use.
        """
        if input_source is None:
            input_source = PromptToolkitInput(
                shell=self,
                data_dir=self.data_dir,
            )
        self._input_source = input_source

        self.output.write(WELCOME_BANNER)

        while True:
            try:
                prompt_text = self._build_prompt()
                line = await input_source.get_line(prompt_text)
            except KeyboardInterrupt:
                self.output.writeln()
                continue
            except EOFError:
                self.output.writeln()
                break

            line = line.strip()
            if not line:
                continue

            self.session.history.append(line)
            exit_code = await self.execute_line(line)

            if exit_code == -1:
                # exit builtin requested termination
                break

            self.session.last_exit_code = exit_code

        # Save game state on exit
        self._save_game_state()

    def _save_game_state(self) -> None:
        """Save all game state to disk."""
        if not self.data_dir:
            return
        try:
            container = self.session.container
            container.app_service.save_all_to_disk(self.data_dir)
            container.npc_manager.save_npcs_to_disk(self.data_dir)
            logger.info("Game state saved to %s", self.data_dir)
        except Exception as e:
            logger.error("Failed to save game state: %s", e)

    async def execute_line(self, line: str) -> int:
        """Parse and execute a single command line.

        Supports pipes (``|``) and output redirection (``>``, ``>>``).

        Returns:
            Exit code (0 = success, -1 = exit requested, other = error).
        """
        try:
            pipeline = parse_pipeline(line)
        except ValueError as e:
            self.output.error(f"nsh: {e}")
            return 1

        if not pipeline.segments or not pipeline.segments[0].tokens:
            return 0

        # Simple case: single command, no redirect
        if len(pipeline.segments) == 1 and pipeline.redirect is None:
            tokens = expand_globs(
                pipeline.segments[0].tokens,
                self.session.cwd_id,
                self.session.container.app_service,
            )
            return await self._execute_tokens(tokens, self.output)

        # Pipeline / redirect execution
        stdin_text: str | None = None
        last_exit = 0

        for i, seg in enumerate(pipeline.segments):
            tokens = expand_globs(
                seg.tokens,
                self.session.cwd_id,
                self.session.container.app_service,
            )
            is_last = i == len(pipeline.segments) - 1

            if not is_last or pipeline.redirect is not None:
                # Capture stdout for piping or redirect
                captured = CapturedOutput()
                last_exit = await self._execute_tokens(
                    tokens, captured, stdin=stdin_text
                )
                stdin_text = captured.text
            else:
                # Last segment, no redirect — write to real output
                last_exit = await self._execute_tokens(
                    tokens, self.output, stdin=stdin_text
                )

        # Handle redirect
        if pipeline.redirect is not None:
            self._write_redirect(pipeline.redirect, stdin_text or "")

        return last_exit

    async def _execute_tokens(
        self,
        tokens: list[str],
        output: Output,
        *,
        stdin: str | None = None,
    ) -> int:
        """Execute a single command from expanded tokens.

        Args:
            tokens: Expanded argv-style tokens (first is command name).
            output: Where stdout goes (may be CapturedOutput for pipes).
            stdin: Piped input from a previous command, or None.

        Returns:
            Exit code.
        """
        if not tokens:
            return 0

        name = tokens[0]

        # Handle -h / --help for any known command
        if len(tokens) >= 2 and tokens[1] in ("-h", "--help"):
            return self._show_command_help(name)

        # 1. Check builtins (builtins don't participate in pipes)
        if name in self.builtins:
            try:
                return await self.builtins[name](self.session, tokens, output)
            except Exception as e:
                self.output.error(f"{name}: {e}")
                return 1

        # 2. Check system programs
        program = self.programs.get(name)
        if program is not None:
            ctx = self._make_program_context(tokens, output=output, stdin=stdin)
            try:
                return await program.run(ctx)
            except Exception as e:
                # Errors go to the real output, not the pipe
                self.output.error(f"{name}: {e}")
                return 1

        self.output.error(f"nsh: command not found: {name}")
        return 127

    def _write_redirect(self, redirect: Redirect, content: str) -> None:
        """Write captured output to a virtual file."""
        app_service = self.session.container.app_service
        try:
            node = self.session.resolve_path(redirect.target)
            if node.type == "directory":
                self.output.error(f"nsh: {redirect.target}: Is a directory")
                return
            if redirect.mode == ">>":
                existing = node.content or ""
                content = existing + content
            app_service.update_file(node.id, {"content": content})
        except FileNotFoundError:
            try:
                from recursive_neon.shell.path_resolver import resolve_parent_and_name

                parent, fname = resolve_parent_and_name(
                    redirect.target,
                    self.session.cwd_id,
                    app_service,
                )
                app_service.create_file(
                    {"name": fname, "parent_id": parent.id, "content": content}
                )
            except (FileNotFoundError, NotADirectoryError, ValueError) as e:
                self.output.error(f"nsh: {e}")
        except NotADirectoryError as e:
            self.output.error(f"nsh: {e}")

    def _show_command_help(self, name: str) -> int:
        """Print help text for a builtin or program. Returns exit code."""
        help_text = BUILTIN_HELP.get(name)
        if help_text:
            first, _, rest = help_text.partition("\n")
            self.output.writeln(f"{name} (builtin): {first}")
            if rest:
                self.output.writeln(rest)
            return 0
        help_text = self.programs.get_help(name)
        if help_text:
            first, _, rest = help_text.partition("\n")
            self.output.writeln(f"{name}: {first}")
            if rest:
                self.output.writeln(rest)
            return 0
        self.output.error(f"nsh: command not found: {name}")
        return 127

    def _make_program_context(
        self,
        args: list[str],
        *,
        output: Output | None = None,
        stdin: str | None = None,
    ) -> ProgramContext:
        """Create a ProgramContext from current session state."""
        env = dict(self.session.env)
        if self.data_dir:
            env["_data_dir"] = self.data_dir

        run_tui = self._run_tui_factory() if self._run_tui_factory else None
        stdout = output or self.output

        return ProgramContext(
            args=args,
            stdout=stdout,
            stderr=self.output,  # stderr always goes to real output
            env=env,
            services=self.session.container,
            cwd_id=self.session.cwd_id,
            builtin_help=self._builtin_help,
            program_help=self._program_help,
            get_line=self._input_source.get_line if self._input_source else None,
            run_tui=run_tui,
            stdin=stdin,
        )

    def get_completions(self, text: str) -> list[str]:
        """Return completion candidates for *text* (transport-agnostic).

        Used by WebSocket tab-completion handler.  For prompt_toolkit,
        the ``ShellCompleter`` adapter calls this internally via the same
        underlying helpers.
        """
        items, _ = self.get_completions_ext(text)
        return items

    def get_completions_ext(self, text: str) -> tuple[list[str], int]:
        """Like ``get_completions`` but also returns the replacement length.

        Delegates to per-command completers when available; falls back to
        filesystem path completion for unknown commands.  Pipe-aware:
        when the cursor is after a ``|``, completions apply to the
        current segment only.

        Returns:
            (items, replace_len) where *replace_len* is the number of
            characters before the cursor that the completions replace.
        """
        # Pipe-aware: find the last unquoted | and scope to that segment
        text = _last_pipe_segment(text)

        arg_start, raw_content = get_current_argument(text)
        replace_len = len(text) - arg_start
        completed_text = text[:arg_start].strip()

        if not completed_text:
            # First argument — complete command names
            all_commands = list(self.builtins.keys()) + self.programs.list_programs()
            items = sorted({n for n in all_commands if n.startswith(raw_content)})
            return items, replace_len

        # Non-first argument — try command-specific completer
        try:
            preceding_tokens = tokenize(completed_text)
        except ValueError:
            return [], replace_len

        if not preceding_tokens:
            return [], replace_len

        command = preceding_tokens[0]
        completer = self._builtin_completers.get(
            command
        ) or self.programs.get_completer(command)

        ctx = CompletionContext(
            args=preceding_tokens,
            current=raw_content,
            arg_index=len(preceding_tokens),
            services=self.session.container,
            cwd_id=self.session.cwd_id,
        )

        items = completer(ctx) if completer is not None else complete_paths(ctx)
        return items, replace_len

    def _build_prompt(self) -> str:
        """Build the colored shell prompt string."""
        cwd = self.session.get_cwd_path()
        user = self.session.username
        host = self.session.hostname

        sigil_color = RED if self.session.last_exit_code != 0 else MAGENTA

        return (
            f"{GREEN}{user}{RESET}"
            f"{DIM}@{RESET}"
            f"{CYAN}{host}{RESET}"
            f"{DIM}:{RESET}"
            f"{BOLD}{cwd}{RESET}"
            f"{sigil_color}${RESET} "
        )


# ---------------------------------------------------------------------------
# PromptToolkitInput — local terminal input source
# ---------------------------------------------------------------------------


class PromptToolkitInput:
    """InputSource backed by prompt_toolkit (readline, history, completion).

    This is the default input source for ``Shell.run()`` when running in a
    real terminal.  It is deliberately kept in this module (rather than a
    separate file) because it needs access to ``ShellCompleter`` and the
    prompt_toolkit imports.

    Also wires up TUI support for the local CLI via ``_run_tui_factory``.
    """

    def __init__(self, shell: Shell, data_dir: str | None = None) -> None:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory, InMemoryHistory

        completer = _make_shell_completer(shell)

        history: FileHistory | InMemoryHistory
        if data_dir:
            history_path = Path(data_dir) / "history.txt"
            history_path.parent.mkdir(parents=True, exist_ok=True)
            history = FileHistory(str(history_path))
        else:
            history = InMemoryHistory()

        self._prompt_session: PromptSession[str] = PromptSession(
            history=history,
            completer=completer,
        )
        self._alt_sessions: dict[str, PromptSession[str]] = {}
        self._shell = shell

        # Wire up TUI support for the local terminal
        shell._run_tui_factory = self._make_run_tui

    def _make_run_tui(self) -> Callable[[Any], Awaitable[int]]:
        """Create a run_tui callback for local terminal raw mode."""
        from recursive_neon.shell.tui.runner import run_tui_app

        shell = self._shell

        async def _run_tui(app: Any) -> int:
            raw_input = LocalRawInput()
            return await run_tui_app(
                app,
                raw_input,
                shell.output,
                enter_raw=lambda: _enter_alt_screen(),
                exit_raw=lambda: _exit_alt_screen(),
            )

        return _run_tui

    def _get_alt_session(self, history_id: str) -> Any:
        """Return (or create) a PromptSession with its own InMemoryHistory."""
        if history_id not in self._alt_sessions:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import InMemoryHistory

            self._alt_sessions[history_id] = PromptSession(
                history=InMemoryHistory(),
            )
        return self._alt_sessions[history_id]

    async def get_line(
        self,
        prompt: str,
        *,
        complete: bool = True,
        history_id: str | None = None,
    ) -> str:
        """Read a line using prompt_toolkit (supports ANSI prompts)."""
        from prompt_toolkit.formatted_text import ANSI

        session = (
            self._get_alt_session(history_id)
            if history_id is not None
            else self._prompt_session
        )

        if complete:
            return await session.prompt_async(ANSI(prompt))

        from prompt_toolkit.completion import WordCompleter

        return await session.prompt_async(
            ANSI(prompt),
            completer=WordCompleter([]),
            complete_while_typing=False,
        )


# ---------------------------------------------------------------------------
# LocalRawInput — raw keystroke reading for the local terminal
# ---------------------------------------------------------------------------


def _enter_alt_screen() -> None:
    """Switch to the alternate screen buffer."""
    import sys as _sys

    _sys.stdout.write("\033[?1049h")
    _sys.stdout.flush()


def _exit_alt_screen() -> None:
    """Return to the normal screen buffer."""
    import sys as _sys

    _sys.stdout.write("\033[?1049l")
    _sys.stdout.flush()


class LocalRawInput:
    """RawInputSource for the local terminal.

    Reads individual keystrokes using platform-specific APIs,
    running the blocking read in a thread executor.
    """

    async def get_key(self) -> str:
        from recursive_neon.shell.keys import read_key_async

        return await read_key_async()
