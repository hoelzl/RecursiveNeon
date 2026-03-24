"""
Chat program — interactive NPC conversation.

Enters a sub-REPL where the player can talk to an NPC.
Uses NPCManager from the service container.
"""

from __future__ import annotations

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
            ctx.stdout.styled("Type 'exit' or Ctrl+D to disconnect.", DIM)
        )
        ctx.stdout.writeln()

        player_id = ctx.env.get("USER", "player_1")

        # Sub-REPL for chat
        while True:
            try:
                # Use prompt_toolkit for async input if available,
                # fall back to simple input()
                prompt = f"{ctx.stdout.styled(npc_id, YELLOW)}> "
                try:
                    from prompt_toolkit import PromptSession

                    ps: PromptSession[str] = PromptSession()
                    user_input = await ps.prompt_async(prompt)
                except ImportError:
                    user_input = input(f"{npc_id}> ")
            except (EOFError, KeyboardInterrupt):
                ctx.stdout.writeln()
                break

            user_input = user_input.strip()
            if not user_input:
                continue
            if user_input.lower() == "exit":
                break

            # Slash commands within chat
            if user_input.startswith("/"):
                cmd = user_input[1:].lower().strip()
                if cmd == "help":
                    ctx.stdout.writeln(ctx.stdout.styled("Chat commands:", BOLD))
                    ctx.stdout.writeln("  /help          Show this help")
                    ctx.stdout.writeln("  /relationship  Show relationship level")
                    ctx.stdout.writeln("  /status        Show NPC info")
                    ctx.stdout.writeln("  exit           Leave conversation")
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
                response = await npc_manager.chat(npc_id, user_input, player_id)
                ctx.stdout.writeln()
                ctx.stdout.writeln(
                    f"[{ctx.stdout.styled(npc.name, YELLOW)}]: {response.message}"
                )
                ctx.stdout.writeln()
            except Exception as e:
                ctx.stderr.error(f"chat: error: {e}")

        ctx.stdout.writeln("Connection closed.")
        return 0


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
        "conversation. Type 'exit' or Ctrl+D to disconnect.",
    )
