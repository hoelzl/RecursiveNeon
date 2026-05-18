"""Run one or more parity scenarios and print a diff report.

Usage::

    python -m parity.run              # run all scenarios
    python -m parity.run 01           # run scenarios matching '01'
    python -m parity.run --list       # list available scenarios

Each scenario module exposes ``run() -> ScenarioResult`` and module-level
``NAME``/``DESCRIPTION``. A scenario lives under
``parity/scenarios/scenario_NN_*.py``.
"""

from __future__ import annotations

import argparse
import importlib
import pkgutil
import sys
from typing import Iterable

from parity import scenarios as scenarios_pkg
from parity.report import format_report


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("patterns", nargs="*", help="substring filter")
    parser.add_argument(
        "--list", action="store_true", help="list scenarios and exit"
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

    for name in names:
        mod = _load(name)
        result = mod.run()
        print(format_report(result))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
