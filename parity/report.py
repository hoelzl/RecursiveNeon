"""Render a side-by-side diff report for a :class:`ScenarioResult`."""

from __future__ import annotations

from parity.harness import ScenarioResult, Snapshot


def format_report(result: ScenarioResult) -> str:
    out: list[str] = []
    out.append(f"# Scenario: {result.name}")
    out.append("")
    out.append(result.description)
    out.append("")
    for step in result.steps:
        out.append(f"## Step: {step.label}")
        out.append("")
        targets = list(step.snapshots.keys())
        if len(targets) != 2:
            out.append(f"(expected 2 targets, got {len(targets)}: {targets})")
            continue
        a, b = targets
        snap_a, snap_b = step.snapshots[a], step.snapshots[b]
        out.append(_side_by_side(a, snap_a, b, snap_b))
        out.append("")
        out.append("### Structured fields")
        out.append("")
        out.append(_kv_diff("modeline", snap_a.modeline, snap_b.modeline, a, b))
        out.append(
            _kv_diff("echo_area", snap_a.echo_area, snap_b.echo_area, a, b)
        )
        out.append(
            _kv_diff(
                "cursor",
                f"col={snap_a.cursor[0]} row={snap_a.cursor[1]}",
                f"col={snap_b.cursor[0]} row={snap_b.cursor[1]}",
                a,
                b,
            )
        )
        out.append("")
        out.append("### Differences (body, line by line)")
        out.append("")
        out.append(_line_diff(snap_a, snap_b, a, b))
        out.append("")
    return "\n".join(out)


def _side_by_side(name_a: str, sa: Snapshot, name_b: str, sb: Snapshot) -> str:
    width = sa.cols
    header = f"{name_a:<{width}}  | {name_b:<{width}}"
    sep = "-" * width + "--+-" + "-" * width
    lines = [header, sep]
    rows = max(len(sa.lines), len(sb.lines))
    for i in range(rows):
        la = sa.lines[i] if i < len(sa.lines) else ""
        lb = sb.lines[i] if i < len(sb.lines) else ""
        marker = "  " if la == lb else "!="
        lines.append(f"{la:<{width}} {marker}| {lb:<{width}}")
    return "```\n" + "\n".join(lines) + "\n```"


def _kv_diff(name: str, va: str, vb: str, na: str, nb: str) -> str:
    if va == vb:
        return f"- {name}: same\n    `{va}`"
    return (
        f"- {name}: DIFFERS\n"
        f"    {na:<10}: `{va}`\n"
        f"    {nb:<10}: `{vb}`"
    )


def _line_diff(sa: Snapshot, sb: Snapshot, na: str, nb: str) -> str:
    out: list[str] = []
    n = max(len(sa.lines), len(sb.lines))
    for i in range(n):
        la = sa.lines[i].rstrip() if i < len(sa.lines) else ""
        lb = sb.lines[i].rstrip() if i < len(sb.lines) else ""
        if la == lb:
            continue
        out.append(f"  row {i:2d}:")
        out.append(f"    {na:<10}: {la!r}")
        out.append(f"    {nb:<10}: {lb!r}")
    if not out:
        return "_(no row differs)_"
    return "\n".join(out)
