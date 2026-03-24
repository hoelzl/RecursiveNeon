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
from typing import TYPE_CHECKING, Protocol

from recursive_neon.shell.builtins import BUILTIN_HELP, get_builtins
from recursive_neon.shell.output import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    MAGENTA,
    RED,
    RESET,
    Output,
)
from recursive_neon.shell.parser import tokenize
from recursive_neon.shell.programs import ProgramContext, ProgramRegistry
from recursive_neon.shell.programs.chat import register_chat_program
from recursive_neon.shell.programs.filesystem import register_filesystem_programs
from recursive_neon.shell.programs.notes import register_note_program
from recursive_neon.shell.programs.tasks import register_task_program
from recursive_neon.shell.programs.utility import register_utility_programs
from recursive_neon.shell.session import ShellSession

if TYPE_CHECKING:
    from recursive_neon.dependencies import ServiceContainer


# ---------------------------------------------------------------------------
# InputSource protocol — how the shell receives command lines
# ---------------------------------------------------------------------------


class InputSource(Protocol):
    """Provides command lines to the shell REPL.

    Implementations must be async and raise ``EOFError`` when no more input
    is available (e.g. the user closed the connection).
    """

    async def get_line(self, prompt: str) -> str:
        """Read one line from the user.

        Args:
            prompt: The prompt string (may contain ANSI codes).

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


def _make_shell_completer(
    builtin_names: list[str],
    program_registry: ProgramRegistry,
    session: ShellSession,
):
    """Create a prompt_toolkit Completer for the shell.

    Factory function so the prompt_toolkit import stays lazy — only
    pulled in when the local CLI is actually used.
    """
    from prompt_toolkit.completion import Completer, Completion

    class ShellCompleter(Completer):
        """Tab completion for the shell.

        Completes command names (builtins + programs) for the first word,
        and virtual filesystem paths for subsequent words.

        Uses our own quoting-aware argument parser instead of prompt_toolkit's
        word detection, so that paths like "My Folder"/a are handled correctly.
        """

        def get_completions(self, document, complete_event):
            text = document.text_before_cursor

            arg_start, raw_content = _get_current_argument(text)
            arg_text_len = len(text) - arg_start
            is_first_arg = not text[:arg_start].strip()

            if is_first_arg:
                all_commands = builtin_names + program_registry.list_programs()
                for name in sorted(set(all_commands)):
                    if name.startswith(raw_content):
                        yield Completion(name, start_position=-arg_text_len)
            else:
                yield from self._path_completions(raw_content, arg_text_len)

        def _path_completions(self, raw_path: str, replace_len: int):
            app_svc = session.container.app_service

            if "/" in raw_path:
                last_slash = raw_path.rfind("/")
                dir_part = raw_path[: last_slash + 1] or "/"
                prefix = raw_path[last_slash + 1 :]
            else:
                dir_part = ""
                prefix = raw_path

            try:
                if dir_part:
                    dir_node = session.resolve_path(dir_part)
                else:
                    dir_node = app_svc.get_file(session.cwd_id)
            except (FileNotFoundError, NotADirectoryError, ValueError):
                return

            if dir_node.type != "directory":
                return

            children = app_svc.list_directory(dir_node.id)
            for child in sorted(children, key=lambda n: n.name.lower()):
                if child.name.lower().startswith(prefix.lower()):
                    suffix = "/" if child.type == "directory" else ""
                    display_name = child.name + suffix
                    full_path = dir_part + child.name + suffix
                    completion_text = _quote_path(full_path)

                    yield Completion(
                        completion_text,
                        start_position=-replace_len,
                        display=display_name,
                    )

    return ShellCompleter()


def _get_current_argument(text_before_cursor: str) -> tuple[int, str]:
    """Parse text before the cursor to find the current incomplete argument.

    Walks the text using the same quoting rules as our tokenizer, tracking
    where each argument starts. When we reach the end, whatever we've
    accumulated is the current (possibly incomplete) argument.

    Returns:
        (arg_start_pos, unquoted_content) where arg_start_pos is the index
        in text_before_cursor where the current argument starts, and
        unquoted_content is the argument with quotes/escapes resolved.
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
            # If unclosed, that's fine — we're mid-argument

        elif ch == "'":
            i += 1
            while i < n and text_before_cursor[i] != "'":
                current_raw.append(text_before_cursor[i])
                i += 1
            if i < n:
                i += 1  # skip closing quote

        elif ch in (" ", "\t"):
            # Whitespace — end of current token, start a new one
            current_raw = []
            i += 1
            while i < n and text_before_cursor[i] in (" ", "\t"):
                i += 1
            arg_start = i

        else:
            current_raw.append(ch)
            i += 1

    return arg_start, "".join(current_raw)


# Characters that require quoting when they appear in a filename
_SHELL_SPECIAL = set(" \t'\"\\")


def _quote_path(path: str) -> str:
    """Quote a path for shell insertion, quoting individual segments as needed.

    Only segments containing special characters get quoted. The /
    separators stay unquoted so the path looks natural:
        My Folder/another file.txt  →  "My Folder"/"another file.txt"
        Documents/readme.txt        →  Documents/readme.txt
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

        # Register all system programs
        register_filesystem_programs(self.programs)
        register_utility_programs(self.programs)
        register_chat_program(self.programs)
        register_note_program(self.programs)
        register_task_program(self.programs)

        # Cache help dicts — program registry is immutable after init
        self._program_help: dict[str, str] = {
            name: self.programs.get_help(name) or ""
            for name in self.programs.list_programs()
        }
        self._builtin_help: dict[str, str] = dict(BUILTIN_HELP)

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

        Returns:
            Exit code (0 = success, -1 = exit requested, other = error).
        """
        try:
            tokens = tokenize(line)
        except ValueError as e:
            self.output.error(f"nsh: {e}")
            return 1

        if not tokens:
            return 0

        name = tokens[0]

        # Handle -h / --help for any known command
        if len(tokens) >= 2 and tokens[1] in ("-h", "--help"):
            return self._show_command_help(name)

        # 1. Check builtins
        if name in self.builtins:
            try:
                return await self.builtins[name](self.session, tokens, self.output)
            except Exception as e:
                self.output.error(f"{name}: {e}")
                return 1

        # 2. Check system programs
        program = self.programs.get(name)
        if program is not None:
            ctx = self._make_program_context(tokens)
            try:
                return await program.run(ctx)
            except Exception as e:
                self.output.error(f"{name}: {e}")
                return 1

        # 3. Future: check PATH for executable scripts

        self.output.error(f"nsh: command not found: {name}")
        return 127

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

    def _make_program_context(self, args: list[str]) -> ProgramContext:
        """Create a ProgramContext from current session state."""
        env = dict(self.session.env)
        if self.data_dir:
            env["_data_dir"] = self.data_dir

        return ProgramContext(
            args=args,
            stdout=self.output,
            stderr=self.output,
            env=env,
            services=self.session.container,
            cwd_id=self.session.cwd_id,
            builtin_help=self._builtin_help,
            program_help=self._program_help,
        )

    def get_completions(self, text: str) -> list[str]:
        """Return completion candidates for *text* (transport-agnostic).

        Used by WebSocket tab-completion handler.  For prompt_toolkit,
        the ``ShellCompleter`` adapter calls this internally via the same
        underlying helpers.
        """
        arg_start, raw_content = _get_current_argument(text)
        is_first_arg = not text[:arg_start].strip()

        if is_first_arg:
            all_commands = list(self.builtins.keys()) + self.programs.list_programs()
            return sorted({n for n in all_commands if n.startswith(raw_content)})

        # Path completions
        return self._path_completion_strings(raw_content)

    def _path_completion_strings(self, raw_path: str) -> list[str]:
        """Return matching path strings for a partial path."""
        app_service = self.session.container.app_service

        if "/" in raw_path:
            last_slash = raw_path.rfind("/")
            dir_part = raw_path[: last_slash + 1] or "/"
            prefix = raw_path[last_slash + 1 :]
        else:
            dir_part = ""
            prefix = raw_path

        try:
            if dir_part:
                dir_node = self.session.resolve_path(dir_part)
            else:
                dir_node = app_service.get_file(self.session.cwd_id)
        except (FileNotFoundError, NotADirectoryError, ValueError):
            return []

        if dir_node.type != "directory":
            return []

        children = app_service.list_directory(dir_node.id)
        results: list[str] = []
        for child in sorted(children, key=lambda n: n.name.lower()):
            if child.name.lower().startswith(prefix.lower()):
                suffix = "/" if child.type == "directory" else ""
                full_path = dir_part + child.name + suffix
                results.append(_quote_path(full_path))
        return results

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
    """

    def __init__(self, shell: Shell, data_dir: str | None = None) -> None:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory, InMemoryHistory

        completer = _make_shell_completer(
            builtin_names=list(shell.builtins.keys()),
            program_registry=shell.programs,
            session=shell.session,
        )

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

    async def get_line(self, prompt: str) -> str:
        """Read a line using prompt_toolkit (supports ANSI prompts)."""
        from prompt_toolkit.formatted_text import ANSI

        return await self._prompt_session.prompt_async(ANSI(prompt))
