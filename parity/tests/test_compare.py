"""Unit tests for the parity comparison/verdict logic.

Run from the repo root::

    .venv/bin/python -m pytest parity/tests -p no:cacheprovider --no-cov

These are pure-Python tests (no pty, no Emacs) so they can run anywhere,
including the CI job that runs the full harness.
"""

from __future__ import annotations

from parity.compare import diff_fields, evaluate, format_verdict
from parity.harness import ScenarioResult, Snapshot, StepResult


def snap(
    body: tuple[str, ...] = ("hello", ""),
    modeline: str = "-UU-:---  F1  f.txt   All   L1    (Text) ---",
    echo: str = "",
    cursor: tuple[int, int] = (0, 0),
) -> Snapshot:
    lines = body + (modeline, echo)
    return Snapshot(
        label="t", lines=lines, cursor=cursor, cols=80, rows=len(lines)
    )


def step(label: str, a: Snapshot, b: Snapshot) -> StepResult:
    s = StepResult(label=label)
    s.snapshots["emacs"] = a
    s.snapshots["neon-edit"] = b
    return s


def scenario(*steps: StepResult) -> ScenarioResult:
    r = ScenarioResult(name="test", description="")
    r.steps.extend(steps)
    return r


class TestDiffFields:
    def test_identical_snapshots_have_no_diff(self):
        assert diff_fields(snap(), snap()) == frozenset()

    def test_body_difference(self):
        assert diff_fields(snap(), snap(body=("bye", ""))) == {"body"}

    def test_trailing_whitespace_in_body_is_ignored(self):
        assert diff_fields(snap(body=("hello   ", "")), snap()) == frozenset()

    def test_modeline_difference(self):
        assert diff_fields(snap(), snap(modeline="other")) == {"modeline"}

    def test_echo_area_difference(self):
        assert diff_fields(snap(), snap(echo="Quit")) == {"echo_area"}

    def test_cursor_difference(self):
        assert diff_fields(snap(), snap(cursor=(2, 0))) == {"cursor"}

    def test_multiple_fields(self):
        got = diff_fields(snap(), snap(body=("x", ""), cursor=(1, 1)))
        assert got == {"body", "cursor"}


class TestEvaluate:
    def test_all_matching_passes(self):
        v = evaluate(scenario(step("a", snap(), snap())))
        assert v.passed
        assert v.checkpoints[0].status == "OK"

    def test_unexpected_divergence_fails(self):
        v = evaluate(scenario(step("a", snap(), snap(echo="x"))))
        assert not v.passed
        assert v.checkpoints[0].status == "FAIL"
        assert v.checkpoints[0].unexpected == {"echo_area"}

    def test_baselined_divergence_is_allowed(self):
        v = evaluate(
            scenario(step("a", snap(), snap(echo="x"))),
            {"a": {"echo_area"}},
        )
        assert v.passed
        assert v.checkpoints[0].status == "ALLOWED"

    def test_partially_baselined_divergence_still_fails(self):
        v = evaluate(
            scenario(step("a", snap(), snap(echo="x", cursor=(3, 3)))),
            {"a": {"echo_area"}},
        )
        assert not v.passed
        assert v.checkpoints[0].unexpected == {"cursor"}

    def test_stale_baseline_is_reported_but_passes(self):
        v = evaluate(
            scenario(step("a", snap(), snap())), {"a": {"echo_area"}}
        )
        assert v.passed
        assert v.has_stale
        assert v.checkpoints[0].stale == {"echo_area"}

    def test_unknown_checkpoint_in_baseline_fails(self):
        v = evaluate(scenario(step("a", snap(), snap())), {"typo": {"body"}})
        assert not v.passed
        assert any("typo" in e for e in v.baseline_errors)

    def test_unknown_field_in_baseline_fails(self):
        v = evaluate(
            scenario(step("a", snap(), snap())), {"a": {"minibuffer"}}
        )
        assert not v.passed
        assert any("minibuffer" in e for e in v.baseline_errors)

    def test_missing_target_is_error(self):
        s = StepResult(label="a")
        s.snapshots["emacs"] = snap()
        v = evaluate(scenario(s))
        assert not v.passed
        assert v.checkpoints[0].status == "ERROR"


class TestFormatVerdict:
    def test_mentions_unexpected_fields(self):
        v = evaluate(scenario(step("cp1", snap(), snap(echo="x"))))
        text = format_verdict(v)
        assert "FAIL" in text
        assert "cp1" in text
        assert "echo_area" in text

    def test_mentions_stale_baseline(self):
        v = evaluate(
            scenario(step("cp1", snap(), snap())), {"cp1": {"cursor"}}
        )
        assert "stale" in format_verdict(v)
