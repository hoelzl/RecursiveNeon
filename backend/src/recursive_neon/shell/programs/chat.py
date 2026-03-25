"""
Chat program — interactive NPC conversation.

Enters a sub-REPL where the player can talk to an NPC.
Uses NPCManager from the service container.
"""

from __future__ import annotations

import asyncio

from recursive_neon.models.npc import NPC
from recursive_neon.shell.output import BOLD, CYAN, DIM, YELLOW
from recursive_neon.shell.programs import ProgramContext, ProgramRegistry


class ChatProgram:
    """Interactive NPC chat program."""

    async def run(self, ctx: ProgramContext) -> int:
        npc_manager = ctx.services.npc_manager

        if len(ctx.args) < 2:
            # No NPC specified — list available NPCs
            npcs = npc_manager.list_npcs()
            if not npcs:
                ctx.stdout.writeln("No NPCs available.")
                return 0

            ctx.stdout.writeln(ctx.stdout.styled("Available NPCs:", BOLD))
            for entry in npcs:
                name = ctx.stdout.styled(entry.name, YELLOW)
                role = ctx.stdout.styled(f"({entry.role.value})", DIM)
                ctx.stdout.writeln(f"  {entry.id:16s} {name} {role}")
                if entry.greeting:
                    greeting_preview = entry.greeting[:60]
                    if len(entry.greeting) > 60:
                        greeting_preview += "..."
                    ctx.stdout.writeln(
                        f"  {'':16s} {ctx.stdout.styled(greeting_preview, DIM)}"
                    )
            ctx.stdout.writeln()
            ctx.stdout.writeln(f"Usage: {ctx.stdout.styled('chat <npc_id>', CYAN)}")
            return 0

        npc_id = ctx.args[1]
        npc: NPC | None = npc_manager.get_npc(npc_id)
        if npc is None:
            ctx.stderr.error(f"chat: unknown NPC: {npc_id}")
            return 1

        # Enter conversation
        ctx.stdout.writeln(f"Connecting to {ctx.stdout.styled(npc.name, YELLOW)}...")
        if npc.greeting:
            ctx.stdout.writeln()
            ctx.stdout.writeln(
                f"[{ctx.stdout.styled(npc.name, YELLOW)}]: {npc.greeting}"
            )
        ctx.stdout.writeln()
        ctx.stdout.writeln(
            ctx.stdout.styled("Type /exit or Ctrl+D to disconnect.", DIM)
        )
        ctx.stdout.writeln()

        player_id = ctx.env.get("USER", "player_1")

        # Create a prompt_toolkit session as fallback for local terminal
        # (when ctx.get_line is not available, e.g. in tests or direct use).
        if ctx.get_line is None:
            try:
                from prompt_toolkit import PromptSession
                from prompt_toolkit.formatted_text import ANSI

                _chat_session: PromptSession[str] = PromptSession()
            except ImportError:
                _chat_session = None  # type: ignore[assignment]

        # Sub-REPL for chat
        while True:
            try:
                prompt = f"{ctx.stdout.styled(npc_id, YELLOW)}> "
                if ctx.get_line is not None:
                    user_input = await ctx.get_line(prompt)
                elif _chat_session is not None:
                    user_input = await _chat_session.prompt_async(ANSI(prompt))
                else:
                    user_input = input(f"{npc_id}> ")
            except (EOFError, KeyboardInterrupt):
                ctx.stdout.writeln()
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            # Slash commands within chat
            if user_input.startswith("/"):
                cmd = user_input[1:].lower().strip()
                if cmd == "exit":
                    break
                elif cmd == "help":
                    ctx.stdout.writeln(ctx.stdout.styled("Chat commands:", BOLD))
                    ctx.stdout.writeln("  /help          Show this help")
                    ctx.stdout.writeln("  /relationship  Show relationship level")
                    ctx.stdout.writeln("  /status        Show NPC info")
                    ctx.stdout.writeln("  /exit          Leave conversation")
                elif cmd == "relationship":
                    level = npc.memory.relationship_level
                    ctx.stdout.writeln(
                        f"Relationship with {ctx.stdout.styled(npc.name, YELLOW)}: {level}"
                    )
                elif cmd == "status":
                    ctx.stdout.writeln(
                        f"{ctx.stdout.styled(npc.name, YELLOW)} "
                        f"({npc.role.value}, {npc.personality.value})"
                    )
                    ctx.stdout.writeln(f"  Location: {npc.location}")
                    ctx.stdout.writeln(
                        f"  Messages: {len(npc.memory.conversation_history)}"
                    )
                else:
                    ctx.stderr.error(f"Unknown command: /{cmd}. Try /help")
                ctx.stdout.writeln()
                continue

            try:
                typing_msg = ctx.stdout.styled(f"{npc.name} is typing...", DIM)
                ctx.stdout.write(f"\r{typing_msg}")
                spinner = asyncio.create_task(_typing_spinner(ctx, npc.name))
                try:
                    response = await npc_manager.chat(npc_id, user_input, player_id)
                finally:
                    spinner.cancel()
                    # Clear the typing indicator line
                    ctx.stdout.write("\r\033[2K")

                ctx.stdout.writeln(
                    f"[{ctx.stdout.styled(npc.name, YELLOW)}]: {response.message}"
                )
                ctx.stdout.writeln()
            except Exception as e:
                ctx.stderr.error(f"chat: error: {e}")

        ctx.stdout.writeln("Connection closed.")
        return 0


_SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


async def _typing_spinner(ctx: ProgramContext, name: str) -> None:
    """Animate a spinner while the NPC is generating a response."""
    try:
        i = 0
        while True:
            frame = _SPINNER_FRAMES[i % len(_SPINNER_FRAMES)]
            text = ctx.stdout.styled(f"{frame} {name} is typing...", DIM)
            ctx.stdout.write(f"\r{text}")
            i += 1
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass


def register_chat_program(registry: ProgramRegistry) -> None:
    """Register the chat program."""
    registry.register(
        "chat",
        ChatProgram(),
        "Chat with an NPC\n"
        "\n"
        "Usage: chat [NPC_ID]\n"
        "\n"
        "With no argument, list available NPCs. With NPC_ID, start a\n"
        "conversation. Type /exit or Ctrl+D to disconnect.",
    )
