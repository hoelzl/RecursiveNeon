"""Tests for _MarkSet — identity-based mark collection (TD-004)."""

from __future__ import annotations

import pytest

from recursive_neon.editor.buffer import _MarkSet
from recursive_neon.editor.mark import Mark


class TestMarkSetIdentity:
    def test_contains_uses_identity_not_equality(self):
        """Two marks at the same position are distinct by identity."""
        ms = _MarkSet()
        m1 = Mark(0, 0)
        m2 = Mark(0, 0)
        ms.add(m1)
        assert m1 in ms
        assert m2 not in ms

    def test_add_and_len(self):
        ms = _MarkSet()
        m = Mark(1, 2)
        ms.add(m)
        assert len(ms) == 1

    def test_discard_by_identity(self):
        ms = _MarkSet()
        m1 = Mark(5, 5)
        m2 = Mark(5, 5)
        ms.add(m1)
        ms.add(m2)
        assert len(ms) == 2
        ms.discard(m1)
        assert len(ms) == 1
        assert m1 not in ms
        assert m2 in ms

    def test_discard_noop_if_not_present(self):
        ms = _MarkSet()
        m = Mark(0, 0)
        ms.discard(m)  # no-op, no error
        assert len(ms) == 0

    def test_duplicate_add_asserts(self):
        ms = _MarkSet()
        m = Mark(3, 3)
        ms.add(m)
        with pytest.raises(AssertionError, match="already tracked"):
            ms.add(m)

    def test_iteration(self):
        ms = _MarkSet()
        marks = [Mark(i, 0) for i in range(3)]
        for m in marks:
            ms.add(m)
        assert list(ms) == marks


class TestBufferTrackMarkUsesMarkSet:
    def test_track_mark_identity(self):
        """Buffer.track_mark uses identity — two marks at same pos can coexist."""
        from recursive_neon.editor.buffer import Buffer

        b = Buffer()
        m1 = Mark(0, 0, kind="left")
        m2 = Mark(0, 0, kind="left")
        b.track_mark(m1)
        b.track_mark(m2)
        assert m1 in b._tracked_marks
        assert m2 in b._tracked_marks

    def test_untrack_mark_identity(self):
        from recursive_neon.editor.buffer import Buffer

        b = Buffer()
        m1 = Mark(0, 0, kind="left")
        m2 = Mark(0, 0, kind="left")
        b.track_mark(m1)
        b.track_mark(m2)
        b.untrack_mark(m1)
        assert m1 not in b._tracked_marks
        assert m2 in b._tracked_marks

    def test_double_track_is_noop(self):
        """track_mark with an already-tracked mark is a no-op."""
        from recursive_neon.editor.buffer import Buffer

        b = Buffer()
        m = Mark(1, 1, kind="left")
        b.track_mark(m)
        b.track_mark(m)  # should not assert — track_mark checks first
        assert sum(1 for t in b._tracked_marks if t is m) == 1
