"""Integration tests — full command flows through Shell.execute_line()."""

from __future__ import annotations

import pytest

from recursive_neon.dependencies import ServiceFactory
from recursive_neon.shell.output import CapturedOutput
from recursive_neon.shell.shell import Shell


@pytest.mark.integration
class TestNoteWorkflow:
    """End-to-end note management workflow."""

    async def test_create_list_show_edit_delete(self, shell):
        s = shell
        o = s.output

        # Create a note
        assert (
            await s.execute_line('note create "My First Note" -c "Initial content"')
            == 0
        )
        assert "My First Note" in o.text
        o.reset()

        # List notes
        assert await s.execute_line("note list") == 0
        assert "[1]" in o.text
        assert "My First Note" in o.text
        o.reset()

        # Show note
        assert await s.execute_line("note show 1") == 0
        assert "Initial content" in o.text
        o.reset()

        # Edit note
        assert await s.execute_line('note edit 1 -c "Updated content"') == 0
        o.reset()

        # Verify edit
        assert await s.execute_line("note show 1") == 0
        assert "Updated content" in o.text
        o.reset()

        # Delete note
        assert await s.execute_line("note delete 1") == 0
        o.reset()

        # Verify deletion
        assert await s.execute_line("note list") == 0
        assert "No notes" in o.text


@pytest.mark.integration
class TestTaskWorkflow:
    """End-to-end task management workflow."""

    async def test_add_list_done_undone_delete(self, shell):
        s = shell
        o = s.output

        # Add tasks (auto-creates default list)
        assert await s.execute_line("task add Buy groceries") == 0
        assert "Buy groceries" in o.text
        o.reset()

        assert await s.execute_line("task add Clean house") == 0
        o.reset()

        # List tasks
        assert await s.execute_line("task list") == 0
        assert "Buy groceries" in o.text
        assert "Clean house" in o.text
        o.reset()

        # Mark task done
        assert await s.execute_line("task done 1") == 0
        assert "[x]" in o.text
        o.reset()

        # Mark task undone
        assert await s.execute_line("task undone 1") == 0
        assert "[ ]" in o.text
        o.reset()

        # Delete task
        assert await s.execute_line("task delete 2") == 0
        assert "Clean house" in o.text
        o.reset()

        # Verify one task remains
        assert await s.execute_line("task list") == 0
        assert "Buy groceries" in o.text
        assert "Clean house" not in o.text


@pytest.mark.integration
class TestFilesystemWorkflow:
    """End-to-end filesystem workflow with new commands."""

    async def test_mkdir_write_grep_find_cat(self, shell):
        s = shell
        o = s.output

        # Create directory and file
        assert await s.execute_line("mkdir /project") == 0
        assert await s.execute_line("write /project/readme.md # My Project") == 0
        o.reset()

        # Cat the file
        assert await s.execute_line("cat /project/readme.md") == 0
        assert "# My Project" in o.text
        o.reset()

        # Find the file
        assert await s.execute_line("find / -name readme.md") == 0
        assert "/project/readme.md" in o.text
        o.reset()

        # Grep for content
        assert await s.execute_line("grep Project /project/readme.md") == 0
        assert "Project" in o.text
        o.reset()

        # Write new content (overwrite)
        assert (
            await s.execute_line("write /project/readme.md Updated content here") == 0
        )
        o.reset()

        # Verify overwrite
        assert await s.execute_line("cat /project/readme.md") == 0
        assert "Updated content here" in o.text
        assert "# My Project" not in o.text

    async def test_grep_across_directories(self, shell):
        s = shell
        o = s.output

        # Grep recursively from root for known content in initial filesystem
        assert await s.execute_line("grep Welcome /") == 0
        assert "welcome.txt" in o.text

    async def test_find_glob_pattern(self, shell):
        s = shell
        o = s.output

        assert await s.execute_line("find / -name '*.txt'") == 0
        text = o.text
        assert "welcome.txt" in text
        # Should find multiple txt files
        assert text.count(".txt") > 1


@pytest.mark.integration
class TestPersistenceRoundTrip:
    """Test that save/load preserves state across shell instances."""

    async def test_save_and_reload(self, shell_with_data_dir, mock_llm):
        s, data_dir = shell_with_data_dir
        o = s.output

        # Create some data
        assert (
            await s.execute_line('note create "Persisted Note" -c "Saved content"') == 0
        )
        assert await s.execute_line("task add Persisted Task") == 0
        assert await s.execute_line("mkdir /saved_dir") == 0
        o.reset()

        # Save explicitly
        assert await s.execute_line("save") == 0
        assert "Game state saved" in o.text

        # Create a fresh shell loading from the same data_dir
        container2 = ServiceFactory.create_test_container(
            mock_npc_manager=ServiceFactory.create_npc_manager(llm=mock_llm),
        )
        # Load state from disk instead of initial filesystem
        container2.app_service.load_all_from_disk(data_dir)
        container2.npc_manager.load_npcs_from_disk(data_dir)

        output2 = CapturedOutput()
        s2 = Shell(container=container2, output=output2, data_dir=data_dir)

        # Verify notes survived
        assert await s2.execute_line("note list") == 0
        assert "Persisted Note" in output2.text
        output2.reset()

        # Verify tasks survived
        assert await s2.execute_line("task list") == 0
        assert "Persisted Task" in output2.text
        output2.reset()

        # Verify filesystem survived
        assert await s2.execute_line("ls /") == 0
        assert "saved_dir" in output2.text


@pytest.mark.integration
class TestChatWorkflow:
    """Test chat program through the shell."""

    async def test_list_npcs(self, shell):
        s = shell
        o = s.output

        assert await s.execute_line("chat") == 0
        text = o.text
        # Default NPCs should be listed
        assert "Aria" in text
        assert "Zero" in text

    async def test_chat_unknown_npc(self, shell):
        s = shell
        o = s.output

        assert await s.execute_line("chat nonexistent_npc") == 1
        assert "unknown NPC" in o.error_text
