"""Contract tests for the deterministic core editor profile."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import FrozenInstanceError
from types import ModuleType

import pytest

from recursive_neon.editor.editor import Editor
from recursive_neon.editor.modes import MODES
from recursive_neon.editor.variables import VARIABLES


def _core_module() -> ModuleType:
    try:
        return importlib.import_module("recursive_neon.editor.core")
    except ModuleNotFoundError:
        pytest.fail("recursive_neon.editor.core is not implemented")


def test_core_contract_is_exported_from_editor_package() -> None:
    core = _core_module()
    package = importlib.import_module("recursive_neon.editor")

    assert package.CoreEditorSession is core.CoreEditorSession
    assert package.EditorObservationV1 is core.EditorObservationV1
    assert package.create_core_editor is core.create_core_editor


def test_lazy_compatibility_exports_remain_discoverable() -> None:
    import recursive_neon.editor as editor_package
    import recursive_neon.shell as shell_package

    assert {
        "BufferOutput",
        "ConfigNamespace",
        "ShellBufferInput",
        "ShellState",
        "build_default_keymap",
        "load_config",
        "setup_shell_buffer",
        "strip_ansi",
    } <= set(dir(editor_package))
    assert {"InputSource", "Shell"} <= set(dir(shell_package))


def test_core_import_and_edit_are_capability_free() -> None:
    script = """
import json
import sys
import asyncio
import builtins
import socket
from pathlib import Path

def deny_capability(*args, **kwargs):
    raise AssertionError("prohibited host capability attempted")

builtins.open = deny_capability
Path.open = deny_capability
Path.read_text = deny_capability
Path.resolve = deny_capability
asyncio.create_task = deny_capability
socket.socket = deny_capability

from recursive_neon.editor.core import create_core_editor
from recursive_neon.editor.core_commands import build_core_keymap

forbidden = (
    "recursive_neon.editor.app_host",
    "recursive_neon.editor.config_loader",
    "recursive_neon.editor.default_commands",
    "recursive_neon.editor.dired",
    "recursive_neon.editor.game_bridge",
    "recursive_neon.editor.isearch_commands",
    "recursive_neon.editor.register_commands",
    "recursive_neon.editor.replace_commands",
    "recursive_neon.editor.shell_mode",
)
keymap = build_core_keymap()
session = create_core_editor(
    content="alpha",
    name="fixture.txt",
    columns=40,
    rows=10,
)
session.start()
step = session.send_key("X")
print(json.dumps({
    "loaded": [name for name in forbidden if name in sys.modules],
    "bindings": sorted(keymap.all_bindings()),
    "text": step.observation.text,
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["loaded"] == []
    assert payload["text"] == "Xalpha"
    assert "C-x" in payload["bindings"]
    assert "C-f" in payload["bindings"]
    assert "M-x" not in payload["bindings"]
    assert "C-x d" not in payload["bindings"]


def test_core_session_start_returns_stable_state_and_frame() -> None:
    core = _core_module()
    session = core.create_core_editor(
        content="alpha\nbeta",
        name="fixture.txt",
        columns=40,
        rows=10,
    )

    step = session.start()

    assert step.observation.buffer_name == "fixture.txt"
    assert step.observation.text == "alpha\nbeta"
    assert step.observation.point.line == 0
    assert step.observation.point.column == 0
    assert step.observation.modified is False
    assert step.observation.running is True
    assert step.observation.buffer_names == ("fixture.txt",)
    assert step.observation.minibuffer_active is False
    assert step.observation.minibuffer_prompt == ""
    assert step.observation.minibuffer_text == ""
    assert step.observation.active_window_buffer == "fixture.txt"
    assert step.observation.visible_start_line == 0
    assert step.observation.visible_end_line == 2
    assert isinstance(step.observation, core.EditorObservationV1)
    assert step.observation.schema_version == 1
    encoded = step.observation.to_dict()
    assert encoded["schema_version"] == 1
    assert encoded["point"] == {"line": 0, "column": 0}
    assert json.loads(json.dumps(encoded)) == encoded
    assert step.frame.columns == 40
    assert step.frame.rows == 10
    assert len(step.frame.lines) == 10
    assert step.frame.cursor.line == 0
    assert step.frame.cursor.column == 0


def test_core_session_rejects_invalid_lifecycle_transitions() -> None:
    core = _core_module()
    session = core.create_core_editor(
        content="alpha",
        name="fixture.txt",
        columns=40,
        rows=10,
    )

    for operation in (
        lambda: session.send_key("X"),
        lambda: session.resize(columns=50, rows=12),
        session.observe,
        session.stop,
        session.abort,
    ):
        with pytest.raises(RuntimeError, match="not started"):
            operation()

    session.start()
    with pytest.raises(RuntimeError, match="already started"):
        session.start()


def test_core_session_rejects_layouts_without_a_content_row() -> None:
    core = _core_module()
    with pytest.raises(ValueError, match="at least 3"):
        core.create_core_editor(
            content="alpha",
            name="fixture.txt",
            columns=40,
            rows=2,
        )

    session = core.create_core_editor(
        content="alpha",
        name="fixture.txt",
        columns=40,
        rows=3,
    )
    session.start()
    with pytest.raises(ValueError, match="at least 3"):
        session.resize(columns=40, rows=2)


def test_core_session_key_dispatch_uses_isolated_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from recursive_neon.editor.commands import COMMANDS

    importlib.import_module("recursive_neon.editor.default_commands")

    core = _core_module()

    def corrupt_self_insert(editor: Editor, prefix: int | None) -> None:
        del prefix
        editor.message = "global command used"

    monkeypatch.setattr(
        COMMANDS["self-insert-command"],
        "function",
        corrupt_self_insert,
    )
    session = core.create_core_editor(
        content="alpha",
        name="fixture.txt",
        columns=40,
        rows=10,
    )
    session.start()

    step = session.send_key("X")

    assert step.observation.text == "Xalpha"
    assert step.observation.point.column == 1
    assert step.observation.message == ""


def test_core_session_supports_movement_insertion_and_undo() -> None:
    core = _core_module()
    session = core.create_core_editor(
        content="alpha\nbeta",
        name="fixture.txt",
        columns=40,
        rows=10,
    )
    session.start()

    moved = session.send_key("M->")
    inserted = session.send_key("X")
    undone = session.send_key("C-/")

    assert moved.observation.point == core.CoreEditorPosition(line=1, column=4)
    assert inserted.observation.text == "alpha\nbetaX"
    assert undone.observation.text == "alpha\nbeta"
    assert undone.observation.point == core.CoreEditorPosition(line=1, column=4)


def test_core_session_supports_linear_undo_redo() -> None:
    core = _core_module()
    session = core.create_core_editor(
        content="hello world\n",
        name="fixture.txt",
        columns=40,
        rows=10,
    )
    session.start()

    session.send_key("A")
    session.send_key("B")
    session.send_key("C-e")
    session.send_key("C")
    edited = session.send_key("D")
    first_undo = session.send_key("C-/")
    second_undo = session.send_key("C-/")
    session.send_key("C-f")
    redone = session.send_key("C-/")

    assert edited.observation.text == "ABhello worldCD\n"
    assert first_undo.observation.text == "ABhello world\n"
    assert second_undo.observation.text == "hello world\n"
    assert redone.observation.text == "ABhello world\n"
    assert redone.observation.message == "Redo"


def test_core_self_insert_preserves_auto_fill_semantics() -> None:
    core = _core_module()
    session = core.create_core_editor(
        content="word word",
        name="fixture.txt",
        columns=40,
        rows=10,
    )
    session._view.editor.set_variable("fill-column", 5)
    session._view.editor.set_variable("auto-fill", True)
    session.start()
    session.send_key("M->")

    step = session.send_key(" ")

    assert step.observation.text == "word\nword "
    assert step.observation.point == core.CoreEditorPosition(line=1, column=5)


def test_core_session_uses_isolated_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    core = _core_module()
    monkeypatch.setattr(MODES["fundamental-mode"], "name", "corrupted-mode")

    session = core.create_core_editor(
        content="alpha",
        name="fixture.txt",
        columns=40,
        rows=10,
    )

    step = session.start()

    assert step.observation.major_mode == "fundamental-mode"


def test_core_session_uses_isolated_variable_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core = _core_module()
    monkeypatch.setattr(VARIABLES["line-number-mode"], "default", False)

    session = core.create_core_editor(
        content="alpha",
        name="fixture.txt",
        columns=40,
        rows=10,
    )

    step = session.start()

    assert "L1" in step.frame.lines[-2]


def test_core_sessions_own_distinct_registry_values() -> None:
    core = _core_module()
    first = core.create_core_editor(
        content="alpha",
        name="first.txt",
        columns=40,
        rows=10,
    )
    second = core.create_core_editor(
        content="beta",
        name="second.txt",
        columns=40,
        rows=10,
    )

    first._view.editor.commands["self-insert-command"].doc = "first only"
    first._view.editor.modes["fundamental-mode"].name = "first-mode"
    first._view.editor.variables["line-number-mode"].default = False

    assert second._view.editor.commands["self-insert-command"].doc != "first only"
    assert second._view.editor.modes["fundamental-mode"].name == "fundamental-mode"
    assert second._view.editor.variables["line-number-mode"].default is True


def test_core_session_resize_preserves_semantic_state() -> None:
    core = _core_module()
    session = core.create_core_editor(
        content="alpha\nbeta",
        name="fixture.txt",
        columns=40,
        rows=10,
    )
    session.start()
    edited = session.send_key("X")

    resized = session.resize(columns=60, rows=20)

    assert resized.observation == edited.observation
    assert resized.frame.columns == 60
    assert resized.frame.rows == 20
    assert len(resized.frame.lines) == 20
    assert 0 <= resized.frame.cursor.line < 20
    assert 0 <= resized.frame.cursor.column < 60


def test_core_session_observe_returns_immutable_latest_epoch() -> None:
    core = _core_module()
    session = core.create_core_editor(
        content="alpha",
        name="fixture.txt",
        columns=40,
        rows=10,
    )
    session.start()
    latest = session.send_key("X")

    observed = session.observe()

    assert observed == latest
    with pytest.raises(FrozenInstanceError):
        observed.observation.text = "corrupted"


def test_core_session_reports_natural_editor_exit() -> None:
    core = _core_module()
    session = core.create_core_editor(
        content="alpha",
        name="fixture.txt",
        columns=40,
        rows=10,
    )
    session.start()
    session.send_key("C-x")

    finished = session.send_key("C-c")

    assert isinstance(finished, core.CoreEditorFinished)
    assert finished.reason == "exit"
    assert finished.observation.running is False
    with pytest.raises(RuntimeError, match="finished"):
        session.send_key("X")


@pytest.mark.parametrize(("method", "reason"), (("stop", "stop"), ("abort", "abort")))
def test_core_session_has_explicit_terminal_lifecycle(
    method: str,
    reason: str,
) -> None:
    core = _core_module()
    session = core.create_core_editor(
        content="alpha",
        name="fixture.txt",
        columns=40,
        rows=10,
    )
    session.start()
    session.send_key("X")

    finished = getattr(session, method)()

    assert isinstance(finished, core.CoreEditorFinished)
    assert finished.reason == reason
    assert finished.observation.text == "Xalpha"
    assert finished.observation.running is False
    with pytest.raises(RuntimeError, match="finished"):
        getattr(session, method)()


@pytest.mark.parametrize(
    "poison",
    (
        lambda editor: editor._after_key_queue.append(lambda: None),
        lambda editor: editor._background_tasks.append(object()),
        lambda editor: setattr(editor, "_render_requested", True),
    ),
)
def test_core_session_fails_closed_when_quiescence_is_violated(
    poison: Callable[[Editor], None],
) -> None:
    core = _core_module()
    session = core.create_core_editor(
        content="alpha",
        name="fixture.txt",
        columns=40,
        rows=10,
    )
    session.start()
    poison(session._view.editor)

    with pytest.raises(core.CoreEditorNotQuiescent):
        session.observe()
