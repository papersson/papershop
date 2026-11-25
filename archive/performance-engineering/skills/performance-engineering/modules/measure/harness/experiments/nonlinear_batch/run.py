"""Attack NONLINEAR-BATCH-AMORTIZATION: is the per-op headline a batch artifact?

Run from the repo root:  uv run python experiments/nonlinear_batch/run.py

Reuses the spine READ-ONLY: it calls ``core._time_batch`` / ``core.run_suite``,
``stats.aggregate``, ``report.plot_scaling`` / ``format_table`` unchanged. No
spine edit -- C1 preserved.

Part 2  Controlled fixed-batch sweep. For each workload, measure at a FIXED batch
        B in BATCH_GRID, repetitions interleaved/randomized, value = elapsed/B,
        params={"batch_probe": B}. Feed through the unchanged aggregate(); the
        falsifiable prediction is seconds_per_op(B) varies monotonically with B by
        more than the per-B bootstrap CI bands.

Part 3  Knob sweep. Run run_suite on the SAME operations with min_batch_time in
        KNOB_GRID; record the calibrated batch and the median seconds_per_op for
        each. The prediction is the headline median shifts >~1.5x as the knob
        changes -- while the correctness gate passes every time (the op is
        byte-identical).
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import target  # noqa: E402

from harness.core import _time_batch, run_suite  # noqa: E402
from harness.report import format_table, plot_scaling  # noqa: E402
from harness.stats import aggregate  # noqa: E402

RESULTS = Path(__file__).resolve().parents[2] / "results" / "nonlinear_batch"

REPS_SWEEP = 40
WARMUP_SWEEP = 3


def controlled_batch_sweep() -> list[dict]:
    """Part 2: measure each workload at fixed batches, interleaved across reps."""
    rng = random.Random(1234)

    # Build one cell per (probe, batch). Fixture prepared once (untimed), warmed.
    cells = []
    for probe in target.sweep_probes:
        fixture = probe.prepare({"batch_probe": 0})
        for b in target.BATCH_GRID:
            for _ in range(WARMUP_SWEEP):
                _time_batch(probe.invoke, fixture, b)
            cells.append((probe, fixture, b))

    samples: list[dict] = []
    order = list(range(len(cells)))
    for rep in range(REPS_SWEEP):
        rng.shuffle(order)
        for idx in order:
            probe, fixture, b = cells[idx]
            elapsed = _time_batch(probe.invoke, fixture, b)
            samples.append(
                {
                    "probe": probe.name,
                    "params": {"batch_probe": b},
                    "rep": rep,
                    "batch": b,
                    "seconds_per_op": elapsed / b,
                }
            )
    return samples


def knob_sweep() -> tuple[list[dict], bool, list[str]]:
    """Part 3: run_suite per gate-set per knob; record batch + median headline."""
    rows: list[dict] = []
    gate_passed = True
    gate_log: list[str] = []

    for label, probes, param_grid in target.gate_sets:
        for knob in target.KNOB_GRID:
            try:
                samples = run_suite(
                    probes,
                    param_grid,
                    min_batch_time=knob,
                    warmup=3,
                    repetitions=20,
                    seed=99,
                )
            except ValueError as e:
                gate_passed = False
                gate_log.append(f"{label} knob={knob}: GATE FAILED: {e}")
                continue
            gate_log.append(f"{label} knob={knob}: gate PASS ({len(probes)} probes agree)")
            summ = aggregate(samples)
            for s in summ:
                rows.append(
                    {
                        "workload": label,
                        "probe": s["probe"],
                        "min_batch_time": knob,
                        "calibrated_batch": next(
                            x["batch"] for x in samples if x["probe"] == s["probe"]
                        ),
                        "median_seconds_per_op": s["median"],
                        "ci_low": s["ci_low"],
                        "ci_high": s["ci_high"],
                    }
                )
    return rows, gate_passed, gate_log


def _by_probe(stats: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in stats:
        out.setdefault(r["probe"], []).append(r)
    for rows in out.values():
        rows.sort(key=lambda r: r["params"]["batch_probe"])
    return out


def analyse_sweep(stats: list[dict]) -> dict:
    """Per workload: B=1 vs B=max ratio, CI-disjointness, monotonicity."""
    findings = {}
    for probe, rows in _by_probe(stats).items():
        first, last = rows[0], rows[-1]
        ratio = first["median"] / last["median"]
        # disjoint CIs => the change exceeds the bootstrap bands
        ci_disjoint = first["ci_low"] > last["ci_high"] or last["ci_low"] > first["ci_high"]
        medians = [r["median"] for r in rows]
        # monotone non-increasing within a small tolerance (overhead amortizes down)
        monotone_down = all(
            medians[i + 1] <= medians[i] * 1.02 for i in range(len(medians) - 1)
        )
        # how much of the change is beyond the typical CI width
        typ_ci_width = sum(r["ci_high"] - r["ci_low"] for r in rows) / len(rows)
        findings[probe] = {
            "B_min": first["params"]["batch_probe"],
            "B_max": last["params"]["batch_probe"],
            "median_at_Bmin": first["median"],
            "median_at_Bmax": last["median"],
            "ratio_Bmin_over_Bmax": ratio,
            "abs_change": first["median"] - last["median"],
            "typical_ci_width": typ_ci_width,
            "change_over_ci_width": (first["median"] - last["median"]) / typ_ci_width,
            "ci_disjoint_Bmin_Bmax": ci_disjoint,
            "monotone_decreasing": monotone_down,
        }
    return findings


def analyse_knob(rows: list[dict]) -> dict:
    findings = {}
    by_probe: dict[str, list[dict]] = {}
    for r in rows:
        by_probe.setdefault(r["probe"], []).append(r)
    for probe, rs in by_probe.items():
        rs.sort(key=lambda r: r["min_batch_time"])
        meds = [r["median_seconds_per_op"] for r in rs]
        findings[probe] = {
            "workload": rs[0]["workload"],
            "knobs": [r["min_batch_time"] for r in rs],
            "calibrated_batches": [r["calibrated_batch"] for r in rs],
            "medians": meds,
            "headline_max_over_min": max(meds) / min(meds),
        }
    return findings


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)

    # ---- Part 2: controlled fixed-batch sweep -------------------------------
    samples = controlled_batch_sweep()
    (RESULTS / "raw_samples.json").write_text(json.dumps(samples, indent=2))

    stats = aggregate(samples)  # spine, unchanged
    (RESULTS / "stats.json").write_text(json.dumps(stats, indent=2))

    plot_scaling(
        stats,
        "batch_probe",
        out_path=RESULTS / "seconds_per_op_vs_batch.png",
        title="seconds_per_op vs fixed batch B (LIBRARY regime)",
        x_label="fixed batch size B (timed iterations)",
        per_call_label="op",
    )

    sweep_findings = analyse_sweep(stats)

    # ---- Part 3: knob sweep -------------------------------------------------
    knob_rows, gate_passed, gate_log = knob_sweep()
    knob_findings = analyse_knob(knob_rows)

    # ---- verdict ------------------------------------------------------------
    # Conjunct (a): per-op varies monotonically with B beyond the CI bands.
    conj_a = any(
        f["ci_disjoint_Bmin_Bmax"] and f["ratio_Bmin_over_Bmax"] > 1.5
        for f in sweep_findings.values()
    )
    # Conjunct (b): the run_suite headline shifts >1.5x across the knob.
    conj_b = any(f["headline_max_over_min"] > 1.5 for f in knob_findings.values())

    if conj_a and conj_b and gate_passed:
        verdict = "REFUTED (per-op is a batch+knob artifact; gate still passes)"
    elif conj_a and not conj_b and gate_passed:
        verdict = (
            "PARTIAL/SCOPED: per-op IS batch-dependent at small fixed B (naive "
            "batch-invariance false), BUT min_batch_time calibration self-amortizes "
            "so the run_suite HEADLINE is stable across the knob -- calibration "
            "defends elapsed/N"
        )
    elif not conj_a:
        verdict = "CONFIRMED (elapsed/N flat within CI across B and stable across knob)"
    else:
        verdict = "MIXED -- see findings"

    findings = {
        "spine_changed": False,
        "correctness_gate_passed": gate_passed,
        "gate_log": gate_log,
        "conjunct_a_perop_varies_with_B_beyond_CI": conj_a,
        "conjunct_b_headline_shifts_across_knob": conj_b,
        "verdict": verdict,
        "part2_fixed_batch_sweep": sweep_findings,
        "part3_knob_sweep": knob_findings,
        "knob_rows": knob_rows,
    }
    (RESULTS / "findings.json").write_text(json.dumps(findings, indent=2))

    # ---- console report -----------------------------------------------------
    print("=== Part 2: controlled fixed-batch sweep ===")
    print(format_table(stats, x_key="batch_probe"))
    print()
    for probe, f in sweep_findings.items():
        print(
            f"  {probe:5s}  B={f['B_min']}->{f['B_max']}  "
            f"median {f['median_at_Bmin']*1e9:,.1f}ns -> {f['median_at_Bmax']*1e9:,.1f}ns  "
            f"ratio={f['ratio_Bmin_over_Bmax']:.2f}x  "
            f"change/CIwidth={f['change_over_ci_width']:.1f}  "
            f"CI-disjoint={f['ci_disjoint_Bmin_Bmax']}  "
            f"monotone_down={f['monotone_decreasing']}"
        )

    print("\n=== Part 3: knob sweep (run_suite, gate active) ===")
    for line in gate_log:
        print("  " + line)
    for probe, f in knob_findings.items():
        print(
            f"  {probe:10s} ({f['workload']})  "
            f"batches={f['calibrated_batches']}  "
            f"medians(ns)={[round(m*1e9,1) for m in f['medians']]}  "
            f"headline max/min={f['headline_max_over_min']:.3f}x"
        )

    print(f"\nCORRECTNESS GATE: {'PASS' if gate_passed else 'FAIL'}")
    print(f"conjunct a (per-op varies with B beyond CI): {conj_a}")
    print(f"conjunct b (headline shifts >1.5x across knob): {conj_b}")
    print(f"VERDICT: {verdict}")
    print(f"\nArtifacts -> {RESULTS}/")
    print("  raw_samples.json  stats.json  seconds_per_op_vs_batch.png  findings.json")


if __name__ == "__main__":
    main()
