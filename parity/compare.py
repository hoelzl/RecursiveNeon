"""Machine-checked comparison of parity snapshots.

Turns a :class:`~parity.harness.ScenarioResult` into per-checkpoint
verdicts so the runner can *fail* on divergences instead of relying on a
human to eyeball the diff report.

Each checkpoint is compared field by field:

- ``body``       — all screen rows above the modeline (right-stripped)
- ``modeline``   — the row above the echo area
- ``echo_area``  — the bottom row
- ``cursor``     — (col, row)

A scenario module may declare a baseline of *expected* divergences::

    EXPECTED_DIVERGENCES = {
        "after-TAB": {"body", "echo_area"},
    }

mapping checkpoint label -> set of field names that are allowed to
differ (the documented deviations from ``docs/PARITY_HARNESS.md``).
Anything beyond the baseline is a failure. A baselined field that no
longer differs is reported as *stale* — a sign the divergence was fixed
and the baseline (and docs) should be updated — but does not fail the
run, since content-dependent diffs (e.g. ``*Help*`` text) can
legitimately come and go across Emacs versions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from parity.harness import ScenarioResult, Snapshot, StepResult

FIELDS = ("body", "modeline", "echo_area", "cursor", "highlights")


@dataclass(frozen=True)
class CheckpointVerdict:
    label: str
    differing: frozenset[str]
    expected: frozenset[str]
    error: str | None = None  # malformed step (e.g. missing target)

    @property
    def unexpected(self) -> frozenset[str]:
        return self.differing - self.expected

    @property
    def stale(self) -> frozenset[str]:
        return self.expected - self.differing

    @property
    def passed(self) -> bool:
        return self.error is None and not self.unexpected

    @property
    def status(self) -> str:
        if self.error is not None:
            return "ERROR"
        if self.unexpected:
            return "FAIL"
        if self.differing:
            return "ALLOWED"
        return "OK"


@dataclass
class ScenarioVerdict:
    name: str
    checkpoints: list[CheckpointVerdict] = field(default_factory=list)
    baseline_errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.baseline_errors and all(
            c.passed for c in self.checkpoints
        )

    @property
    def has_stale(self) -> bool:
        return any(c.stale for c in self.checkpoints)


def diff_fields(
    a: Snapshot, b: Snapshot, *, compare_highlights: bool = False
) -> frozenset[str]:
    """Names of the snapshot fields on which ``a`` and ``b`` differ.

    ``highlights`` (reverse-video / non-default-background runs) is only
    compared when ``compare_highlights`` is set — scenarios opt in via a
    module-level ``COMPARE_HIGHLIGHTS = True``; the suite-wide text-only
    decision stands.
    """
    differing: set[str] = set()
    body_a = [line.rstrip() for line in a.body]
    body_b = [line.rstrip() for line in b.body]
    if body_a != body_b:
        differing.add("body")
    if a.modeline != b.modeline:
        differing.add("modeline")
    if a.echo_area != b.echo_area:
        differing.add("echo_area")
    if a.cursor != b.cursor:
        differing.add("cursor")
    if compare_highlights and a.highlights != b.highlights:
        differing.add("highlights")
    return frozenset(differing)


def _verdict_for_step(
    step: StepResult,
    expected: dict[str, set[str]],
    *,
    compare_highlights: bool = False,
) -> CheckpointVerdict:
    exp = frozenset(expected.get(step.label, set()))
    snaps = list(step.snapshots.values())
    if len(snaps) != 2:
        return CheckpointVerdict(
            label=step.label,
            differing=frozenset(),
            expected=exp,
            error=f"expected 2 targets, got {len(snaps)}",
        )
    return CheckpointVerdict(
        label=step.label,
        differing=diff_fields(
            snaps[0], snaps[1], compare_highlights=compare_highlights
        ),
        expected=exp,
    )


def evaluate(
    result: ScenarioResult,
    expected: dict[str, set[str]] | None = None,
    *,
    compare_highlights: bool = False,
) -> ScenarioVerdict:
    """Evaluate every checkpoint of ``result`` against the baseline."""
    expected = expected or {}
    verdict = ScenarioVerdict(name=result.name)

    labels = {step.label for step in result.steps}
    for label, fields in sorted(expected.items()):
        if label not in labels:
            verdict.baseline_errors.append(
                f"baseline references unknown checkpoint {label!r}"
            )
        bad = set(fields) - set(FIELDS)
        if bad:
            verdict.baseline_errors.append(
                f"baseline for {label!r} has unknown fields: {sorted(bad)}"
            )

    for step in result.steps:
        verdict.checkpoints.append(
            _verdict_for_step(
                step, expected, compare_highlights=compare_highlights
            )
        )
    return verdict


def format_verdict(verdict: ScenarioVerdict) -> str:
    """Compact one-line-per-checkpoint summary."""
    out: list[str] = [f"{verdict.name}:"]
    for err in verdict.baseline_errors:
        out.append(f"  BASELINE ERROR: {err}")
    for cp in verdict.checkpoints:
        line = f"  [{cp.status:>7}] {cp.label}"
        if cp.error:
            line += f" — {cp.error}"
        if cp.unexpected:
            line += f" — unexpected diff in: {', '.join(sorted(cp.unexpected))}"
        elif cp.differing:
            line += f" — allowed diff in: {', '.join(sorted(cp.differing))}"
        if cp.stale:
            line += (
                f" (stale baseline: {', '.join(sorted(cp.stale))}"
                " no longer differs)"
            )
        out.append(line)
    return "\n".join(out)
