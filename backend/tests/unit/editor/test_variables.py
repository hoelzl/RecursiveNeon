"""Tests for editor variable system (Phase 6g)."""

from __future__ import annotations

import pytest

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.variables import VARIABLES, EditorVariable, defvar
from tests.unit.editor.harness import make_harness

# ═══════════════════════════════════════════════════════════════════════
# EditorVariable
# ═══════════════════════════════════════════════════════════════════════


class TestEditorVariable:
    def test_validate_int(self):
        v = EditorVariable(name="x", default=10, type=int)
        assert v.validate(42) == 42
        assert v.validate("7") == 7

    def test_validate_bool_true(self):
        v = EditorVariable(name="x", default=False, type=bool)
        assert v.validate(True) is True
        assert v.validate("true") is True
        assert v.validate("yes") is True
        assert v.validate("1") is True
        assert v.validate("on") is True

    def test_validate_bool_false(self):
        v = EditorVariable(name="x", default=False, type=bool)
        assert v.validate(False) is False
        assert v.validate("false") is False
        assert v.validate("no") is False
        assert v.validate("0") is False
        assert v.validate("off") is False

    def test_validate_bool_invalid(self):
        v = EditorVariable(name="x", default=False, type=bool)
        with pytest.raises(ValueError, match="expected bool"):
            v.validate("maybe")

    def test_validate_str(self):
        v = EditorVariable(name="x", default="hi", type=str)
        assert v.validate("hello") == "hello"
        assert v.validate(42) == "42"

    def test_validate_float(self):
        v = EditorVariable(name="x", default=1.0, type=float)
        assert v.validate("3.14") == pytest.approx(3.14)


# ═══════════════════════════════════════════════════════════════════════
# defvar and registry
# ═══════════════════════════════════════════════════════════════════════


class TestDefvar:
    def test_builtin_variables_registered(self):
        assert "fill-column" in VARIABLES
        assert "tab-width" in VARIABLES
        assert "indent-tabs-mode" in VARIABLES
        assert "truncate-lines" in VARIABLES
        assert "auto-fill" in VARIABLES

    def test_fill_column_defaults(self):
        v = VARIABLES["fill-column"]
        assert v.default == 70
        assert v.type is int

    def test_tab_width_defaults(self):
        v = VARIABLES["tab-width"]
        assert v.default == 8

    def test_indent_tabs_mode_defaults(self):
        v = VARIABLES["indent-tabs-mode"]
        assert v.default is False
        assert v.type is bool

    def test_defvar_creates_variable(self):
        v = defvar("test-phase6g-var", 99, "A test variable.", var_type=int)
        assert v.name == "test-phase6g-var"
        assert VARIABLES["test-phase6g-var"] is v
        # Clean up
        del VARIABLES["test-phase6g-var"]

    def test_defvar_infers_type(self):
        v = defvar("test-phase6g-infer", True, "Inferred bool.")
        assert v.type is bool
        del VARIABLES["test-phase6g-infer"]


# ═══════════════════════════════════════════════════════════════════════
# Buffer local variables
# ═══════════════════════════════════════════════════════════════════════


class TestBufferLocalVariables:
    def test_set_and_get_local(self):
        buf = Buffer(name="test")
        buf.set_variable_local("fill-column", 100)
        assert buf.local_variables["fill-column"] == 100

    def test_set_local_validates(self):
        buf = Buffer(name="test")
        buf.set_variable_local("fill-column", "80")
        assert buf.local_variables["fill-column"] == 80

    def test_set_local_unknown_variable(self):
        buf = Buffer(name="test")
        # Unknown variables are stored without validation
        buf.set_variable_local("unknown-var", "whatever")
        assert buf.local_variables["unknown-var"] == "whatever"


# ═══════════════════════════════════════════════════════════════════════
# Editor.get_variable / set_variable
# ═══════════════════════════════════════════════════════════════════════


class TestEditorVariables:
    def _make_editor(self) -> Editor:
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(name="test")
        return ed

    def test_get_global_default(self):
        ed = self._make_editor()
        assert ed.get_variable("fill-column") == 70

    def test_set_global_variable(self):
        ed = self._make_editor()
        old = VARIABLES["fill-column"].default
        try:
            ed.set_variable("fill-column", 80)
            assert ed.get_variable("fill-column") == 80
        finally:
            VARIABLES["fill-column"].default = old

    def test_buffer_local_overrides_global(self):
        ed = self._make_editor()
        ed.buffer.set_variable_local("fill-column", 100)
        assert ed.get_variable("fill-column") == 100

    def test_major_mode_overrides_global(self):
        ed = self._make_editor()

        ed.set_major_mode("text-mode")
        # text-mode sets auto-fill to True
        assert ed.get_variable("auto-fill") is True

    def test_buffer_local_overrides_major_mode(self):
        ed = self._make_editor()
        ed.set_major_mode("text-mode")
        ed.buffer.set_variable_local("auto-fill", False)
        assert ed.get_variable("auto-fill") is False

    def test_minor_mode_overrides_major_mode(self):
        """A minor mode's variable default overrides the major mode."""
        from recursive_neon.editor.modes import MODES, defmode

        defmode(
            "test-minor-6g",
            is_major=False,
            variables={"auto-fill": False},
            doc="Test minor mode",
        )
        try:
            ed = self._make_editor()
            ed.set_major_mode("text-mode")
            assert ed.get_variable("auto-fill") is True
            ed.toggle_minor_mode("test-minor-6g")
            assert ed.get_variable("auto-fill") is False
        finally:
            del MODES["test-minor-6g"]

    def test_get_unknown_variable(self):
        ed = self._make_editor()
        assert ed.get_variable("nonexistent") is None

    def test_set_unknown_variable_message(self):
        ed = self._make_editor()
        ed.set_variable("nonexistent", 42)
        assert "Unknown variable" in ed.message

    def test_set_variable_validates(self):
        ed = self._make_editor()
        old = VARIABLES["fill-column"].default
        try:
            ed.set_variable("fill-column", "90")
            assert ed.get_variable("fill-column") == 90
        finally:
            VARIABLES["fill-column"].default = old


# ═══════════════════════════════════════════════════════════════════════
# Describe-variable command (C-h v)
# ═══════════════════════════════════════════════════════════════════════


class TestDescribeVariable:
    def test_describe_variable_shows_help(self):
        h = make_harness("", width=80, height=24)
        h.send_keys("C-h", "v")
        h.type_string("fill-column")
        h.send_keys("Enter")
        text = h.buffer_text()
        assert "fill-column" in text
        assert "70" in text
        assert "int" in text

    def test_describe_variable_unknown(self):
        h = make_harness("", width=80, height=24)
        h.send_keys("C-h", "v")
        h.type_string("no-such-var")
        h.send_keys("Enter")
        assert "Unknown variable" in h.message_line()

    def test_describe_variable_shows_buffer_local(self):
        h = make_harness("", width=80, height=24)
        h.editor.buffer.set_variable_local("fill-column", 120)
        h.send_keys("C-h", "v")
        h.type_string("fill-column")
        h.send_keys("Enter")
        text = h.buffer_text()
        assert "120" in text
        assert "Buffer-local" in text


# ═══════════════════════════════════════════════════════════════════════
# Set-variable command (M-x set-variable)
# ═══════════════════════════════════════════════════════════════════════


class TestSetVariable:
    def test_set_variable_via_mx(self):
        h = make_harness("", width=80, height=24)
        old = VARIABLES["fill-column"].default
        try:
            h.send_keys("M-x")
            h.type_string("set-variable")
            h.send_keys("Enter")
            h.type_string("fill-column")
            h.send_keys("Enter")
            h.type_string("90")
            h.send_keys("Enter")
            assert "Set fill-column to 90" in h.message_line()
        finally:
            VARIABLES["fill-column"].default = old

    def test_set_variable_invalid_value(self):
        h = make_harness("", width=80, height=24)
        h.send_keys("M-x")
        h.type_string("set-variable")
        h.send_keys("Enter")
        h.type_string("indent-tabs-mode")
        h.send_keys("Enter")
        h.type_string("maybe")
        h.send_keys("Enter")
        assert "expected bool" in h.message_line()
