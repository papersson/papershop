"""The reporter: statistics in, plots and tables out.

It reads only the summary schema from ``stats`` — it never reaches back into
the runner or the probe. That one-way dependency is what lets you add a new plot
or a new output format without touching how anything is measured.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # headless: render to a file, never to a window
import matplotlib.pyplot as plt  # noqa: E402


def plot_scaling(stats, x_key, *, out_path, title, x_label, per_call_label="call"):
    """Plot median time vs an input parameter, one line per probe, with CI bands.

    Both axes are logarithmic, which is the standard view for scaling: a
    straight line then reveals the growth order (flat = constant, 45-degree =
    linear, and so on).
    """
    # Defensive (additive): co-plotting lines that are in different units puts
    # incommensurable numbers on one axis. Refuse, rather than draw a lie. Rows
    # without a `unit` are legacy time summaries and plot as before.
    units = {row.get("unit", "seconds") for row in stats}
    if len(units) > 1:
        raise ValueError(
            f"refusing to co-plot mismatched units on one axis: {sorted(units)}"
        )

    by_probe: dict[str, list[dict]] = {}
    for row in stats:
        by_probe.setdefault(row["probe"], []).append(row)

    fig, ax = plt.subplots(figsize=(8, 5))
    for probe, rows in sorted(by_probe.items()):
        rows = sorted(rows, key=lambda r: r["params"][x_key])
        xs = [r["params"][x_key] for r in rows]
        ys = [r["median"] * 1e9 for r in rows]
        lo = [r["ci_low"] * 1e9 for r in rows]
        hi = [r["ci_high"] * 1e9 for r in rows]
        line, = ax.plot(xs, ys, marker="o", label=probe)
        ax.fill_between(xs, lo, hi, alpha=0.2, color=line.get_color())

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(x_label)
    ax.set_ylabel(f"median time per {per_call_label} (ns)")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, which="both", ls=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def format_table(stats, x_key="n") -> str:
    """A compact text table of the summary, sorted by probe then input size."""
    rows = sorted(stats, key=lambda r: (r["probe"], r["params"].get(x_key, 0)))
    header = (
        f"{'probe':<14}{x_key:>9}{'median(ns)':>15}{'p99(ns)':>15}"
        f"{'95% CI median (ns)':>28}{'95% CI p99 (ns)':>28}"
    )
    lines = [header, "-" * len(header)]
    for r in rows:
        med_ci = f"[{r['ci_low'] * 1e9:,.0f}, {r['ci_high'] * 1e9:,.0f}]"
        # Band the p99 with the p99's own CI — never the median's (tail-CI rule).
        # Older summaries without p99 bands fall back to a blank cell.
        if "p99_ci_low" in r:
            p99_ci = f"[{r['p99_ci_low'] * 1e9:,.0f}, {r['p99_ci_high'] * 1e9:,.0f}]"
        else:
            p99_ci = "-"
        lines.append(
            f"{r['probe']:<14}{r['params'][x_key]:>9,}"
            f"{r['median'] * 1e9:>15,.0f}{r['p99'] * 1e9:>15,.0f}"
            f"{med_ci:>28}{p99_ci:>28}"
        )
    return "\n".join(lines)
