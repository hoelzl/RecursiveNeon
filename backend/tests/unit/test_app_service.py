"""
Tests for desktop app service
"""

import pytest
from pydantic import ValidationError

from recursive_neon.models.app_models import FileNode
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

    def test_get_file_not_found(self, app_service):
        """Getting a non-existent file raises ValueError."""
        with pytest.raises(ValueError, match="File not found"):
            app_service.get_file("nonexistent-uuid")

    def test_move_file_into_self_raises(self, app_service):
        """Moving a directory into itself raises ValueError."""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        dir_a = app_service.create_directory({"name": "A", "parent_id": root_id})
        with pytest.raises(ValueError, match="Cannot move"):
            app_service.move_file(dir_a.id, dir_a.id)

    def test_move_file_into_descendant_raises(self, app_service):
        """Moving a directory into its own descendant raises ValueError."""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        dir_a = app_service.create_directory({"name": "A", "parent_id": root_id})
        dir_b = app_service.create_directory({"name": "B", "parent_id": dir_a.id})
        with pytest.raises(ValueError, match="Cannot move"):
            app_service.move_file(dir_a.id, dir_b.id)

    def test_move_file_updates_parent(self, app_service):
        """Moving a file changes its parent_id."""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        dir_a = app_service.create_directory({"name": "A", "parent_id": root_id})
        dir_b = app_service.create_directory({"name": "B", "parent_id": root_id})
        f = app_service.create_file(
            {"name": "x.txt", "parent_id": dir_a.id, "content": "x"}
        )
        moved = app_service.move_file(f.id, dir_b.id)
        assert moved.parent_id == dir_b.id
        # Should appear in dir_b listing, not dir_a
        assert any(n.id == f.id for n in app_service.list_directory(dir_b.id))
        assert all(n.id != f.id for n in app_service.list_directory(dir_a.id))

    def test_copy_file_deep(self, app_service):
        """Copying a directory recursively copies children."""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        src = app_service.create_directory({"name": "src", "parent_id": root_id})
        app_service.create_file(
            {"name": "a.txt", "parent_id": src.id, "content": "hello"}
        )
        copy = app_service.copy_file(src.id, root_id, "src_copy")
        assert copy.name == "src_copy"
        children = app_service.list_directory(copy.id)
        assert len(children) == 1
        assert children[0].name == "a.txt"
        assert children[0].id != src.id  # new UUID

    def test_delete_directory_recursive(self, app_service):
        """Deleting a directory removes all descendants."""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        parent = app_service.create_directory({"name": "parent", "parent_id": root_id})
        child = app_service.create_file(
            {"name": "c.txt", "parent_id": parent.id, "content": "c"}
        )
        app_service.delete_file(parent.id)
        with pytest.raises(ValueError):
            app_service.get_file(child.id)
        with pytest.raises(ValueError):
            app_service.get_file(parent.id)

    def test_delete_deep_tree_removes_all_descendants(self, app_service):
        """Deleting a deep directory tree removes everything in one pass."""
        app_service.init_filesystem()
        root_id = app_service.game_state.filesystem.root_id
        # Build: /a/b/c/d.txt
        a = app_service.create_directory({"name": "a", "parent_id": root_id})
        b = app_service.create_directory({"name": "b", "parent_id": a.id})
        c = app_service.create_directory({"name": "c", "parent_id": b.id})
        d = app_service.create_file(
            {"name": "d.txt", "parent_id": c.id, "content": "x"}
        )
        initial_count = len(app_service.game_state.filesystem.nodes)
        app_service.delete_file(a.id)
        # Should have removed a, b, c, d (4 nodes)
        assert len(app_service.game_state.filesystem.nodes) == initial_count - 4
        for nid in [a.id, b.id, c.id, d.id]:
            assert nid not in app_service._node_index


class TestFileNodeTypeValidation:
    """FileNode.type must be 'file' or 'directory'."""

    def test_valid_file_type(self):
        FileNode(id="1", name="f", type="file")

    def test_valid_directory_type(self):
        FileNode(id="1", name="d", type="directory")

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            FileNode(id="1", name="bad", type="fle")

    def test_invalid_type_case_sensitive(self):
        with pytest.raises(ValidationError):
            FileNode(id="1", name="bad", type="Directory")


class TestFilesystemIndexConsistency:
    """Verify that O(1) lookup indexes stay consistent with the nodes list."""

    @pytest.fixture
    def svc(self):
        svc = AppService(GameState())
        svc.init_filesystem()
        return svc

    def test_index_after_create(self, svc):
        root_id = svc.game_state.filesystem.root_id
        f = svc.create_file({"name": "x.txt", "parent_id": root_id, "content": ""})
        assert svc._node_index[f.id] is f
        assert f.id in svc._children_index[root_id]

    def test_index_after_delete(self, svc):
        root_id = svc.game_state.filesystem.root_id
        f = svc.create_file({"name": "x.txt", "parent_id": root_id, "content": ""})
        svc.delete_file(f.id)
        assert f.id not in svc._node_index
        assert f.id not in svc._children_index.get(root_id, [])

    def test_index_after_move(self, svc):
        root_id = svc.game_state.filesystem.root_id
        a = svc.create_directory({"name": "a", "parent_id": root_id})
        b = svc.create_directory({"name": "b", "parent_id": root_id})
        f = svc.create_file({"name": "x.txt", "parent_id": a.id, "content": ""})
        svc.move_file(f.id, b.id)
        assert f.id not in svc._children_index.get(a.id, [])
        assert f.id in svc._children_index[b.id]
        assert svc._node_index[f.id].parent_id == b.id

    def test_index_after_update(self, svc):
        root_id = svc.game_state.filesystem.root_id
        f = svc.create_file({"name": "x.txt", "parent_id": root_id, "content": "old"})
        updated = svc.update_file(f.id, {"content": "new"})
        assert svc._node_index[f.id] is updated
        assert updated.content == "new"

    def test_index_after_load_from_disk(self, svc, tmp_path):
        root_id = svc.game_state.filesystem.root_id
        svc.create_file({"name": "x.txt", "parent_id": root_id, "content": "data"})
        svc.save_filesystem_to_disk(str(tmp_path))

        fresh = AppService(GameState())
        fresh.load_filesystem_from_disk(str(tmp_path))
        # Index should be populated after load
        assert len(fresh._node_index) == len(fresh.game_state.filesystem.nodes)
        for node in fresh.game_state.filesystem.nodes:
            assert fresh._node_index[node.id] is node


class TestParentIdValidation:
    """Tests for parent_id validation in create_file/create_directory (fix #7)."""

    @pytest.fixture
    def svc(self):
        svc = AppService(GameState())
        svc.init_filesystem()
        return svc

    def test_create_file_invalid_parent_id(self, svc):
        """Creating a file with a non-existent parent_id raises ValueError."""
        with pytest.raises(ValueError, match="Parent directory not found"):
            svc.create_file({"name": "orphan.txt", "parent_id": "nonexistent-uuid"})

    def test_create_file_parent_is_file(self, svc):
        """Creating a file under a file (not directory) raises ValueError."""
        root_id = svc.game_state.filesystem.root_id
        f = svc.create_file({"name": "parent.txt", "parent_id": root_id, "content": ""})
        with pytest.raises(ValueError, match="Parent is not a directory"):
            svc.create_file({"name": "child.txt", "parent_id": f.id})

    def test_create_directory_invalid_parent_id(self, svc):
        """Creating a directory with a non-existent parent_id raises ValueError."""
        with pytest.raises(ValueError, match="Parent directory not found"):
            svc.create_directory({"name": "orphan", "parent_id": "nonexistent-uuid"})

    def test_create_directory_parent_is_file(self, svc):
        """Creating a directory under a file raises ValueError."""
        root_id = svc.game_state.filesystem.root_id
        f = svc.create_file({"name": "parent.txt", "parent_id": root_id, "content": ""})
        with pytest.raises(ValueError, match="Parent is not a directory"):
            svc.create_directory({"name": "child", "parent_id": f.id})

    def test_create_file_none_parent_id_ok(self, svc):
        """Creating a file with parent_id=None is allowed (e.g. root node)."""
        f = svc.create_file({"name": "rootfile.txt"})
        assert f.parent_id is None


class TestMoveFileWithRename:
    """Tests for atomic move_file with new_name parameter (fix #6)."""

    @pytest.fixture
    def svc(self):
        svc = AppService(GameState())
        svc.init_filesystem()
        return svc

    def test_move_file_with_rename(self, svc):
        """Move to a new parent with a new name in one operation."""
        root_id = svc.game_state.filesystem.root_id
        dir_a = svc.create_directory({"name": "A", "parent_id": root_id})
        dir_b = svc.create_directory({"name": "B", "parent_id": root_id})
        f = svc.create_file(
            {"name": "old.txt", "parent_id": dir_a.id, "content": "data"}
        )
        moved = svc.move_file(f.id, dir_b.id, new_name="new.txt")
        assert moved.parent_id == dir_b.id
        assert moved.name == "new.txt"
        assert moved.content == "data"
        # Verify indexes
        assert f.id in [n.id for n in svc.list_directory(dir_b.id)]
        assert f.id not in [n.id for n in svc.list_directory(dir_a.id)]

    def test_move_file_rename_only(self, svc):
        """Move to the same parent with a new name (effectively a rename)."""
        root_id = svc.game_state.filesystem.root_id
        f = svc.create_file(
            {"name": "old.txt", "parent_id": root_id, "content": "data"}
        )
        moved = svc.move_file(f.id, root_id, new_name="renamed.txt")
        assert moved.parent_id == root_id
        assert moved.name == "renamed.txt"

    def test_move_file_no_rename(self, svc):
        """Move without new_name keeps the original name."""
        root_id = svc.game_state.filesystem.root_id
        dir_a = svc.create_directory({"name": "A", "parent_id": root_id})
        f = svc.create_file(
            {"name": "keep.txt", "parent_id": root_id, "content": "data"}
        )
        moved = svc.move_file(f.id, dir_a.id)
        assert moved.name == "keep.txt"


class TestAppServiceLock:
    """Verify the concurrency lock exists (fix #1)."""

    def test_lock_attribute_exists(self):
        import asyncio

        svc = AppService(GameState())
        assert hasattr(svc, "lock")
        assert isinstance(svc.lock, asyncio.Lock)
