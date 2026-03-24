"""Tests for path resolution."""

import pytest

from recursive_neon.shell.path_resolver import (
    get_node_path,
    resolve_parent_and_name,
    resolve_path,
)


@pytest.mark.unit
class TestResolvePath:
    """Test resolve_path with various path forms."""

    def test_resolve_root(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        node = resolve_path("/", root_id, test_container.app_service)
        assert node.id == root_id
        assert node.name == "/"

    def test_resolve_absolute_directory(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        node = resolve_path("/Documents", root_id, test_container.app_service)
        assert node.name == "Documents"
        assert node.type == "directory"

    def test_resolve_absolute_file(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        node = resolve_path(
            "/Documents/readme.txt", root_id, test_container.app_service
        )
        assert node.name == "readme.txt"
        assert node.type == "file"

    def test_resolve_relative_from_cwd(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        # First get Documents id
        docs = resolve_path("/Documents", root_id, test_container.app_service)
        # Then resolve relative path from Documents
        node = resolve_path("readme.txt", docs.id, test_container.app_service)
        assert node.name == "readme.txt"

    def test_resolve_dot(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        docs = resolve_path("/Documents", root_id, test_container.app_service)
        node = resolve_path(".", docs.id, test_container.app_service)
        assert node.id == docs.id

    def test_resolve_dotdot(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        docs = resolve_path("/Documents", root_id, test_container.app_service)
        node = resolve_path("..", docs.id, test_container.app_service)
        assert node.id == root_id

    def test_resolve_dotdot_at_root(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        node = resolve_path("..", root_id, test_container.app_service)
        assert node.id == root_id

    def test_resolve_complex_path(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        # /Documents/../Documents/readme.txt
        node = resolve_path(
            "/Documents/../Documents/readme.txt",
            root_id,
            test_container.app_service,
        )
        assert node.name == "readme.txt"

    def test_resolve_nonexistent_raises(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        with pytest.raises(FileNotFoundError, match="No such file or directory"):
            resolve_path("/nonexistent", root_id, test_container.app_service)

    def test_resolve_through_file_raises(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        with pytest.raises(NotADirectoryError):
            resolve_path(
                "/welcome.txt/something",
                root_id,
                test_container.app_service,
            )

    def test_resolve_path_with_spaces(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        node = resolve_path("/My Folder", root_id, test_container.app_service)
        assert node.name == "My Folder"
        assert node.type == "directory"


@pytest.mark.unit
class TestResolveParentAndName:
    def test_simple_name(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        parent, name = resolve_parent_and_name(
            "newfile.txt", root_id, test_container.app_service
        )
        assert parent.id == root_id
        assert name == "newfile.txt"

    def test_absolute_path(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        parent, name = resolve_parent_and_name(
            "/Documents/newfile.txt", root_id, test_container.app_service
        )
        assert parent.name == "Documents"
        assert name == "newfile.txt"

    def test_root_level(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        parent, name = resolve_parent_and_name(
            "/newfile.txt", root_id, test_container.app_service
        )
        assert parent.id == root_id
        assert name == "newfile.txt"

    def test_empty_path_raises(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        with pytest.raises(ValueError, match="name component"):
            resolve_parent_and_name("", root_id, test_container.app_service)

    def test_just_slash_raises(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        with pytest.raises(ValueError, match="name component"):
            resolve_parent_and_name("/", root_id, test_container.app_service)


@pytest.mark.unit
class TestGetNodePath:
    def test_root_path(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        assert get_node_path(root_id, test_container.app_service) == "/"

    def test_directory_path(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        docs = resolve_path("/Documents", root_id, test_container.app_service)
        assert get_node_path(docs.id, test_container.app_service) == "/Documents"

    def test_file_path(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        node = resolve_path(
            "/Documents/readme.txt", root_id, test_container.app_service
        )
        path = get_node_path(node.id, test_container.app_service)
        assert path == "/Documents/readme.txt"

    def test_path_with_spaces(self, test_container):
        root_id = test_container.game_state.filesystem.root_id
        node = resolve_path("/My Folder", root_id, test_container.app_service)
        assert get_node_path(node.id, test_container.app_service) == "/My Folder"
