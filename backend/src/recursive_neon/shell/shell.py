"""
Shell REPL — the main interactive loop.

Uses prompt_toolkit for line editing, history, and tab completion.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.history import InMemoryHistory

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
from recursive_neon.shell.programs.utility import register_utility_programs
from recursive_neon.shell.session import ShellSession

if TYPE_CHECKING:
    from recursive_neon.dependencies import ServiceContainer

logger = logging.getLogger(__name__)


WELCOME_BANNER = """\
\033[36m╔══════════════════════════════════════════════════╗
║  Recursive://Neon                                ║
║  Connection established to neon-proxy            ║
║  Type 'help' for available commands              ║
╚══════════════════════════════════════════════════╝\033[0m
"""


class ShellCompleter(Completer):
    """Tab completion for the shell.

    Completes command names (builtins + programs) for the first word,
    and virtual filesystem paths for subsequent words.

    Uses our own quoting-aware argument parser instead of prompt_toolkit's
    word detection, so that paths like "My Folder"/a are handled correctly.
    """

    def __init__(
        self,
        builtin_names: list[str],
        program_registry: ProgramRegistry,
        session: ShellSession,
    ) -> None:
        self._builtin_names = builtin_names
        self._program_registry = program_registry
        self._session = session

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        arg_start, raw_content = _get_current_argument(text)
        arg_text_len = len(text) - arg_start
        is_first_arg = not text[:arg_start].strip()

        if is_first_arg:
            # First word — complete command names
            all_commands = self._builtin_names + self._program_registry.list_programs()
            for name in sorted(set(all_commands)):
                if name.startswith(raw_content):
                    yield Completion(name, start_position=-arg_text_len)
        else:
            # Subsequent words — complete file paths
            yield from self._path_completions(raw_content, arg_text_len)

    def _path_completions(self, raw_path: str, replace_len: int):
        """Complete virtual filesystem paths.

        Args:
            raw_path: The unquoted path content typed so far.
            replace_len: Number of characters to replace on the input line
                         (the full extent of the current argument including quotes).
        """
        app_service = self._session.container.app_service

        # Split into directory part and name prefix
        if "/" in raw_path:
            last_slash = raw_path.rfind("/")
            dir_part = raw_path[: last_slash + 1] or "/"
            prefix = raw_path[last_slash + 1 :]
        else:
            dir_part = ""
            prefix = raw_path

        # Resolve directory to list children
        try:
            if dir_part:
                dir_node = self._session.resolve_path(dir_part)
            else:
                dir_node = app_service.get_file(self._session.cwd_id)
        except (FileNotFoundError, NotADirectoryError, ValueError):
            return

        if dir_node.type != "directory":
            return

        children = app_service.list_directory(dir_node.id)
        for child in sorted(children, key=lambda n: n.name.lower()):
            if child.name.lower().startswith(prefix.lower()):
                suffix = "/" if child.type == "directory" else ""
                display_name = child.name + suffix

                # Build full path and quote per-segment
                full_path = dir_part + child.name + suffix
                completion_text = _quote_path(full_path)

                yield Completion(
                    completion_text,
                    start_position=-replace_len,
                    display=display_name,
                )


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
    """The main shell REPL."""

    def __init__(
        self,
        container: ServiceContainer,
        output: Output | None = None,
    ) -> None:
        self.output = output or Output()
        self.session = ShellSession(container)
        self.builtins = get_builtins()
        self.programs = ProgramRegistry()

        # Register all system programs
        register_filesystem_programs(self.programs)
        register_utility_programs(self.programs)
        register_chat_program(self.programs)

    async def run(self) -> None:
        """Main REPL loop."""
        self.output.write(WELCOME_BANNER)

        completer = ShellCompleter(
            builtin_names=list(self.builtins.keys()),
            program_registry=self.programs,
            session=self.session,
        )

        prompt_session: PromptSession[str] = PromptSession(
            history=InMemoryHistory(),
            completer=completer,
        )

        while True:
            try:
                prompt_text = ANSI(self._build_prompt())
                line = await prompt_session.prompt_async(prompt_text)
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
            self.output.writeln(f"{name} (builtin): {help_text}")
            return 0
        help_text = self.programs.get_help(name)
        if help_text:
            self.output.writeln(f"{name}: {help_text}")
            return 0
        self.output.error(f"nsh: command not found: {name}")
        return 127

    def _make_program_context(self, args: list[str]) -> ProgramContext:
        """Create a ProgramContext from current session state."""
        # Pass help data through env so the help program can access it
        env = dict(self.session.env)
        env["_builtin_help"] = json.dumps(BUILTIN_HELP)
        program_help = {
            name: self.programs.get_help(name) or ""
            for name in self.programs.list_programs()
        }
        env["_program_help"] = json.dumps(program_help)

        return ProgramContext(
            args=args,
            stdout=self.output,
            stderr=self.output,
            env=env,
            services=self.session.container,
            cwd_id=self.session.cwd_id,
        )

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
