"""Tail-CI stress test of the spine's default statistic (claim C2-tail).

Run from the repo root:  uv run python experiments/tail_ci/run.py

This is a pure-statistics experiment. It touches NO spine files: it feeds
synthetic heavy-tailed raw_samples (in the load-bearing schema) straight into
the UNMODIFIED ``harness.stats.aggregate`` and asks a simple question:

    The spine reports a 95% bootstrap CI for the MEDIAN (ci_low/ci_high) and a
    bare p99 with no band. If a reader takes p99 as their headline, is the only
    uncertainty band the spine offers (the median CI) adequate for it?

We answer empirically by simulating K independent "experiments" per model and
measuring coverage of the TRUE median and TRUE p99 by (a) the spine's median CI
and (b) a reference ``bootstrap_ci_quantile`` defined only in the experiment.

Correctness/validity gate: before trusting any coverage number we verify that
the spine, run unchanged on this data, reproduces the same median, p99 and
median-CI that an independent local computation produces from the same samples.
If the spine and the independent reference disagree, the comparison is void.
"""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

import target  # same directory; on sys.path because this file is the entrypoint

from harness.stats import aggregate, bootstrap_ci_median

RESULTS = Path(__file__).resolve().parents[2] / "results" / "tail_ci"

# --- experiment knobs (kept modest: runs in a couple of minutes) ----------
K = 200  # independent experiments per model
N = 2000  # samples per experiment
REF_N = 5_000_000  # huge draw for the TRUE median / TRUE p99
BASE_SEED = 20260620


def true_values(model, seed: int) -> tuple[float, float]:
    """TRUE median and TRUE p99 from one huge reference draw."""
    rng = random.Random(seed)
    xs = target.draw(model, rng, REF_N)
    return statistics.median(xs), target._percentile(xs, 0.99)


def covers(lo: float, hi: float, value: float) -> bool:
    return lo <= value <= hi


def validity_gate(model, model_name: str) -> dict:
    """Confirm the UNMODIFIED spine reproduces an independent local computation.

    Builds one experiment's worth of samples, runs them through the real
    ``aggregate``, and checks that the spine's median / p99 / median-CI match a
    direct local computation on the identical numbers. Guards the whole
    comparison: if the spine isn't doing what we think, the coverage study is
    meaningless.
    """
    rng = random.Random(12345)  # fixed gate seed
    xs = target.draw(model, rng, N)
    samples = target.make_raw_samples(xs, probe=model_name, params={"model": model_name})

    summary = aggregate(samples)
    assert len(summary) == 1, "expected exactly one probe/param group"
    row = summary[0]

    # independent local reference (does not go through aggregate)
    ref_median = statistics.median(xs)
    ref_p99 = target._percentile(xs, 0.99)
    ref_lo, ref_hi = bootstrap_ci_median(xs)  # same defaults aggregate uses

    checks = {
        "median": (row["median"], ref_median),
        "p99": (row["p99"], ref_p99),
        "ci_low": (row["ci_low"], ref_lo),
        "ci_high": (row["ci_high"], ref_hi),
    }
    mismatches = {
        k: {"spine": a, "reference": b}
        for k, (a, b) in checks.items()
        if abs(a - b) > 1e-18
    }
    return {
        "model": model_name,
        "n_samples": len(samples),
        "passed": not mismatches,
        "mismatches": mismatches,
        "checked": list(checks),
    }


def run_model(model, model_name: str) -> dict:
    true_median, true_p99 = true_values(model, BASE_SEED + 999)

    per_exp_p99 = []  # the spine's per-experiment p99 point estimate
    per_exp_median = []
    median_ci_widths = []
    p99_ci_widths = []
    median_ci_rel_widths = []
    p99_ci_rel_widths = []

    n_cov_median = 0  # spine median CI covers TRUE median (sanity ~0.95)
    n_cov_median_for_p99 = 0  # spine median CI covers TRUE p99 (predict ~0)
    n_cov_qci_for_p99 = 0  # reference p99 CI covers TRUE p99 (predict ~0.95)

    for k in range(K):
        rng = random.Random(BASE_SEED + k)
        xs = target.draw(model, rng, N)
        samples = target.make_raw_samples(
            xs, probe=model_name, params={"model": model_name, "exp": k}
        )

        # The spine, unchanged, on heavy-tailed data.
        row = aggregate(samples)[0]
        m_lo, m_hi = row["ci_low"], row["ci_high"]
        median = row["median"]
        p99 = row["p99"]

        # Reference tail CI — defined only in the experiment.
        q_lo, q_hi = target.bootstrap_ci_quantile(xs, 0.99)

        per_exp_median.append(median)
        per_exp_p99.append(p99)
        median_ci_widths.append(m_hi - m_lo)
        p99_ci_widths.append(q_hi - q_lo)
        median_ci_rel_widths.append((m_hi - m_lo) / median)
        p99_ci_rel_widths.append((q_hi - q_lo) / p99)

        n_cov_median += covers(m_lo, m_hi, true_median)
        n_cov_median_for_p99 += covers(m_lo, m_hi, true_p99)
        n_cov_qci_for_p99 += covers(q_lo, q_hi, true_p99)

    p99_sampling_sd = statistics.pstdev(per_exp_p99)
    mean_median_ci_width = statistics.fmean(median_ci_widths)

    return {
        "model": model_name,
        "K": K,
        "n_per_experiment": N,
        "true_median": true_median,
        "true_p99": true_p99,
        "cov_median": n_cov_median / K,
        "cov_median_for_p99": n_cov_median_for_p99 / K,
        "cov_qci_for_p99": n_cov_qci_for_p99 / K,
        "p99_sampling_sd": p99_sampling_sd,
        "mean_median_ci_width": mean_median_ci_width,
        "p99_sd_over_median_ci_width": p99_sampling_sd / mean_median_ci_width,
        "median_ci_rel_width": statistics.fmean(median_ci_rel_widths),
        "p99_ci_rel_width": statistics.fmean(p99_ci_rel_widths),
        "mean_p99_ci_width": statistics.fmean(p99_ci_widths),
        # arrays for plotting
        "_per_exp_p99": per_exp_p99,
        "_per_exp_median": per_exp_median,
    }


def verdict(results: list[dict]) -> str:
    """Apply the plan's success criteria across BOTH distribution models."""
    confirm = all(
        0.90 <= r["cov_median"] <= 0.98
        and r["cov_median_for_p99"] <= 0.10
        and r["p99_sd_over_median_ci_width"] > 2.0
        and 0.90 <= r["cov_qci_for_p99"] <= 0.97
        for r in results
    )
    refute = any(
        r["cov_median_for_p99"] >= 0.90 or r["p99_sd_over_median_ci_width"] <= 1.2
        for r in results
    )
    if confirm:
        return "CONFIRMS C2-tail gap"
    if refute:
        return "REFUTES C2-tail gap"
    return "INCONCLUSIVE"


def plot(results: list[dict], out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(results), figsize=(7 * len(results), 5.2))
    if len(results) == 1:
        axes = [axes]

    for ax, r in zip(axes, results):
        us = 1e6  # plot in microseconds
        p99s = [v * us for v in r["_per_exp_p99"]]
        true_p99 = r["true_p99"] * us
        true_median = r["true_median"] * us

        ax.hist(
            p99s,
            bins=40,
            color="#888",
            alpha=0.55,
            label="per-experiment p99 estimates (spine)",
        )
        ax.axvline(
            true_p99, color="black", lw=2, label=f"TRUE p99 = {true_p99:.2f} us"
        )

        # The only band the spine offers (median CI), centered at true median.
        m_half = (r["mean_median_ci_width"] * us) / 2
        ax.axvspan(
            true_median - m_half,
            true_median + m_half,
            color="tab:red",
            alpha=0.35,
            label=f"spine median CI band (w={r['mean_median_ci_width']*us:.3f} us)",
        )

        # Reference p99 CI band, centered at true p99.
        q_half = (r["mean_p99_ci_width"] * us) / 2
        ax.axvspan(
            true_p99 - q_half,
            true_p99 + q_half,
            color="tab:green",
            alpha=0.30,
            label=f"reference p99 CI band (w={r['mean_p99_ci_width']*us:.3f} us)",
        )

        ax.set_title(
            f"{r['model']}\n"
            f"cov(median CI, p99)={r['cov_median_for_p99']:.2f}  "
            f"cov(p99 CI, p99)={r['cov_qci_for_p99']:.2f}  "
            f"p99SD/medCIw={r['p99_sd_over_median_ci_width']:.1f}x"
        )
        ax.set_xlabel("seconds_per_op statistic (microseconds)")
        ax.set_ylabel(f"count over K={r['K']} experiments")
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(True, ls=":", alpha=0.5)

    fig.suptitle(
        "Spine's median CI is correct for the median but misleading as a p99 band",
        fontsize=13,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)

    # --- validity gate: spine reproduces an independent computation ---------
    gates = [validity_gate(model, name) for name, model in target.MODELS.items()]
    for g in gates:
        status = "PASS" if g["passed"] else "FAIL"
        print(f"[validity gate] {g['model']:<22} {status}  (checked {g['checked']})")
        if not g["passed"]:
            raise SystemExit(
                f"CORRECTNESS GATE FAILED: spine disagrees with reference on "
                f"{g['model']}: {g['mismatches']}"
            )

    # --- coverage study -----------------------------------------------------
    results = [run_model(model, name) for name, model in target.MODELS.items()]
    final = verdict(results)

    # strip plotting arrays out of the JSON payload
    payload = {
        "claim_id": "C2-tail",
        "verdict": final,
        "K": K,
        "n_per_experiment": N,
        "reference_draw_N": REF_N,
        "validity_gate": gates,
        "models": [
            {k: v for k, v in r.items() if not k.startswith("_")} for r in results
        ],
    }
    (RESULTS / "coverage.json").write_text(json.dumps(payload, indent=2))

    plot(results, RESULTS / "tail_ci.png")

    # --- console report -----------------------------------------------------
    print()
    hdr = (
        f"{'model':<22}{'cov_med':>9}{'cov_med→p99':>13}"
        f"{'cov_p99CI':>11}{'p99SD/medCIw':>14}"
    )
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        print(
            f"{r['model']:<22}{r['cov_median']:>9.2f}{r['cov_median_for_p99']:>13.2f}"
            f"{r['cov_qci_for_p99']:>11.2f}{r['p99_sd_over_median_ci_width']:>14.1f}"
        )
    print()
    for r in results:
        print(
            f"{r['model']}: median rel-CI-width={r['median_ci_rel_width']:.4f}  "
            f"p99 rel-CI-width={r['p99_ci_rel_width']:.4f}"
        )
    print(f"\nVERDICT: {final}")
    print(f"Artifacts written to {RESULTS}/")
    print("  coverage.json  tail_ci.png")


if __name__ == "__main__":
    main()
