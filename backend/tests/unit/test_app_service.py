"""
Tests for desktop app service
"""
import pytest
from datetime import datetime
from backend.services.app_service import AppService
from backend.models.game_state import GameState
from backend.models.app_models import Note, Task, TaskList, FileNode, BrowserPage


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
        note_data = {
            "title": "Test Note",
            "content": "This is a test"
        }
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
        updated = app_service.update_note(note.id, {"title": "Updated", "content": "New"})
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
        parent_task = app_service.create_task(task_list.id, {"title": "Project", "completed": False})
        subtask = app_service.create_task(
            task_list.id,
            {"title": "Step 1", "completed": False, "parent_id": parent_task.id}
        )
        assert subtask.parent_id == parent_task.id

    def test_update_task(self, app_service):
        """Test updating a task"""
        task_list = app_service.create_task_list({"name": "Work"})
        task = app_service.create_task(task_list.id, {"title": "Task", "completed": False})
        updated = app_service.update_task(task_list.id, task.id, {"completed": True})
        assert updated.completed is True

    def test_delete_task_list(self, app_service):
        """Test deleting a task list"""
        task_list = app_service.create_task_list({"name": "Delete Me"})
        app_service.delete_task_list(task_list.id)
        with pytest.raises(ValueError):
            app_service.get_task_list(task_list.id)


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
            "mime_type": "text/plain"
        }
        file = app_service.create_file(file_data)
        assert file.name == "readme.txt"
        assert file.content == "Hello, World!"

    def test_get_file_by_id(self, app_service):
        """Test getting a file by ID"""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        file = app_service.create_file({
            "name": "test.txt",
            "parent_id": root_id,
            "content": "test",
            "mime_type": "text/plain"
        })
        retrieved = app_service.get_file(file.id)
        assert retrieved.id == file.id

    def test_update_file(self, app_service):
        """Test updating file content"""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        file = app_service.create_file({
            "name": "test.txt",
            "parent_id": root_id,
            "content": "old",
            "mime_type": "text/plain"
        })
        updated = app_service.update_file(file.id, {"content": "new"})
        assert updated.content == "new"

    def test_delete_file(self, app_service):
        """Test deleting a file"""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        file = app_service.create_file({
            "name": "delete.txt",
            "parent_id": root_id,
            "content": "delete me",
            "mime_type": "text/plain"
        })
        app_service.delete_file(file.id)
        with pytest.raises(ValueError):
            app_service.get_file(file.id)

    def test_list_directory_contents(self, app_service):
        """Test listing directory contents"""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        app_service.create_file({
            "name": "file1.txt",
            "parent_id": root_id,
            "content": "1",
            "mime_type": "text/plain"
        })
        app_service.create_directory({"name": "dir1", "parent_id": root_id})
        contents = app_service.list_directory(root_id)
        assert len(contents) == 2


class TestBrowserService:
    """Tests for browser service"""

    @pytest.fixture
    def app_service(self):
        """Create app service with fresh game state"""
        game_state = GameState()
        return AppService(game_state)

    def test_get_all_pages_empty(self, app_service):
        """Test getting all pages when empty"""
        pages = app_service.get_browser_pages()
        assert pages == []

    def test_create_browser_page(self, app_service):
        """Test creating a browser page"""
        page_data = {
            "url": "welcome.html",
            "title": "Welcome",
            "content": "<h1>Welcome</h1>"
        }
        page = app_service.create_browser_page(page_data)
        assert page.url == "welcome.html"
        assert page.title == "Welcome"

    def test_get_page_by_url(self, app_service):
        """Test getting a page by URL"""
        page = app_service.create_browser_page({
            "url": "test.html",
            "title": "Test",
            "content": "<p>Test</p>"
        })
        retrieved = app_service.get_browser_page_by_url("test.html")
        assert retrieved.url == "test.html"

    def test_add_bookmark(self, app_service):
        """Test adding a bookmark"""
        app_service.add_bookmark("favorite.html")
        bookmarks = app_service.get_bookmarks()
        assert "favorite.html" in bookmarks

    def test_remove_bookmark(self, app_service):
        """Test removing a bookmark"""
        app_service.add_bookmark("temp.html")
        app_service.remove_bookmark("temp.html")
        bookmarks = app_service.get_bookmarks()
        assert "temp.html" not in bookmarks
