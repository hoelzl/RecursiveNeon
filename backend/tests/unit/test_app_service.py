"""
Tests for desktop app service
"""

import pytest

from recursive_neon.models.game_state import GameState
from recursive_neon.services.app_service import AppService


class TestNotesService:
    """Tests for notes service"""

    @pytest.fixture
    def app_service(self):
        """Create app service with fresh game state"""
        game_state = GameState()
        return AppService(game_state)

    def test_get_all_notes_empty(self, app_service):
        """Test getting all notes when empty"""
        notes = app_service.get_notes()
        assert notes == []

    def test_create_note(self, app_service):
        """Test creating a new note"""
        note_data = {"title": "Test Note", "content": "This is a test"}
        note = app_service.create_note(note_data)
        assert note.title == "Test Note"
        assert note.content == "This is a test"
        assert note.id is not None

    def test_get_note_by_id(self, app_service):
        """Test getting a specific note"""
        note = app_service.create_note({"title": "Test", "content": "Content"})
        retrieved = app_service.get_note(note.id)
        assert retrieved.id == note.id
        assert retrieved.title == "Test"

    def test_update_note(self, app_service):
        """Test updating a note"""
        note = app_service.create_note({"title": "Original", "content": "Old"})
        updated = app_service.update_note(
            note.id, {"title": "Updated", "content": "New"}
        )
        assert updated.title == "Updated"
        assert updated.content == "New"

    def test_delete_note(self, app_service):
        """Test deleting a note"""
        note = app_service.create_note({"title": "Delete Me", "content": "..."})
        app_service.delete_note(note.id)
        with pytest.raises(ValueError):
            app_service.get_note(note.id)


class TestTasksService:
    """Tests for tasks service"""

    @pytest.fixture
    def app_service(self):
        """Create app service with fresh game state"""
        game_state = GameState()
        return AppService(game_state)

    def test_get_all_task_lists_empty(self, app_service):
        """Test getting all task lists when empty"""
        lists = app_service.get_task_lists()
        assert lists == []

    def test_create_task_list(self, app_service):
        """Test creating a new task list"""
        list_data = {"name": "Personal"}
        task_list = app_service.create_task_list(list_data)
        assert task_list.name == "Personal"
        assert task_list.id is not None
        assert task_list.tasks == []

    def test_create_task(self, app_service):
        """Test creating a task in a list"""
        task_list = app_service.create_task_list({"name": "Work"})
        task_data = {"title": "Finish report", "completed": False}
        task = app_service.create_task(task_list.id, task_data)
        assert task.title == "Finish report"
        assert task.completed is False

    def test_create_subtask(self, app_service):
        """Test creating a subtask"""
        task_list = app_service.create_task_list({"name": "Work"})
        parent_task = app_service.create_task(
            task_list.id, {"title": "Project", "completed": False}
        )
        subtask = app_service.create_task(
            task_list.id,
            {"title": "Step 1", "completed": False, "parent_id": parent_task.id},
        )
        assert subtask.parent_id == parent_task.id

    def test_update_task(self, app_service):
        """Test updating a task"""
        task_list = app_service.create_task_list({"name": "Work"})
        task = app_service.create_task(
            task_list.id, {"title": "Task", "completed": False}
        )
        updated = app_service.update_task(task_list.id, task.id, {"completed": True})
        assert updated.completed is True

    def test_delete_task_list(self, app_service):
        """Test deleting a task list"""
        task_list = app_service.create_task_list({"name": "Delete Me"})
        app_service.delete_task_list(task_list.id)
        with pytest.raises(ValueError):
            app_service.get_task_list(task_list.id)


class TestNotesPersistence:
    """Tests for notes save/load persistence."""

    @pytest.fixture
    def app_service(self):
        game_state = GameState()
        return AppService(game_state)

    def test_save_and_load_notes(self, app_service, tmp_path):
        """Notes survive a save/load round-trip."""
        app_service.create_note({"title": "Note A", "content": "Content A"})
        app_service.create_note({"title": "Note B", "content": "Content B"})
        app_service.save_notes_to_disk(str(tmp_path))

        # Load into fresh state
        fresh = AppService(GameState())
        assert fresh.get_notes() == []
        assert fresh.load_notes_from_disk(str(tmp_path)) is True
        notes = fresh.get_notes()
        assert len(notes) == 2
        assert notes[0].title == "Note A"
        assert notes[1].content == "Content B"

    def test_load_notes_missing_file(self, app_service, tmp_path):
        """Returns False when no saved file exists."""
        assert app_service.load_notes_from_disk(str(tmp_path)) is False

    def test_save_empty_notes(self, app_service, tmp_path):
        """Saving empty notes still creates valid file."""
        app_service.save_notes_to_disk(str(tmp_path))
        fresh = AppService(GameState())
        assert fresh.load_notes_from_disk(str(tmp_path)) is True
        assert fresh.get_notes() == []

    def test_load_corrupt_notes_json(self, app_service, tmp_path):
        """Corrupt JSON returns False without crashing."""
        (tmp_path / "notes.json").write_text("{invalid json", encoding="utf-8")
        assert app_service.load_notes_from_disk(str(tmp_path)) is False


class TestTasksPersistence:
    """Tests for tasks save/load persistence."""

    @pytest.fixture
    def app_service(self):
        game_state = GameState()
        return AppService(game_state)

    def test_save_and_load_tasks(self, app_service, tmp_path):
        """Task lists and tasks survive a save/load round-trip."""
        tl = app_service.create_task_list({"name": "Work"})
        app_service.create_task(tl.id, {"title": "Task 1", "completed": False})
        app_service.create_task(tl.id, {"title": "Task 2", "completed": True})
        app_service.save_tasks_to_disk(str(tmp_path))

        fresh = AppService(GameState())
        assert fresh.load_tasks_from_disk(str(tmp_path)) is True
        lists = fresh.get_task_lists()
        assert len(lists) == 1
        assert lists[0].name == "Work"
        assert len(lists[0].tasks) == 2
        assert lists[0].tasks[0].title == "Task 1"
        assert lists[0].tasks[1].completed is True

    def test_load_tasks_missing_file(self, app_service, tmp_path):
        """Returns False when no saved file exists."""
        assert app_service.load_tasks_from_disk(str(tmp_path)) is False

    def test_load_corrupt_tasks_json(self, app_service, tmp_path):
        """Corrupt JSON returns False without crashing."""
        (tmp_path / "tasks.json").write_text("not json!", encoding="utf-8")
        assert app_service.load_tasks_from_disk(str(tmp_path)) is False

    def test_save_all_and_load_all(self, app_service, tmp_path):
        """save_all/load_all round-trips filesystem, notes, and tasks."""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        app_service.create_file(
            {"name": "test.txt", "parent_id": root_id, "content": "hello"}
        )
        app_service.create_note({"title": "My Note", "content": "body"})
        app_service.create_task_list({"name": "Todo"})

        app_service.save_all_to_disk(str(tmp_path))

        fresh = AppService(GameState())
        assert fresh.load_all_from_disk(str(tmp_path)) is True
        assert len(fresh.get_notes()) == 1
        assert len(fresh.get_task_lists()) == 1
        assert fresh.game_state.filesystem.root_id is not None


class TestFileSystemService:
    """Tests for filesystem service"""

    @pytest.fixture
    def app_service(self):
        """Create app service with fresh game state"""
        game_state = GameState()
        return AppService(game_state)

    def test_initialize_filesystem(self, app_service):
        """Test initializing filesystem with root"""
        app_service.init_filesystem()
        assert app_service.game_state.filesystem.root_id is not None

    def test_create_directory(self, app_service):
        """Test creating a directory"""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        dir_data = {"name": "Documents", "parent_id": root_id}
        directory = app_service.create_directory(dir_data)
        assert directory.name == "Documents"
        assert directory.type == "directory"

    def test_create_file(self, app_service):
        """Test creating a file"""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        file_data = {
            "name": "readme.txt",
            "parent_id": root_id,
            "content": "Hello, World!",
            "mime_type": "text/plain",
        }
        file = app_service.create_file(file_data)
        assert file.name == "readme.txt"
        assert file.content == "Hello, World!"

    def test_get_file_by_id(self, app_service):
        """Test getting a file by ID"""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        file = app_service.create_file(
            {
                "name": "test.txt",
                "parent_id": root_id,
                "content": "test",
                "mime_type": "text/plain",
            }
        )
        retrieved = app_service.get_file(file.id)
        assert retrieved.id == file.id

    def test_update_file(self, app_service):
        """Test updating file content"""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        file = app_service.create_file(
            {
                "name": "test.txt",
                "parent_id": root_id,
                "content": "old",
                "mime_type": "text/plain",
            }
        )
        updated = app_service.update_file(file.id, {"content": "new"})
        assert updated.content == "new"

    def test_delete_file(self, app_service):
        """Test deleting a file"""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        file = app_service.create_file(
            {
                "name": "delete.txt",
                "parent_id": root_id,
                "content": "delete me",
                "mime_type": "text/plain",
            }
        )
        app_service.delete_file(file.id)
        with pytest.raises(ValueError):
            app_service.get_file(file.id)

    def test_list_directory_contents(self, app_service):
        """Test listing directory contents"""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        app_service.create_file(
            {
                "name": "file1.txt",
                "parent_id": root_id,
                "content": "1",
                "mime_type": "text/plain",
            }
        )
        app_service.create_directory({"name": "dir1", "parent_id": root_id})
        contents = app_service.list_directory(root_id)
        assert len(contents) == 2
