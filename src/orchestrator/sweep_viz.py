"""L30: sweep visualization — sparkline, text tables, CSV export.

Pure text (no matplotlib/PNG/HTML): ASCII sparkline + markdown/plain
tables + CSV writers for 1D trends and 2D grid sweep results.
"""

from __future__ import annotations

import csv
import math
from typing import Any, Iterable, Sequence

# ascending block elements used for sparklines
_BLOCKS = "▁▂▃▄▅▆▇█"


def sparkline(ys: Sequence[Any]) -> str:
    """Map finite values to a one-char-per-sample block sparkline."""
    vals: list[float] = []
    for y in ys:
        if y is None:
            continue
        try:
            v = float(y)
        except (TypeError, ValueError):
            continue
        if math.isfinite(v):
            vals.append(v)
    if not vals:
        return ""
    lo, hi = min(vals), max(vals)
    span = hi - lo
    if span == 0:
        return _BLOCKS[0] * len(vals)
    last = len(_BLOCKS) - 1
    return "".join(
        _BLOCKS[int(round((v - lo) / span * last))] for v in vals
    )


def _fmt(v: Any) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return f"{f:.6g}"


def render_trend_table(trend: dict | None) -> str:
    """Markdown table of 1D sweep points (x | y) or '' if empty."""
    pts = (trend or {}).get("points") or []
    if not pts:
        return ""
    lines = ["| x | y |", "|---|---|"]
    for p in pts:
        lines.append(f"| {_fmt(p.get('x'))} | {_fmt(p.get('y'))} |")
    return "\n".join(lines)


def render_grid_table(grid: dict | None) -> str:
    """Text matrix of a 2D grid: header 'x\\y' + one line per y row."""
    cells = (grid or {}).get("cells") or []
    finite = [
        c for c in cells
        if c.get("z") is not None and math.isfinite(float(c["z"]))
    ]
    if not finite:
        return ""
    xs = sorted({float(c["x"]) for c in finite})
    ys = sorted({float(c["y"]) for c in finite})
    x_name = str((grid or {}).get("x_name") or "x")
    y_name = str((grid or {}).get("y_name") or "y")
    lookup = {(float(c["x"]), float(c["y"])): float(c["z"]) for c in finite}

    header = f"{x_name}\\{y_name} " + " ".join(_fmt(x) for x in xs)
    lines = [header]
    for y in ys:
        row = [_fmt(lookup.get((x, y), "")) for x in xs]
        lines.append(f"{_fmt(y)} " + " ".join(row))
    return "\n".join(lines)


def write_csv(path: str, rows: Iterable[dict], headers: Sequence[str]) -> str:
    """Write rows as CSV with a fixed header line; create parent dirs."""
    import os

    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(list(headers))
        for r in rows:
            w.writerow([r.get(h, "") for h in headers])
    return path


def render_run_sweep_viz(result: dict) -> str:
    """Viz section for ResearchLoop.run() output: sweep + grid tables."""
    parts: list[str] = []
    for res in result.get("results") or []:
        sw = res.get("sweep") or {}
        if sw.get("points"):
            pts = [p.get("y") for p in sw["points"] if "y" in p]
            sl = sparkline(pts)
            table = render_trend_table(sw)
            if sl or table:
                parts.append("### Sweep viz\n")
                if sl:
                    parts.append(f"`{sl}`\n")
                if table:
                    parts.append(table + "\n")
        g = res.get("grid") or {}
        table_g = render_grid_table(g)
        if table_g:
            parts.append("### Grid viz\n")
            parts.append("```\n" + table_g + "\n```\n")
    return "\n".join(parts)
