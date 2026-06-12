"""Tests for the opt-in highlight capture and comparison.

``Snapshot.highlights`` records (row, start, end_exclusive) runs of
cells with reverse video or a non-default background; ``diff_fields``
only consults them when ``compare_highlights`` is set.
"""

from __future__ import annotations

import pyte

from parity.compare import diff_fields, evaluate
from parity.harness import ScenarioResult, Snapshot, StepResult, capture_highlights


def screen_with(data: bytes, cols: int = 20, rows: int = 3) -> pyte.Screen:
    screen = pyte.Screen(cols, rows)
    pyte.ByteStream(screen).feed(data)
    return screen


def snap(label: str = "s", **kw) -> Snapshot:
    defaults = dict(
        lines=("a", "m", "e"),
        cursor=(0, 0),
        cols=20,
        rows=3,
        highlights=(),
    )
    defaults.update(kw)
    return Snapshot(label=label, **defaults)


class TestCaptureHighlights:
    def test_plain_screen_has_no_runs(self) -> None:
        screen = screen_with(b"hello")
        assert capture_highlights(screen) == ()

    def test_reverse_video_run(self) -> None:
        screen = screen_with(b"ab\x1b[7mCD\x1b[0mef")
        assert capture_highlights(screen) == ((0, 2, 4),)

    def test_background_color_run(self) -> None:
        screen = screen_with(b"\x1b[44mXY\x1b[0mz")
        assert capture_highlights(screen) == ((0, 0, 2),)

    def test_foreground_color_is_ignored(self) -> None:
        # Syntax highlighting (fg-only) must not register.
        screen = screen_with(b"\x1b[31mred\x1b[0m")
        assert capture_highlights(screen) == ()

    def test_run_to_end_of_row(self) -> None:
        screen = screen_with(b"\x1b[7m" + b"x" * 20)
        assert capture_highlights(screen) == ((0, 0, 20),)

    def test_runs_on_multiple_rows(self) -> None:
        screen = screen_with(b"\x1b[7mA\x1b[0m\r\n\x1b[7mB\x1b[0m")
        assert capture_highlights(screen) == ((0, 0, 1), (1, 0, 1))


class TestOptInComparison:
    def test_highlights_ignored_by_default(self) -> None:
        a = snap(highlights=((0, 0, 3),))
        b = snap(highlights=())
        assert diff_fields(a, b) == frozenset()

    def test_highlights_compared_when_opted_in(self) -> None:
        a = snap(highlights=((0, 0, 3),))
        b = snap(highlights=())
        assert diff_fields(a, b, compare_highlights=True) == frozenset(
            {"highlights"}
        )

    def test_equal_highlights_pass_when_opted_in(self) -> None:
        a = snap(highlights=((1, 2, 5),))
        b = snap(highlights=((1, 2, 5),))
        assert diff_fields(a, b, compare_highlights=True) == frozenset()

    def test_evaluate_threads_the_flag(self) -> None:
        step = StepResult(label="cp")
        step.snapshots["emacs"] = snap(highlights=((0, 0, 1),))
        step.snapshots["neon"] = snap(highlights=())
        result = ScenarioResult(name="t", description="d", steps=[step])
        assert evaluate(result).passed
        verdict = evaluate(result, compare_highlights=True)
        assert not verdict.passed
        assert verdict.checkpoints[0].unexpected == frozenset({"highlights"})

    def test_highlights_baseline_field_is_valid(self) -> None:
        step = StepResult(label="cp")
        step.snapshots["emacs"] = snap(highlights=((0, 0, 1),))
        step.snapshots["neon"] = snap(highlights=())
        result = ScenarioResult(name="t", description="d", steps=[step])
        verdict = evaluate(
            result, {"cp": {"highlights"}}, compare_highlights=True
        )
        assert verdict.passed
        assert not verdict.baseline_errors
