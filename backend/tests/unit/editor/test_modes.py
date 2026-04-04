"""Tests for editor mode system (Phase 6g)."""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.keymap import Keymap
from recursive_neon.editor.modes import MODES, defmode
from tests.unit.editor.harness import make_harness

# ═══════════════════════════════════════════════════════════════════════
# Mode registration
# ═══════════════════════════════════════════════════════════════════════


class TestModeRegistry:
    def test_fundamental_mode_registered(self):
        assert "fundamental-mode" in MODES
        assert MODES["fundamental-mode"].is_major is True

    def test_text_mode_registered(self):
        assert "text-mode" in MODES
        assert MODES["text-mode"].is_major is True
        assert MODES["text-mode"].variables.get("auto-fill") is True

    def test_defmode_creates_and_registers(self):
        m = defmode("test-reg-mode-6g", doc="Test mode")
        assert MODES["test-reg-mode-6g"] is m
        del MODES["test-reg-mode-6g"]


# ═══════════════════════════════════════════════════════════════════════
# Major mode switching
# ═══════════════════════════════════════════════════════════════════════


class TestMajorMode:
    def _make_editor(self) -> Editor:
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(name="test")
        return ed

    def test_new_buffer_gets_fundamental_mode(self):
        ed = self._make_editor()
        assert ed.buffer.major_mode is not None
        assert ed.buffer.major_mode.name == "fundamental-mode"

    def test_set_major_mode(self):
        ed = self._make_editor()
        assert ed.set_major_mode("text-mode") is True
        assert ed.buffer.major_mode is not None
        assert ed.buffer.major_mode.name == "text-mode"

    def test_set_unknown_mode(self):
        ed = self._make_editor()
        assert ed.set_major_mode("nonexistent-mode") is False
        assert "Unknown major mode" in ed.message

    def test_set_minor_as_major_fails(self):
        defmode("test-minor-maj-6g", is_major=False, doc="minor")
        try:
            ed = self._make_editor()
            assert ed.set_major_mode("test-minor-maj-6g") is False
        finally:
            del MODES["test-minor-maj-6g"]

    def test_on_enter_called(self):
        entered = []
        defmode("test-enter-6g", on_enter=lambda ed: entered.append(True))
        try:
            ed = self._make_editor()
            ed.set_major_mode("test-enter-6g")
            assert entered == [True]
        finally:
            del MODES["test-enter-6g"]

    def test_on_exit_called(self):
        exited = []
        defmode("test-exit-6g", on_exit=lambda ed: exited.append(True))
        try:
            ed = self._make_editor()
            ed.set_major_mode("test-exit-6g")
            # Now switch away
            ed.set_major_mode("fundamental-mode")
            assert exited == [True]
        finally:
            del MODES["test-exit-6g"]

    def test_mode_message(self):
        ed = self._make_editor()
        ed.set_major_mode("text-mode")
        assert "(text-mode)" in ed.message


# ═══════════════════════════════════════════════════════════════════════
# Minor mode toggling
# ═══════════════════════════════════════════════════════════════════════


class TestMinorMode:
    def _make_editor(self) -> Editor:
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(name="test")
        return ed

    def test_toggle_on(self):
        defmode("test-toggle-6g", is_major=False, doc="toggle test")
        try:
            ed = self._make_editor()
            assert ed.toggle_minor_mode("test-toggle-6g") is True
            assert len(ed.buffer.minor_modes) == 1
            assert ed.buffer.minor_modes[0].name == "test-toggle-6g"
            assert "enabled" in ed.message
        finally:
            del MODES["test-toggle-6g"]

    def test_toggle_off(self):
        defmode("test-toggle2-6g", is_major=False, doc="toggle test")
        try:
            ed = self._make_editor()
            ed.toggle_minor_mode("test-toggle2-6g")
            ed.toggle_minor_mode("test-toggle2-6g")
            assert len(ed.buffer.minor_modes) == 0
            assert "disabled" in ed.message
        finally:
            del MODES["test-toggle2-6g"]

    def test_toggle_major_as_minor_fails(self):
        ed = self._make_editor()
        assert ed.toggle_minor_mode("fundamental-mode") is False
        assert "Unknown minor mode" in ed.message

    def test_minor_mode_on_enter_exit(self):
        log: list[str] = []
        defmode(
            "test-hooks-6g",
            is_major=False,
            on_enter=lambda ed: log.append("enter"),
            on_exit=lambda ed: log.append("exit"),
        )
        try:
            ed = self._make_editor()
            ed.toggle_minor_mode("test-hooks-6g")
            assert log == ["enter"]
            ed.toggle_minor_mode("test-hooks-6g")
            assert log == ["enter", "exit"]
        finally:
            del MODES["test-hooks-6g"]


# ═══════════════════════════════════════════════════════════════════════
# Keymap resolution with modes
# ═══════════════════════════════════════════════════════════════════════


class TestModeKeymapResolution:
    def _make_editor(self) -> Editor:
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(name="test")
        return ed

    def test_major_mode_keymap_used(self):
        km = Keymap("test-major-km", parent=build_default_keymap())
        km.bind("C-t", "test-cmd")
        defmode("test-km-major-6g", keymap=km)
        try:
            ed = self._make_editor()
            ed.set_major_mode("test-km-major-6g")
            resolved = ed._resolve_keymap()
            assert resolved.lookup("C-t") == "test-cmd"
        finally:
            del MODES["test-km-major-6g"]

    def test_minor_mode_keymap_overrides_major(self):
        major_km = Keymap("major-km", parent=build_default_keymap())
        major_km.bind("C-t", "major-cmd")
        minor_km = Keymap("minor-km", parent=build_default_keymap())
        minor_km.bind("C-t", "minor-cmd")
        defmode("test-km-maj2-6g", keymap=major_km)
        defmode("test-km-min-6g", is_major=False, keymap=minor_km)
        try:
            ed = self._make_editor()
            ed.set_major_mode("test-km-maj2-6g")
            ed.toggle_minor_mode("test-km-min-6g")
            resolved = ed._resolve_keymap()
            assert resolved.lookup("C-t") == "minor-cmd"
        finally:
            del MODES["test-km-maj2-6g"]
            del MODES["test-km-min-6g"]

    def test_buffer_local_keymap_overrides_all(self):
        minor_km = Keymap("minor-km", parent=build_default_keymap())
        minor_km.bind("C-t", "minor-cmd")
        defmode("test-km-min2-6g", is_major=False, keymap=minor_km)
        try:
            ed = self._make_editor()
            ed.toggle_minor_mode("test-km-min2-6g")
            # Buffer-local keymap should win
            local_km = Keymap("local", parent=build_default_keymap())
            local_km.bind("C-t", "local-cmd")
            ed.buffer.keymap = local_km
            resolved = ed._resolve_keymap()
            assert resolved.lookup("C-t") == "local-cmd"
        finally:
            del MODES["test-km-min2-6g"]

    def test_global_keymap_fallback(self):
        ed = self._make_editor()
        resolved = ed._resolve_keymap()
        # C-f is in the global keymap
        assert resolved.lookup("C-f") == "forward-char"


# ═══════════════════════════════════════════════════════════════════════
# Modeline mode display
# ═══════════════════════════════════════════════════════════════════════


class TestModelineMode:
    def test_modeline_shows_fundamental(self):
        h = make_harness("hello", width=80, height=10)
        ml = h.modeline()
        assert "Fundamental" in ml

    def test_modeline_shows_text_mode(self):
        h = make_harness("hello", width=80, height=10)
        h.editor.set_major_mode("text-mode")
        # Re-render to pick up mode change
        h.send_keys("C-f")
        h.send_keys("C-b")
        ml = h.modeline()
        assert "Text" in ml

    def test_modeline_shows_minor_modes(self):
        defmode("test-ml-minor-6g", is_major=False, doc="test minor")
        try:
            h = make_harness("hello", width=80, height=10)
            h.editor.toggle_minor_mode("test-ml-minor-6g")
            h.send_keys("C-f")
            h.send_keys("C-b")
            ml = h.modeline()
            assert "Test-ml-minor" in ml
        finally:
            del MODES["test-ml-minor-6g"]


# ═══════════════════════════════════════════════════════════════════════
# Describe-mode updated output
# ═══════════════════════════════════════════════════════════════════════


class TestDescribeModeUpdated:
    def test_describe_mode_shows_major(self):
        h = make_harness("hello", width=80, height=24)
        h.send_keys("C-h", "m")
        text = h.buffer_text()
        assert "Major mode: fundamental-mode" in text

    def test_describe_mode_shows_minor(self):
        defmode("test-dm-minor-6g", is_major=False, doc="A test minor mode")
        try:
            h = make_harness("hello", width=80, height=24)
            h.editor.toggle_minor_mode("test-dm-minor-6g")
            h.send_keys("C-h", "m")
            text = h.buffer_text()
            assert "Minor modes:" in text
            assert "test-dm-minor-6g" in text
        finally:
            del MODES["test-dm-minor-6g"]
