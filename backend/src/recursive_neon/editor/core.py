"""Deterministic, framework-neutral session for the core editor profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal, TypedDict

from recursive_neon.editor.core_commands import (
    build_core_commands,
    build_core_keymap,
)
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.modes import build_core_modes
from recursive_neon.editor.variables import build_core_variables
from recursive_neon.editor.view import EditorView
from recursive_neon.shell.tui import ScreenBuffer


class CoreEditorNotQuiescent(RuntimeError):
    """Raised when a core operation leaves asynchronous work pending."""


CoreEditorFinishReason = Literal["exit", "stop", "abort"]


class EditorPositionV1Dict(TypedDict):
    """JSON object for a zero-based editor position."""

    line: int
    column: int


class EditorObservationV1Dict(TypedDict):
    """Typed JSON representation returned by :meth:`EditorObservationV1.to_dict`."""

    schema_version: Literal[1]
    buffer_name: str
    text: str
    point: EditorPositionV1Dict
    mark: EditorPositionV1Dict | None
    mark_active: bool
    modified: bool
    read_only: bool
    major_mode: str | None
    minor_modes: list[str]
    message: str
    running: bool
    buffer_names: list[str]
    minibuffer_active: bool
    minibuffer_prompt: str
    minibuffer_text: str
    active_window_buffer: str
    visible_start_line: int
    visible_end_line: int


def _validate_geometry(columns: int, rows: int) -> None:
    if columns <= 0:
        raise ValueError("columns must be positive")
    if rows < 3:
        raise ValueError("rows must be at least 3")


@dataclass(frozen=True)
class CoreEditorPosition:
    """Zero-based line and column position."""

    line: int
    column: int


@dataclass(frozen=True)
class EditorObservationV1:
    """Stable semantic editor observation, schema version 1."""

    schema_version: ClassVar[Literal[1]] = 1
    buffer_name: str
    text: str
    point: CoreEditorPosition
    mark: CoreEditorPosition | None
    mark_active: bool
    modified: bool
    read_only: bool
    major_mode: str | None
    minor_modes: tuple[str, ...]
    message: str
    running: bool
    buffer_names: tuple[str, ...]
    minibuffer_active: bool
    minibuffer_prompt: str
    minibuffer_text: str
    active_window_buffer: str
    visible_start_line: int
    visible_end_line: int

    def to_dict(self) -> EditorObservationV1Dict:
        """Return the stable JSON-shaped representation of schema version 1."""
        return {
            "schema_version": 1,
            "buffer_name": self.buffer_name,
            "text": self.text,
            "point": _position_to_dict(self.point),
            "mark": _position_to_dict(self.mark) if self.mark is not None else None,
            "mark_active": self.mark_active,
            "modified": self.modified,
            "read_only": self.read_only,
            "major_mode": self.major_mode,
            "minor_modes": list(self.minor_modes),
            "message": self.message,
            "running": self.running,
            "buffer_names": list(self.buffer_names),
            "minibuffer_active": self.minibuffer_active,
            "minibuffer_prompt": self.minibuffer_prompt,
            "minibuffer_text": self.minibuffer_text,
            "active_window_buffer": self.active_window_buffer,
            "visible_start_line": self.visible_start_line,
            "visible_end_line": self.visible_end_line,
        }


def _position_to_dict(position: CoreEditorPosition) -> EditorPositionV1Dict:
    return {"line": position.line, "column": position.column}


@dataclass(frozen=True)
class CoreEditorFrame:
    """Immutable complete terminal frame produced by the editor view."""

    columns: int
    rows: int
    lines: tuple[str, ...]
    cursor: CoreEditorPosition
    cursor_visible: bool


@dataclass(frozen=True)
class CoreEditorStep:
    """Semantic state and complete frame at one quiescent epoch."""

    observation: EditorObservationV1
    frame: CoreEditorFrame


@dataclass(frozen=True)
class CoreEditorFinished:
    """Final semantic state and last complete frame for a finished session."""

    observation: EditorObservationV1
    frame: CoreEditorFrame
    reason: CoreEditorFinishReason


class _CoreEditorView(EditorView):
    """Editor view with timed integration behavior structurally disabled."""

    @property
    def tick_interval_ms(self) -> int:
        return 0


class CoreEditorSession:
    """Drive a deterministic core editor without a terminal runner."""

    def __init__(
        self,
        *,
        content: str,
        name: str,
        columns: int,
        rows: int,
    ) -> None:
        _validate_geometry(columns, rows)
        editor = Editor(
            global_keymap=build_core_keymap(),
            commands=build_core_commands(),
            modes=build_core_modes(),
            variables=build_core_variables(),
        )
        editor.create_buffer(name=name, text=content)
        self._view = _CoreEditorView(editor)
        self._columns = columns
        self._rows = rows
        self._screen: ScreenBuffer | None = None
        self._started = False
        self._finished = False

    def start(self) -> CoreEditorStep:
        """Start once and return the initial quiescent epoch."""
        if self._started:
            raise RuntimeError("core editor session has already started")
        self._started = True
        self._screen = self._view.on_start(self._columns, self._rows)
        return self._step()

    def send_key(self, key: str) -> CoreEditorStep | CoreEditorFinished:
        """Dispatch one canonical editor key and return its completed epoch."""
        self._ensure_active()
        screen = self._view.on_key(key)
        if screen is None:
            return self._finish("exit")
        self._screen = screen
        return self._step()

    def resize(self, *, columns: int, rows: int) -> CoreEditorStep:
        """Resize the core terminal and return its completed epoch."""
        self._ensure_active()
        _validate_geometry(columns, rows)
        self._columns = columns
        self._rows = rows
        self._screen = self._view.on_resize(columns, rows)
        return self._step()

    def observe(self) -> CoreEditorStep:
        """Return the latest immutable state and frame without advancing."""
        if not self._started:
            raise RuntimeError("core editor session has not started")
        return self._step()

    def stop(self) -> CoreEditorFinished:
        """Finish the session normally without dispatching another key."""
        self._ensure_active()
        self._view.editor.quit()
        return self._finish("stop")

    def abort(self) -> CoreEditorFinished:
        """Finish the session as aborted without dispatching another key."""
        self._ensure_active()
        self._view.editor.quit()
        return self._finish("abort")

    def _ensure_active(self) -> None:
        if not self._started:
            raise RuntimeError("core editor session has not started")
        if self._finished:
            raise RuntimeError("core editor session has finished")

    def _finish(self, reason: CoreEditorFinishReason) -> CoreEditorFinished:
        self._finished = True
        step = self._step()
        return CoreEditorFinished(
            observation=step.observation,
            frame=step.frame,
            reason=reason,
        )

    def _step(self) -> CoreEditorStep:
        self._assert_quiescent()
        assert self._screen is not None
        editor = self._view.editor
        buffer = editor.buffer
        mark = buffer.mark
        minibuffer = editor.minibuffer
        active_window = self._view._tree.active
        observation = EditorObservationV1(
            buffer_name=buffer.name,
            text=buffer.text,
            point=CoreEditorPosition(buffer.point.line, buffer.point.col),
            mark=(
                CoreEditorPosition(mark.line, mark.col) if mark is not None else None
            ),
            mark_active=buffer.mark_active,
            modified=buffer.modified,
            read_only=buffer.read_only,
            major_mode=(
                buffer.major_mode.name if buffer.major_mode is not None else None
            ),
            minor_modes=tuple(mode.name for mode in buffer.minor_modes),
            message=editor.message,
            running=editor.running,
            buffer_names=tuple(item.name for item in editor.buffers),
            minibuffer_active=minibuffer is not None,
            minibuffer_prompt=minibuffer.prompt if minibuffer is not None else "",
            minibuffer_text=minibuffer.text if minibuffer is not None else "",
            active_window_buffer=active_window.buffer.name,
            visible_start_line=active_window.scroll_top,
            visible_end_line=min(
                len(active_window.buffer.lines),
                active_window.scroll_top + active_window.text_height,
            ),
        )
        frame = CoreEditorFrame(
            columns=self._screen.width,
            rows=self._screen.height,
            lines=tuple(self._screen.lines),
            cursor=CoreEditorPosition(
                self._screen.cursor_row,
                self._screen.cursor_col,
            ),
            cursor_visible=self._screen.cursor_visible,
        )
        return CoreEditorStep(observation=observation, frame=frame)

    def _assert_quiescent(self) -> None:
        editor = self._view.editor
        if (
            self._view.tick_interval_ms != 0
            or editor._after_key_queue
            or editor._background_tasks
            or editor._render_requested
        ):
            raise CoreEditorNotQuiescent(
                "core editor did not reach synchronous quiescence"
            )


def create_core_editor(
    *,
    content: str,
    name: str,
    columns: int,
    rows: int,
) -> CoreEditorSession:
    """Create an unstarted deterministic core editor session."""
    return CoreEditorSession(
        content=content,
        name=name,
        columns=columns,
        rows=rows,
    )
