"""
Tests for desktop app data models
"""
import pytest
from datetime import datetime
from backend.models.app_models import (
    Note,
    NotesState,
    Task,
    TaskList,
    TasksState,
    FileNode,
    FileSystemState,
    BrowserPage,
    BrowserState,
)


class TestNote:
    """Tests for Note model"""

    def test_create_note(self):
        """Test creating a new note"""
        note = Note(
            id="note-1",
            title="Test Note",
            content="This is a test note",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert note.id == "note-1"
        assert note.title == "Test Note"
        assert note.content == "This is a test note"

    def test_note_serialization(self):
        """Test note can be serialized to dict"""
        note = Note(
            id="note-1",
            title="Test",
            content="Content",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        data = note.model_dump()
        assert data["id"] == "note-1"
        assert data["title"] == "Test"


class TestNotesState:
    """Tests for NotesState model"""

    def test_empty_notes_state(self):
        """Test creating empty notes state"""
        state = NotesState()
        assert state.notes == []

    def test_notes_state_with_notes(self):
        """Test notes state with multiple notes"""
        notes = [
            Note(
                id="1",
                title="Note 1",
                content="Content 1",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
            Note(
                id="2",
                title="Note 2",
                content="Content 2",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
        ]
        state = NotesState(notes=notes)
        assert len(state.notes) == 2
        assert state.notes[0].title == "Note 1"


class TestTask:
    """Tests for Task model"""

    def test_create_task(self):
        """Test creating a new task"""
        task = Task(
            id="task-1",
            title="Test Task",
            completed=False,
            parent_id=None,
        )
        assert task.id == "task-1"
        assert task.title == "Test Task"
        assert task.completed is False
        assert task.parent_id is None

    def test_task_with_subtasks(self):
        """Test task with parent-child relationship"""
        parent = Task(id="parent", title="Parent", completed=False)
        child = Task(id="child", title="Child", completed=False, parent_id="parent")
        assert child.parent_id == "parent"


class TestTaskList:
    """Tests for TaskList model"""

    def test_create_task_list(self):
        """Test creating a task list"""
        task_list = TaskList(
            id="list-1",
            name="My Tasks",
            tasks=[],
        )
        assert task_list.id == "list-1"
        assert task_list.name == "My Tasks"
        assert task_list.tasks == []

    def test_task_list_with_tasks(self):
        """Test task list with tasks"""
        tasks = [
            Task(id="1", title="Task 1", completed=False),
            Task(id="2", title="Task 2", completed=True),
        ]
        task_list = TaskList(id="list-1", name="Work", tasks=tasks)
        assert len(task_list.tasks) == 2
        assert task_list.tasks[1].completed is True


class TestTasksState:
    """Tests for TasksState model"""

    def test_empty_tasks_state(self):
        """Test creating empty tasks state"""
        state = TasksState()
        assert state.lists == []

    def test_tasks_state_with_lists(self):
        """Test tasks state with multiple lists"""
        lists = [
            TaskList(id="1", name="Personal", tasks=[]),
            TaskList(id="2", name="Work", tasks=[]),
        ]
        state = TasksState(lists=lists)
        assert len(state.lists) == 2


class TestFileNode:
    """Tests for FileNode model"""

    def test_create_directory(self):
        """Test creating a directory node"""
        node = FileNode(
            id="dir-1",
            name="Documents",
            type="directory",
            parent_id=None,
        )
        assert node.type == "directory"
        assert node.name == "Documents"
        assert node.content is None

    def test_create_file(self):
        """Test creating a file node"""
        node = FileNode(
            id="file-1",
            name="readme.txt",
            type="file",
            parent_id="dir-1",
            content="Hello, World!",
            mime_type="text/plain",
        )
        assert node.type == "file"
        assert node.content == "Hello, World!"
        assert node.mime_type == "text/plain"

    def test_create_image_file(self):
        """Test creating an image file node"""
        node = FileNode(
            id="img-1",
            name="photo.jpg",
            type="file",
            parent_id="dir-1",
            content="base64encodeddata...",
            mime_type="image/jpeg",
        )
        assert node.mime_type == "image/jpeg"


class TestFileSystemState:
    """Tests for FileSystemState model"""

    def test_empty_filesystem(self):
        """Test creating empty filesystem"""
        fs = FileSystemState()
        assert fs.nodes == []
        assert fs.root_id is None

    def test_filesystem_with_nodes(self):
        """Test filesystem with multiple nodes"""
        nodes = [
            FileNode(id="root", name="/", type="directory", parent_id=None),
            FileNode(id="file1", name="test.txt", type="file", parent_id="root"),
        ]
        fs = FileSystemState(nodes=nodes, root_id="root")
        assert len(fs.nodes) == 2
        assert fs.root_id == "root"


class TestBrowserPage:
    """Tests for BrowserPage model"""

    def test_create_browser_page(self):
        """Test creating a browser page"""
        page = BrowserPage(
            id="page-1",
            url="example.html",
            title="Example Page",
            content="<h1>Hello</h1>",
        )
        assert page.url == "example.html"
        assert page.title == "Example Page"
        assert page.content == "<h1>Hello</h1>"


class TestBrowserState:
    """Tests for BrowserState model"""

    def test_empty_browser_state(self):
        """Test creating empty browser state"""
        state = BrowserState()
        assert state.pages == []
        assert state.bookmarks == []

    def test_browser_state_with_pages(self):
        """Test browser state with pages and bookmarks"""
        pages = [
            BrowserPage(id="1", url="page1.html", title="Page 1", content="<p>1</p>"),
            BrowserPage(id="2", url="page2.html", title="Page 2", content="<p>2</p>"),
        ]
        bookmarks = ["page1.html", "page2.html"]
        state = BrowserState(pages=pages, bookmarks=bookmarks)
        assert len(state.pages) == 2
        assert len(state.bookmarks) == 2
