"""Tests for editor/config_loader.py — sandboxed user config execution."""

from __future__ import annotations

import textwrap

from recursive_neon.editor.commands import COMMANDS
from recursive_neon.editor.config_loader import (
    ConfigNamespace,
    _config_path,
    _exec_config,
    _make_safe_builtins,
    load_config,
)
from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.modes import MODES
from recursive_neon.editor.variables import VARIABLES


def _editor() -> Editor:
    return Editor(global_keymap=build_default_keymap())


class TestSafeBuiltins:
    """Restricted __builtins__ namespace."""

    def test_safe_builtins_excludes_open(self):
        safe = _make_safe_builtins()
        assert "open" not in safe

    def test_safe_builtins_excludes_exec(self):
        safe = _make_safe_builtins()
        assert "exec" not in safe

    def test_safe_builtins_excludes_eval(self):
        safe = _make_safe_builtins()
        assert "eval" not in safe

    def test_safe_builtins_excludes_compile(self):
        safe = _make_safe_builtins()
        assert "compile" not in safe

    def test_safe_builtins_has_restricted_import(self):
        safe = _make_safe_builtins()
        # __import__ is present but restricted, not the real one
        assert "__import__" in safe
        assert safe["__import__"] is not __import__

    def test_safe_builtins_excludes_globals(self):
        safe = _make_safe_builtins()
        assert "globals" not in safe

    def test_safe_builtins_excludes_locals(self):
        safe = _make_safe_builtins()
        assert "locals" not in safe

    def test_safe_builtins_excludes_breakpoint(self):
        safe = _make_safe_builtins()
        assert "breakpoint" not in safe

    def test_safe_builtins_includes_print(self):
        safe = _make_safe_builtins()
        assert "print" in safe

    def test_safe_builtins_includes_len(self):
        safe = _make_safe_builtins()
        assert "len" in safe

    def test_safe_builtins_includes_range(self):
        safe = _make_safe_builtins()
        assert "range" in safe

    def test_safe_builtins_includes_isinstance(self):
        safe = _make_safe_builtins()
        assert "isinstance" in safe

    def test_safe_builtins_includes_dict(self):
        safe = _make_safe_builtins()
        assert "dict" in safe


class TestConfigNamespace:
    """Namespace exposed to user config."""

    def test_namespace_contains_defcommand(self):
        ed = _editor()
        ns = ConfigNamespace(ed).build()
        assert "defcommand" in ns

    def test_namespace_contains_defvar(self):
        ed = _editor()
        ns = ConfigNamespace(ed).build()
        assert "defvar" in ns

    def test_namespace_contains_defmode(self):
        ed = _editor()
        ns = ConfigNamespace(ed).build()
        assert "defmode" in ns

    def test_namespace_contains_bind(self):
        ed = _editor()
        ns = ConfigNamespace(ed).build()
        assert "bind" in ns

    def test_namespace_contains_unbind(self):
        ed = _editor()
        ns = ConfigNamespace(ed).build()
        assert "unbind" in ns

    def test_namespace_contains_editor(self):
        ed = _editor()
        ns = ConfigNamespace(ed).build()
        assert ns["editor"] is ed

    def test_namespace_contains_buffer_class(self):
        ed = _editor()
        ns = ConfigNamespace(ed).build()
        from recursive_neon.editor.buffer import Buffer

        assert ns["Buffer"] is Buffer

    def test_namespace_contains_mark_class(self):
        ed = _editor()
        ns = ConfigNamespace(ed).build()
        from recursive_neon.editor.mark import Mark

        assert ns["Mark"] is Mark

    def test_namespace_contains_keymap_class(self):
        ed = _editor()
        ns = ConfigNamespace(ed).build()
        from recursive_neon.editor.keymap import Keymap

        assert ns["Keymap"] is Keymap

    def test_namespace_contains_mode_class(self):
        ed = _editor()
        ns = ConfigNamespace(ed).build()
        from recursive_neon.editor.modes import Mode

        assert ns["Mode"] is Mode

    def test_namespace_contains_syntax_rule_class(self):
        ed = _editor()
        ns = ConfigNamespace(ed).build()
        from recursive_neon.editor.modes import SyntaxRule

        assert ns["SyntaxRule"] is SyntaxRule

    def test_namespace_contains_commands_registry(self):
        ed = _editor()
        ns = ConfigNamespace(ed).build()
        assert ns["COMMANDS"] is COMMANDS

    def test_namespace_contains_modes_registry(self):
        ed = _editor()
        ns = ConfigNamespace(ed).build()
        assert ns["MODES"] is MODES


class TestExecConfig:
    """Executing user config source code."""

    def test_defcommand_in_config(self):
        """Config can define a new command."""
        ed = _editor()
        source = textwrap.dedent("""\
            @defcommand("my-test-cmd", "A test command.")
            def my_test_cmd(ed, prefix):
                ed.message = "hello from config"
        """)
        _exec_config(ed, source, "<test>")
        try:
            assert "my-test-cmd" in COMMANDS
            COMMANDS["my-test-cmd"].function(ed, None)
            assert ed.message == "hello from config"
        finally:
            COMMANDS.pop("my-test-cmd", None)

    def test_bind_in_config(self):
        """Config can bind a key."""
        ed = _editor()
        source = 'bind("M-z", "forward-char")'
        _exec_config(ed, source, "<test>")
        assert ed.global_keymap.lookup("M-z") == "forward-char"
        # Clean up
        ed.global_keymap.unbind("M-z")

    def test_unbind_in_config(self):
        """Config can unbind a key."""
        ed = _editor()
        ed.global_keymap.bind("M-z", "forward-char")
        source = 'unbind("M-z")'
        _exec_config(ed, source, "<test>")
        assert ed.global_keymap.lookup("M-z") != "forward-char"

    def test_bind_in_prefix_keymap(self):
        """Config can bind inside a prefix keymap like C-x."""
        ed = _editor()
        source = 'bind("z", "forward-char", keymap="C-x")'
        _exec_config(ed, source, "<test>")
        cx = ed.global_keymap.lookup("C-x")
        assert cx is not None
        assert cx.lookup("z") == "forward-char"
        # Clean up
        cx.unbind("z")

    def test_defvar_in_config(self):
        """Config can define a new variable."""
        ed = _editor()
        source = 'defvar("my-test-var", 42, "A test variable.", var_type=int)'
        _exec_config(ed, source, "<test>")
        try:
            assert "my-test-var" in VARIABLES
            assert VARIABLES["my-test-var"].default == 42
        finally:
            VARIABLES.pop("my-test-var", None)

    def test_defmode_in_config(self):
        """Config can define a new mode."""
        ed = _editor()
        source = 'defmode("my-test-mode", doc="Test mode.")'
        _exec_config(ed, source, "<test>")
        try:
            assert "my-test-mode" in MODES
        finally:
            MODES.pop("my-test-mode", None)

    def test_syntax_error_does_not_crash(self):
        """Syntax error in config surfaces in message, doesn't crash."""
        ed = _editor()
        source = "def foo(\n"  # broken syntax
        _exec_config(ed, source, "<test>")
        assert "Config syntax error" in ed.message

    def test_runtime_error_does_not_crash(self):
        """Runtime error in config surfaces in message, doesn't crash."""
        ed = _editor()
        source = "1 / 0\n"
        _exec_config(ed, source, "<test>")
        assert "Config error" in ed.message

    def test_open_raises_name_error(self):
        """open() is blocked in config namespace."""
        ed = _editor()
        source = 'open("foo.txt")\n'
        _exec_config(ed, source, "<test>")
        assert "Config error" in ed.message
        assert "NameError" in ed.message or "name" in ed.message

    def test_exec_raises_name_error(self):
        """exec() is blocked in config namespace."""
        ed = _editor()
        source = 'exec("print(1)")\n'
        _exec_config(ed, source, "<test>")
        assert "Config error" in ed.message

    def test_eval_raises_name_error(self):
        """eval() is blocked in config namespace."""
        ed = _editor()
        source = 'eval("1+1")\n'
        _exec_config(ed, source, "<test>")
        assert "Config error" in ed.message

    def test_import_os_blocked(self):
        """Importing unsafe modules (os) is blocked."""
        ed = _editor()
        source = "import os\n"
        _exec_config(ed, source, "<test>")
        assert "Config error" in ed.message

    def test_import_subprocess_blocked(self):
        """Importing subprocess is blocked."""
        ed = _editor()
        source = "import subprocess\n"
        _exec_config(ed, source, "<test>")
        assert "Config error" in ed.message

    def test_import_re_allowed(self):
        """Importing re (needed for syntax rules) is allowed."""
        ed = _editor()
        source = 'import re\nresult = re.compile(r"foo")\n'
        result = _exec_config(ed, source, "<test>")
        assert result is True

    def test_empty_config_is_noop(self):
        """An empty config file does nothing."""
        ed = _editor()
        _exec_config(ed, "", "<test>")
        assert not ed.message

    def test_config_can_access_editor(self):
        """Config can read and modify editor state."""
        ed = _editor()
        source = 'editor.message = "set by config"'
        _exec_config(ed, source, "<test>")
        assert ed.message == "set by config"

    def test_config_returns_true_on_success(self):
        ed = _editor()
        result = _exec_config(ed, "x = 1", "<test>")
        assert result is True

    def test_config_returns_false_on_syntax_error(self):
        ed = _editor()
        result = _exec_config(ed, "def(\n", "<test>")
        assert result is False

    def test_config_returns_false_on_runtime_error(self):
        ed = _editor()
        result = _exec_config(ed, "1/0", "<test>")
        assert result is False


class TestLoadConfig:
    """load_config integration with filesystem."""

    def test_missing_config_is_noop(self, tmp_path, monkeypatch):
        """Missing config file is silently ignored."""
        monkeypatch.setenv("RECURSIVE_NEON_CONFIG_PATH", str(tmp_path / "nope.py"))
        ed = _editor()
        load_config(ed)
        assert not ed.message

    def test_loads_config_from_env_path(self, tmp_path, monkeypatch):
        """Config file is loaded from RECURSIVE_NEON_CONFIG_PATH."""
        config = tmp_path / "my_config.py"
        config.write_text('editor.message = "loaded"', encoding="utf-8")
        monkeypatch.setenv("RECURSIVE_NEON_CONFIG_PATH", str(config))
        ed = _editor()
        load_config(ed)
        assert ed.message == "loaded"

    def test_reload_picks_up_changes(self, tmp_path, monkeypatch):
        """reload-config re-executes the config file."""
        config = tmp_path / "config.py"
        config.write_text('editor.message = "v1"', encoding="utf-8")
        monkeypatch.setenv("RECURSIVE_NEON_CONFIG_PATH", str(config))
        ed = _editor()
        load_config(ed)
        assert ed.message == "v1"

        config.write_text('editor.message = "v2"', encoding="utf-8")
        load_config(ed)
        assert ed.message == "v2"

    def test_env_var_overrides_default_path(self, tmp_path, monkeypatch):
        """RECURSIVE_NEON_CONFIG_PATH overrides the default."""
        monkeypatch.setenv("RECURSIVE_NEON_CONFIG_PATH", str(tmp_path / "alt.py"))
        assert _config_path() == tmp_path / "alt.py"

    def test_config_adds_command_available_in_editor(self, tmp_path, monkeypatch):
        """A command defined in config is usable by the editor."""
        config = tmp_path / "config.py"
        config.write_text(
            textwrap.dedent("""\
                @defcommand("config-hello", "Say hello from config.")
                def config_hello(ed, prefix):
                    ed.message = "config says hello"
            """),
            encoding="utf-8",
        )
        monkeypatch.setenv("RECURSIVE_NEON_CONFIG_PATH", str(config))
        ed = _editor()
        load_config(ed)
        try:
            assert ed.execute_command("config-hello")
            assert ed.message == "config says hello"
        finally:
            COMMANDS.pop("config-hello", None)

    def test_config_can_define_mode_with_syntax_rules(self, tmp_path, monkeypatch):
        """Config can define a mode with syntax rules."""
        config = tmp_path / "config.py"
        config.write_text(
            textwrap.dedent("""\
                import re
                rules = [SyntaxRule(re.compile(r"\\bTODO\\b"), "keyword")]
                defmode("todo-mode", doc="Highlights TODOs.", syntax_rules=rules)
            """),
            encoding="utf-8",
        )
        monkeypatch.setenv("RECURSIVE_NEON_CONFIG_PATH", str(config))
        ed = _editor()
        load_config(ed)
        try:
            assert "todo-mode" in MODES
            assert len(MODES["todo-mode"].syntax_rules) == 1
        finally:
            MODES.pop("todo-mode", None)


class TestReloadConfigCommand:
    """M-x reload-config command."""

    def test_reload_config_command_exists(self):
        assert "reload-config" in COMMANDS

    def test_reload_config_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RECURSIVE_NEON_CONFIG_PATH", str(tmp_path / "nope.py"))
        ed = _editor()
        ed.execute_command("reload-config")
        assert "No config file" in ed.message

    def test_reload_config_success(self, tmp_path, monkeypatch):
        config = tmp_path / "config.py"
        config.write_text("x = 1", encoding="utf-8")
        monkeypatch.setenv("RECURSIVE_NEON_CONFIG_PATH", str(config))
        ed = _editor()
        ed.execute_command("reload-config")
        assert "reloaded" in ed.message.lower()

    def test_reload_config_reports_error(self, tmp_path, monkeypatch):
        config = tmp_path / "config.py"
        config.write_text("1/0", encoding="utf-8")
        monkeypatch.setenv("RECURSIVE_NEON_CONFIG_PATH", str(config))
        ed = _editor()
        ed.execute_command("reload-config")
        assert "Config error" in ed.message


class TestBindResolveKeymap:
    """ConfigNamespace._resolve_keymap edge cases."""

    def test_resolve_global(self):
        ed = _editor()
        ns = ConfigNamespace(ed)
        km = ns._resolve_keymap("global")
        assert km is ed.global_keymap

    def test_resolve_prefix_keymap(self):
        ed = _editor()
        ns = ConfigNamespace(ed)
        km = ns._resolve_keymap("C-x")
        assert km is not None
        # C-x is a prefix map in the default keymap
        assert km.lookup("C-s") == "save-buffer"

    def test_resolve_unknown_keymap(self):
        ed = _editor()
        ns = ConfigNamespace(ed)
        assert ns._resolve_keymap("nonexistent") is None

    def test_bind_unknown_keymap_messages(self):
        ed = _editor()
        ns = ConfigNamespace(ed)
        ns._bind("z", "forward-char", keymap="nonexistent")
        assert "unknown keymap" in ed.message
