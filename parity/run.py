"""Run one or more parity scenarios and assert on the results.

Usage::

    python -m parity.run              # run all scenarios, assert, exit 0/1
    python -m parity.run 01           # run scenarios matching '01'
    python -m parity.run --list      # list available scenarios
    python -m parity.run --report    # also print full diff reports for
                                      # passing checkpoints

Each scenario module exposes ``run() -> ScenarioResult`` and module-level
``NAME``/``DESCRIPTION``, plus an optional ``EXPECTED_DIVERGENCES``
baseline (checkpoint label -> set of snapshot fields allowed to differ —
the documented deviations from ``docs/PARITY_HARNESS.md``). A scenario
lives under ``parity/scenarios/scenario_NN_*.py``.

A checkpoint that differs outside its baseline fails the run (exit 1).
The full side-by-side diff is always printed for failing scenarios so
the divergence can be inspected without a re-run.
"""

from __future__ import annotations

import argparse
import importlib
import pkgutil
import subprocess
import sys
from typing import Iterable

from parity import scenarios as scenarios_pkg
from parity.compare import evaluate, format_verdict
from parity.report import format_report
from parity.targets import emacs_binary


def _discover() -> list[str]:
    return sorted(
        m.name
        for m in pkgutil.iter_modules(scenarios_pkg.__path__)
        if m.name.startswith("scenario_")
    )


def _load(module_name: str):
    return importlib.import_module(f"parity.scenarios.{module_name}")


def _select(patterns: Iterable[str]) -> list[str]:
    all_mods = _discover()
    if not patterns:
        return all_mods
    selected: list[str] = []
    for pat in patterns:
        for name in all_mods:
            if pat in name and name not in selected:
                selected.append(name)
    return selected


def _emacs_version() -> str:
    try:
        out = subprocess.run(
            [emacs_binary(), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
        return out.splitlines()[0] if out else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("patterns", nargs="*", help="substring filter")
    parser.add_argument(
        "--list", action="store_true", help="list scenarios and exit"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="print full diff reports even for passing scenarios",
    )
    args = parser.parse_args(argv)

    if args.list:
        for name in _discover():
            mod = _load(name)
            print(f"  {name}: {getattr(mod, 'DESCRIPTION', '')}")
        return 0

    names = _select(args.patterns)
    if not names:
        print("No scenarios match.", file=sys.stderr)
        return 2

    print(f"Ground truth: {_emacs_version()}")
    print()

    verdicts = []
    for name in names:
        mod = _load(name)
        result = mod.run()
        expected = getattr(mod, "EXPECTED_DIVERGENCES", {})
        verdict = evaluate(
            result,
            expected,
            compare_highlights=getattr(mod, "COMPARE_HIGHLIGHTS", False),
        )
        verdicts.append(verdict)
        print(format_verdict(verdict))
        if args.report or not verdict.passed:
            print()
            print(format_report(result))
        print()

    failed = [v.name for v in verdicts if not v.passed]
    stale = [v.name for v in verdicts if v.has_stale]
    total = sum(len(v.checkpoints) for v in verdicts)
    print(
        f"Summary: {len(verdicts)} scenario(s), {total} checkpoint(s), "
        f"{len(failed)} failing."
    )
    if stale:
        print(
            "Stale baselines (documented divergence no longer occurs — "
            f"update the scenario + docs): {', '.join(stale)}"
        )
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
