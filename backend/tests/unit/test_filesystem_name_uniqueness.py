"""
Regression tests for TD-006: duplicate filenames within a single directory.

**Bug report** (2026-04-05): a user reported seeing two files with the same
name in the same directory after editing multiple files via ``edit`` + C-x 2
+ C-x C-f.  Investigation identified two independent root causes:

1. **Filesystem layer** — ``AppService.create_file``,
   ``create_directory``, ``update_file`` (rename path), ``copy_file`` and
   ``move_file`` do not check for name collisions within the target
   parent directory.  Nothing prevents two nodes with identical
   ``(parent_id, name)`` from coexisting, which breaks path resolution
   (``resolve_path`` returns the first match, making later duplicates
   invisible to most commands).

2. **Editor layer** — ``shell/programs/edit.py``'s ``save_callback``
   captures a single shared ``file_id`` closure across the entire
   editor session.  A buffer opened via ``find-file`` (C-x C-f) starts
   with ``file_id = None``; saving that buffer calls
   ``app_service.create_file`` even though the file already exists,
   producing a duplicate node with the same name as the file the user
   intended to update.  See ``test_edit_save_callback.py`` for
   editor-layer coverage.

These tests target **bug 1** — the filesystem must refuse to create or
rename a node into a name that already exists within the parent.  They
are currently marked ``xfail(strict=True)`` so they document the
expected behaviour and turn into passing tests the moment the fix lands.
Removing the xfail marker is part of the fix PR.

See ``docs/V2_HANDOVER.md`` (Phase 7, TD-006) and
``docs/TECH_DEBT.md`` (TD-006) for the fix plan.
"""

from __future__ import annotations

import contextlib

import pytest

from recursive_neon.models.game_state import GameState
from recursive_neon.services.app_service import AppService


@pytest.fixture
def svc() -> AppService:
    """Fresh app service with an initialised root directory."""
    service = AppService(GameState())
    service.init_filesystem()
    return service


def _root_id(svc: AppService) -> str:
    root_id = svc.game_state.filesystem.root_id
    assert root_id is not None
    return root_id


# ═══════════════════════════════════════════════════════════════════════
# create_file: duplicate name in same parent must be rejected
# ═══════════════════════════════════════════════════════════════════════


class TestCreateFileDuplicate:
    @pytest.mark.xfail(
        strict=True,
        reason="TD-006 bug 1: create_file does not check for name collisions",
    )
    def test_create_file_rejects_duplicate_name_in_same_parent(self, svc):
        """Creating a second file with the same name in the same parent
        must raise ``ValueError`` (or ``FileExistsError``).
        """
        root = _root_id(svc)
        svc.create_file({"name": "readme.txt", "parent_id": root, "content": "first"})
        with pytest.raises((ValueError, FileExistsError)):
            svc.create_file(
                {"name": "readme.txt", "parent_id": root, "content": "second"}
            )

    @pytest.mark.xfail(
        strict=True,
        reason="TD-006 bug 1: create_file does not check for name collisions",
    )
    def test_duplicate_creation_leaves_only_one_node(self, svc):
        """Even with the current buggy behaviour, there must not be two
        nodes sharing ``(parent_id, name)`` after a rejected create.
        """
        root = _root_id(svc)
        svc.create_file({"name": "a.txt", "parent_id": root})
        with contextlib.suppress(ValueError, FileExistsError):
            svc.create_file({"name": "a.txt", "parent_id": root})
        # Expectation: exactly one child of root named "a.txt"
        children = [c for c in svc.list_directory(root) if c.name == "a.txt"]
        assert len(children) == 1

    def test_same_name_different_parents_is_allowed(self, svc):
        """Two files with the same name in **different** directories is
        perfectly legal (mirrors real filesystems).  Not an xfail —
        current behaviour already handles this correctly.
        """
        root = _root_id(svc)
        dir_a = svc.create_directory({"name": "A", "parent_id": root})
        dir_b = svc.create_directory({"name": "B", "parent_id": root})
        svc.create_file({"name": "notes.txt", "parent_id": dir_a.id})
        svc.create_file({"name": "notes.txt", "parent_id": dir_b.id})
        assert len(svc.list_directory(dir_a.id)) == 1
        assert len(svc.list_directory(dir_b.id)) == 1


# ═══════════════════════════════════════════════════════════════════════
# create_directory: duplicate name in same parent must be rejected
# ═══════════════════════════════════════════════════════════════════════


class TestCreateDirectoryDuplicate:
    @pytest.mark.xfail(
        strict=True,
        reason="TD-006 bug 1: create_directory does not check for collisions",
    )
    def test_create_directory_rejects_duplicate(self, svc):
        root = _root_id(svc)
        svc.create_directory({"name": "Documents", "parent_id": root})
        with pytest.raises((ValueError, FileExistsError)):
            svc.create_directory({"name": "Documents", "parent_id": root})

    @pytest.mark.xfail(
        strict=True,
        reason="TD-006 bug 1: directory/file name collision not rejected",
    )
    def test_directory_cannot_shadow_existing_file(self, svc):
        """A directory with the same name as an existing file in the
        same parent must be rejected — path resolution can't distinguish
        them.
        """
        root = _root_id(svc)
        svc.create_file({"name": "shared", "parent_id": root})
        with pytest.raises((ValueError, FileExistsError)):
            svc.create_directory({"name": "shared", "parent_id": root})


# ═══════════════════════════════════════════════════════════════════════
# update_file (rename): target name collision must be rejected
# ═══════════════════════════════════════════════════════════════════════


class TestUpdateFileRenameCollision:
    @pytest.mark.xfail(
        strict=True,
        reason="TD-006 bug 1: update_file rename does not check collisions",
    )
    def test_rename_to_existing_name_rejected(self, svc):
        root = _root_id(svc)
        svc.create_file({"name": "keep.txt", "parent_id": root})
        other = svc.create_file({"name": "rename_me.txt", "parent_id": root})
        with pytest.raises((ValueError, FileExistsError)):
            svc.update_file(other.id, {"name": "keep.txt"})

    def test_rename_to_own_name_is_noop(self, svc):
        """Renaming a file to its current name must succeed (no-op)."""
        root = _root_id(svc)
        node = svc.create_file({"name": "same.txt", "parent_id": root})
        updated = svc.update_file(node.id, {"name": "same.txt"})
        assert updated.name == "same.txt"


# ═══════════════════════════════════════════════════════════════════════
# copy_file: target directory collision
# ═══════════════════════════════════════════════════════════════════════


class TestCopyFileCollision:
    @pytest.mark.xfail(
        strict=True,
        reason="TD-006 bug 1: copy_file does not check for target name collision",
    )
    def test_copy_into_parent_with_existing_name_rejected(self, svc):
        """Copying a file into a directory that already has a child
        with the same name must raise (or require ``new_name``).
        """
        root = _root_id(svc)
        dir_a = svc.create_directory({"name": "A", "parent_id": root})
        dir_b = svc.create_directory({"name": "B", "parent_id": root})
        source = svc.create_file({"name": "doc.txt", "parent_id": dir_a.id})
        svc.create_file({"name": "doc.txt", "parent_id": dir_b.id})  # blocker
        with pytest.raises((ValueError, FileExistsError)):
            svc.copy_file(source.id, dir_b.id)

    def test_copy_into_parent_with_new_name_allowed(self, svc):
        """Copying with an explicit ``new_name`` that does not collide
        must succeed (current behaviour).
        """
        root = _root_id(svc)
        dir_a = svc.create_directory({"name": "A", "parent_id": root})
        dir_b = svc.create_directory({"name": "B", "parent_id": root})
        source = svc.create_file({"name": "doc.txt", "parent_id": dir_a.id})
        svc.copy_file(source.id, dir_b.id, new_name="doc_copy.txt")
        names = {c.name for c in svc.list_directory(dir_b.id)}
        assert "doc_copy.txt" in names


# ═══════════════════════════════════════════════════════════════════════
# move_file: target directory collision
# ═══════════════════════════════════════════════════════════════════════


class TestMoveFileCollision:
    @pytest.mark.xfail(
        strict=True,
        reason="TD-006 bug 1: move_file does not check for target name collision",
    )
    def test_move_into_parent_with_existing_name_rejected(self, svc):
        root = _root_id(svc)
        dir_a = svc.create_directory({"name": "A", "parent_id": root})
        dir_b = svc.create_directory({"name": "B", "parent_id": root})
        source = svc.create_file({"name": "doc.txt", "parent_id": dir_a.id})
        svc.create_file({"name": "doc.txt", "parent_id": dir_b.id})
        with pytest.raises((ValueError, FileExistsError)):
            svc.move_file(source.id, dir_b.id)

    @pytest.mark.xfail(
        strict=True,
        reason="TD-006 bug 1: rename-during-move does not check collisions",
    )
    def test_move_with_new_name_collision_rejected(self, svc):
        """Moving with ``new_name`` that collides in the target must be
        rejected, even if the source's original name wouldn't collide.
        """
        root = _root_id(svc)
        dir_a = svc.create_directory({"name": "A", "parent_id": root})
        dir_b = svc.create_directory({"name": "B", "parent_id": root})
        source = svc.create_file({"name": "src.txt", "parent_id": dir_a.id})
        svc.create_file({"name": "taken.txt", "parent_id": dir_b.id})
        with pytest.raises((ValueError, FileExistsError)):
            svc.move_file(source.id, dir_b.id, new_name="taken.txt")


# ═══════════════════════════════════════════════════════════════════════
# Path resolution invariant
# ═══════════════════════════════════════════════════════════════════════


class TestPathResolutionInvariant:
    @pytest.mark.xfail(
        strict=True,
        reason="TD-006 bug 1: duplicates break path resolution uniqueness",
    )
    def test_resolve_path_is_deterministic_after_duplicate_attempt(self, svc):
        """After any sequence of operations, ``resolve_path`` must
        always return the unique node at a given path — guaranteed by
        the uniqueness invariant enforced during create/update/move.
        """
        from recursive_neon.shell.path_resolver import resolve_path

        root = _root_id(svc)
        svc.create_file({"name": "pinned.txt", "parent_id": root, "content": "one"})
        # Any attempt to introduce a duplicate must be rejected.
        with pytest.raises((ValueError, FileExistsError)):
            svc.create_file({"name": "pinned.txt", "parent_id": root, "content": "two"})
        # resolve_path returns the single original node.
        node = resolve_path("/pinned.txt", root, svc)
        assert node.content == "one"
