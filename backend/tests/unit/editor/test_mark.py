"""Tests for the Mark class."""

from __future__ import annotations

from recursive_neon.editor.mark import Mark


class TestMarkCreation:
    def test_default_kind_is_temporary(self):
        m = Mark(0, 0)
        assert m.kind == "temporary"

    def test_explicit_kind(self):
        assert Mark(0, 0, kind="left").kind == "left"
        assert Mark(0, 0, kind="right").kind == "right"

    def test_to_tuple(self):
        assert Mark(3, 7).to_tuple() == (3, 7)


class TestMarkComparison:
    def test_equal_position(self):
        assert Mark(1, 5) == Mark(1, 5)

    def test_equal_ignores_kind(self):
        assert Mark(1, 5, "left") == Mark(1, 5, "right")

    def test_not_equal_different_line(self):
        assert Mark(0, 5) != Mark(1, 5)

    def test_not_equal_different_col(self):
        assert Mark(1, 3) != Mark(1, 5)

    def test_not_equal_to_non_mark(self):
        assert Mark(0, 0) != (0, 0)

    def test_less_than_same_line(self):
        assert Mark(1, 3) < Mark(1, 5)

    def test_less_than_different_line(self):
        assert Mark(0, 99) < Mark(1, 0)

    def test_not_less_than_equal(self):
        assert not (Mark(1, 5) < Mark(1, 5))

    def test_less_equal(self):
        assert Mark(1, 5) <= Mark(1, 5)
        assert Mark(1, 3) <= Mark(1, 5)

    def test_greater_than(self):
        assert Mark(2, 0) > Mark(1, 99)

    def test_greater_equal(self):
        assert Mark(2, 0) >= Mark(1, 99)
        assert Mark(1, 5) >= Mark(1, 5)

    def test_ordering_chain(self):
        marks = [Mark(2, 0), Mark(0, 5), Mark(1, 3), Mark(0, 0)]
        marks.sort()
        assert marks == [Mark(0, 0), Mark(0, 5), Mark(1, 3), Mark(2, 0)]


class TestMarkCopy:
    def test_copy_preserves_position(self):
        m = Mark(3, 7, "left")
        c = m.copy()
        assert c == m
        assert c.kind == "left"
        assert c is not m

    def test_copy_with_kind_override(self):
        m = Mark(3, 7, "left")
        c = m.copy(kind="right")
        assert c.line == 3 and c.col == 7
        assert c.kind == "right"

    def test_copy_is_independent(self):
        m = Mark(3, 7)
        c = m.copy()
        c.line = 0
        assert m.line == 3


class TestMarkMoveTo:
    def test_move_to(self):
        m = Mark(0, 0)
        m.move_to(5, 10)
        assert m.line == 5
        assert m.col == 10

    def test_move_to_preserves_kind(self):
        m = Mark(0, 0, "left")
        m.move_to(1, 1)
        assert m.kind == "left"


class TestMarkHash:
    def test_hashable_in_set(self):
        s = {Mark(0, 0, "left"), Mark(0, 0, "right")}
        # Different kinds get different hashes
        assert len(s) == 2

    def test_same_hash_for_identical(self):
        assert hash(Mark(1, 2, "left")) == hash(Mark(1, 2, "left"))
