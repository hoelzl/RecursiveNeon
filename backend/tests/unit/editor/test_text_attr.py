"""Tests for TextAttr (Phase 7a-2)."""

from recursive_neon.editor.text_attr import TextAttr


class TestTextAttrBasics:
    def test_default_is_empty(self):
        a = TextAttr()
        assert a.fg is None
        assert a.bg is None
        assert not a.bold

    def test_equality(self):
        a = TextAttr(fg=1, bold=True)
        b = TextAttr(fg=1, bold=True)
        assert a == b

    def test_inequality(self):
        a = TextAttr(fg=1)
        b = TextAttr(fg=2)
        assert a != b

    def test_frozen(self):
        a = TextAttr(fg=1)
        try:
            a.fg = 2  # type: ignore[misc]
            assert False, "should be frozen"
        except AttributeError:
            pass


class TestToSgr:
    def test_default_empty(self):
        assert TextAttr().to_sgr() == ""

    def test_bold(self):
        assert TextAttr(bold=True).to_sgr() == "\033[1m"

    def test_fg_color(self):
        assert TextAttr(fg=1).to_sgr() == "\033[38;5;1m"

    def test_bg_color(self):
        assert TextAttr(bg=4).to_sgr() == "\033[48;5;4m"

    def test_combined(self):
        sgr = TextAttr(fg=1, bold=True, underline=True).to_sgr()
        assert "1" in sgr  # bold
        assert "4" in sgr  # underline
        assert "38;5;1" in sgr  # fg

    def test_cached(self):
        a = TextAttr(fg=1)
        first = a.to_sgr()
        second = a.to_sgr()
        assert first is second  # same object (cached)
