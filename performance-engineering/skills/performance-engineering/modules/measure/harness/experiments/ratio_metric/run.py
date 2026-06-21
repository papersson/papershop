"""Ratio-of-totals estimator trap (claim RATIO-METRIC-ESTIMATOR).

Run from the repo root:  uv run python experiments/ratio_metric/run.py

A pure-statistics experiment. It touches NO spine files: it feeds synthetic
throughput raw_samples (in the load-bearing schema, value = per-window rate)
straight into the UNMODIFIED ``harness.stats.aggregate`` and asks:

    The headline is a ratio of totals, R* = sum(num)/sum(den). The schema's
    single scalar slot forces us to feed per-window rates (num_i/den_i). Does the
    spine's median/mean of those rates, and its bootstrap CI, recover R* when
    window denominators vary and correlate with rate?

We answer empirically. One representative dataset shows the point/interval error;
a 300-trial coverage study (fresh seed per trial) measures how often the spine's
median CI covers R* versus a paired (num,den) window-resample bootstrap that
recomputes the ratio of totals directly.

Correctness/validity gate: before trusting any number we verify (a) the spine,
run unchanged, reproduces an independent local median and median-CI of the rate
list, and (b) the experiment's paired bootstrap point estimate equals the direct
sum(num)/sum(den). If either fails the comparison is void.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import target  # same directory; on sys.path because this file is the entrypoint

from harness.stats import aggregate, bootstrap_ci_median

RESULTS = Path(__file__).resolve().parents[2] / "results" / "ratio_metric"

# --- experiment knobs (kept modest: runs in well under two minutes) -------
TRIALS = 300  # independent datasets in the coverage study
BOOT_ITERS = 2000  # paired-bootstrap iters (aggregate uses its own 2000 default)
REF_TRIALS = 20000  # huge resample to cross-check the closed-form R*
BASE_SEED = 20260620
REP_SEED = 0  # the single "representative" dataset (plan step 3)


def covers(lo: float, hi: float, value: float) -> bool:
    return lo <= value <= hi


def validity_gate() -> dict:
    """Confirm the spine reproduces an independent computation, and the reference
    paired estimator equals the direct ratio of totals. Guards everything below.
    """
    windows = target.generate_windows(REP_SEED)
    samples = target.make_raw_samples(windows, probe="throughput", params={"point": 0})

    summary = aggregate(samples)
    assert len(summary) == 1, "expected exactly one probe/param group"
    row = summary[0]

    rates = [w["rate"] for w in windows]
    ref_median = statistics.median(rates)
    ref_lo, ref_hi = bootstrap_ci_median(rates)  # same defaults aggregate uses

    # The spine must reproduce the independent median / median-CI of the rates.
    spine_checks = {
        "median": (row["median"], ref_median),
        "ci_low": (row["ci_low"], ref_lo),
        "ci_high": (row["ci_high"], ref_hi),
    }
    spine_mismatches = {
        k: {"spine": a, "reference": b}
        for k, (a, b) in spine_checks.items()
        if abs(a - b) > 1e-15
    }

    # The reference paired estimator's point must equal the direct ratio of
    # totals (the estimator the experiment claims to implement).
    paired_lo, paired_hi = target.paired_bootstrap_ci_ratio(windows, iters=BOOT_ITERS)
    direct = target.ratio_of_totals(windows)
    paired_point_ok = paired_lo <= direct <= paired_hi  # point lies inside its own CI

    # And the spine genuinely ignored num/den: confirm aggregate's unit is the
    # declared throughput unit and nothing leaked the denominator into `value`.
    unit_ok = row["unit"] == "req_per_s" and row["metric"] == "throughput"

    passed = not spine_mismatches and paired_point_ok and unit_ok
    return {
        "passed": passed,
        "spine_mismatches": spine_mismatches,
        "paired_point_in_ci": paired_point_ok,
        "ratio_of_totals_point": direct,
        "paired_ci": [paired_lo, paired_hi],
        "unit_ok": unit_ok,
        "checked": ["spine median/ci vs reference", "paired point == sum/sum", "unit"],
    }


def representative(true_ratio: float) -> dict:
    """The single dataset of plan step 3: the point/interval error, made concrete."""
    windows = target.generate_windows(REP_SEED)
    samples = target.make_raw_samples(windows, probe="throughput", params={"point": 0})
    row = aggregate(samples)[0]

    paired_point = target.ratio_of_totals(windows)
    paired_lo, paired_hi = target.paired_bootstrap_ci_ratio(windows, iters=BOOT_ITERS)

    return {
        "true_ratio": true_ratio,
        "median_of_rates": row["median"],
        "mean_of_rates": row["mean"],
        "p99_of_rates": row["p99"],
        "paired_ratio_point": paired_point,
        "median_ci": [row["ci_low"], row["ci_high"]],
        "paired_ci": [paired_lo, paired_hi],
        "median_rel_bias": abs(row["median"] - true_ratio) / true_ratio,
        "mean_rel_bias": abs(row["mean"] - true_ratio) / true_ratio,
        "paired_rel_bias": abs(paired_point - true_ratio) / true_ratio,
        "median_ci_covers_true": covers(row["ci_low"], row["ci_high"], true_ratio),
        "paired_ci_covers_true": covers(paired_lo, paired_hi, true_ratio),
        "_summary_row": row,
        "_raw_samples": samples,
    }


def coverage_study(true_ratio: float) -> dict:
    """300 trials: how often does each CI cover R*, and the mean median bias."""
    n_cov_iid = 0  # spine median CI covers R*
    n_cov_paired = 0  # paired ratio-of-totals CI covers R*
    median_rel_biases = []
    mean_rel_biases = []
    paired_rel_biases = []

    for t in range(TRIALS):
        windows = target.generate_windows(BASE_SEED + t)
        samples = target.make_raw_samples(
            windows, probe="throughput", params={"trial": t}
        )

        # The spine, unchanged, on per-window rates.
        row = aggregate(samples)[0]
        n_cov_iid += covers(row["ci_low"], row["ci_high"], true_ratio)
        median_rel_biases.append(abs(row["median"] - true_ratio) / true_ratio)
        mean_rel_biases.append(abs(row["mean"] - true_ratio) / true_ratio)

        # The reference paired bootstrap on the same windows.
        p_lo, p_hi = target.paired_bootstrap_ci_ratio(
            windows, iters=BOOT_ITERS, seed=BASE_SEED + t
        )
        n_cov_paired += covers(p_lo, p_hi, true_ratio)
        paired_rel_biases.append(
            abs(target.ratio_of_totals(windows) - true_ratio) / true_ratio
        )

    return {
        "trials": TRIALS,
        "coverage_iid_median": n_cov_iid / TRIALS,
        "coverage_paired": n_cov_paired / TRIALS,
        "median_rel_bias": statistics.fmean(median_rel_biases),
        "mean_rel_bias": statistics.fmean(mean_rel_biases),
        "paired_rel_bias": statistics.fmean(paired_rel_biases),
    }


def verdict(rep: dict, cov: dict) -> str:
    """Apply the plan's success criteria."""
    confirm = (
        cov["median_rel_bias"] > 2.0  # >200% point bias
        and cov["coverage_iid_median"] < 0.10  # near-zero CI coverage
        and cov["coverage_paired"] >= 0.90  # paired estimator fixes it
    )
    refute = cov["coverage_iid_median"] >= 0.90 or cov["median_rel_bias"] < 0.10
    if confirm:
        return "CONFIRMS RATIO-METRIC-ESTIMATOR gap"
    if refute:
        return "REFUTES RATIO-METRIC-ESTIMATOR gap"
    return "INCONCLUSIVE"


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)

    # TRUE headline: closed form, cross-checked against a huge resampled ratio.
    true_ratio = target.true_ratio()
    big = target.generate_windows(999)
    # Average realized ratio over many fresh datasets approaches R* (E[num]/E[den]).
    realized = []
    for t in range(50):
        w = target.generate_windows(7000 + t)
        realized.append(target.ratio_of_totals(w))
    ref_ratio = statistics.fmean(realized)
    rel_err = abs(ref_ratio - true_ratio) / true_ratio
    print(
        f"[true ratio] closed-form R*={true_ratio:.4f} req/s  "
        f"mean realized ratio (50 datasets)={ref_ratio:.4f}  rel-err={rel_err:.3f}"
    )
    assert rel_err < 0.05, "closed-form R* disagrees with realized reference"

    # --- validity gate ------------------------------------------------------
    gate = validity_gate()
    status = "PASS" if gate["passed"] else "FAIL"
    print(f"[validity gate] {status}  (checked {gate['checked']})")
    if not gate["passed"]:
        raise SystemExit(f"CORRECTNESS GATE FAILED: {gate}")

    # --- representative dataset (point/interval error) ----------------------
    rep = representative(true_ratio)

    # --- coverage study -----------------------------------------------------
    cov = coverage_study(true_ratio)
    final = verdict(rep, cov)

    # --- artifacts ----------------------------------------------------------
    (RESULTS / "raw_samples.json").write_text(json.dumps(rep["_raw_samples"], indent=2))
    (RESULTS / "summary.json").write_text(json.dumps([rep["_summary_row"]], indent=2))

    comparison = {
        "claim_id": "RATIO-METRIC-ESTIMATOR",
        "verdict": final,
        "true_ratio": true_ratio,
        "median_of_rates": rep["median_of_rates"],
        "mean_of_rates": rep["mean_of_rates"],
        "paired_ratio_point": rep["paired_ratio_point"],
        "median_ci": rep["median_ci"],
        "paired_ci": rep["paired_ci"],
        "coverage_iid_median": cov["coverage_iid_median"],
        "coverage_paired": cov["coverage_paired"],
        "median_rel_bias": cov["median_rel_bias"],
        "mean_rel_bias": cov["mean_rel_bias"],
        "paired_rel_bias": cov["paired_rel_bias"],
        "representative_seed": REP_SEED,
        "trials": cov["trials"],
        "bootstrap_iters": BOOT_ITERS,
        "validity_gate": gate,
    }
    (RESULTS / "comparison.json").write_text(json.dumps(comparison, indent=2))

    report = _format_report(rep, cov, final, true_ratio)
    (RESULTS / "report.txt").write_text(report)
    print()
    print(report)
    print(f"\nArtifacts written to {RESULTS}/")
    print("  raw_samples.json  summary.json  comparison.json  report.txt")


def _format_report(rep: dict, cov: dict, final: str, true_ratio: float) -> str:
    """A custom throughput table.

    NB: report.format_table is deliberately NOT reused here -- it is time-shaped
    (multiplies values by 1e9 and labels them 'ns'), which would misrender a
    req/s throughput. That mismatch is itself a small symptom of the same gap:
    the spine's reporting assumes a lower-is-better time metric. The spine's
    aggregate() is reused unchanged; only the metric-appropriate rendering is local.
    """
    lines = []
    lines.append("RATIO-METRIC-ESTIMATOR: ratio-of-totals throughput vs the spine")
    lines.append("=" * 70)
    lines.append(f"TRUE headline R* = sum(num)/sum(den) = {true_ratio:,.2f} req/s")
    lines.append("")
    lines.append("Representative dataset (seed 0):")
    lines.append("-" * 70)
    hdr = f"{'estimator':<26}{'point (req/s)':>16}{'rel.bias':>10}{'95% CI (req/s)':>26}"
    lines.append(hdr)
    lines.append("-" * len(hdr))
    lines.append(
        f"{'spine median-of-rates':<26}{rep['median_of_rates']:>16,.2f}"
        f"{rep['median_rel_bias']*100:>9.0f}%"
        f"{('[%.1f, %.1f]' % tuple(rep['median_ci'])):>26}"
    )
    lines.append(
        f"{'spine mean-of-rates':<26}{rep['mean_of_rates']:>16,.2f}"
        f"{rep['mean_rel_bias']*100:>9.0f}%{'(no CI reported)':>26}"
    )
    lines.append(
        f"{'paired ratio-of-totals':<26}{rep['paired_ratio_point']:>16,.2f}"
        f"{rep['paired_rel_bias']*100:>9.0f}%"
        f"{('[%.1f, %.1f]' % tuple(rep['paired_ci'])):>26}"
    )
    lines.append(
        f"  median CI covers R*: {rep['median_ci_covers_true']}    "
        f"paired CI covers R*: {rep['paired_ci_covers_true']}"
    )
    lines.append("")
    lines.append(f"Coverage study ({cov['trials']} trials):")
    lines.append("-" * 70)
    lines.append(
        f"  spine median-CI coverage of R*   : {cov['coverage_iid_median']:.3f}"
    )
    lines.append(
        f"  paired ratio-CI coverage of R*   : {cov['coverage_paired']:.3f}"
    )
    lines.append(
        f"  mean |median_of_rates - R*| / R* : {cov['median_rel_bias']*100:.0f}%"
    )
    lines.append(
        f"  mean |mean_of_rates   - R*| / R* : {cov['mean_rel_bias']*100:.0f}%"
    )
    lines.append(
        f"  mean |ratio_of_totals - R*| / R* : {cov['paired_rel_bias']*100:.1f}%"
    )
    lines.append("")
    lines.append(f"VERDICT: {final}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
