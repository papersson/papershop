"""i.i.d.-bootstrap blind-spot test of the spine's CI (claim IID-BOOTSTRAP).

Run from the repo root:  uv run python experiments/iid_bootstrap/run.py

A pure-statistics experiment. It touches NO spine files: it feeds synthetic
serially correlated raw_samples (in the load-bearing schema) straight into the
UNMODIFIED ``harness.stats.aggregate`` and asks one question:

    The spine builds its 95% median CI by resampling samples i.i.d. (drawing
    single indices uniformly with replacement). If the per-op samples are NOT
    exchangeable — a state-dependent trajectory with autocorrelation — does that
    i.i.d. CI still cover the TRUE marginal median 95% of the time?

We answer empirically: per AR(1) model, simulate K independent stationary paths,
feed each through the unmodified aggregate to get the spine's i.i.d. median CI,
and compute a moving-block-bootstrap CI (defined only in the experiment) on the
same path. We measure coverage of the TRUE median (= BASE, closed form) by each
CI, both CI widths, and the empirical between-experiment SD of the sample median
(the quantity the CI is supposed to track).

Correctness/validity gate: before trusting any coverage number we verify that the
spine, run unchanged on this data, reproduces the same median and median-CI that
an independent local computation produces from the identical numbers. If the
spine and the independent reference disagree, the comparison is void.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import numpy as np
import target  # same directory; on sys.path because this file is the entrypoint

from harness.stats import aggregate, bootstrap_ci_median

RESULTS = Path(__file__).resolve().parents[2] / "results" / "iid_bootstrap"

# --- experiment knobs (kept modest: runs in a couple of minutes) ----------
K = 300  # independent experiments per model
N = 2000  # samples per experiment
BOOT_ITERS = 2000  # block-bootstrap iterations (spine uses its own 2000 default)
REF_N = 5_000_000  # huge i.i.d. draw to cross-check the closed-form TRUE median
BASE_SEED = 20260620


def covers(lo: float, hi: float, value: float) -> bool:
    return lo <= value <= hi


def validity_gate(rho: float, model_name: str) -> dict:
    """Confirm the UNMODIFIED spine reproduces an independent local computation.

    Builds one experiment's worth of samples, runs them through the real
    ``aggregate``, and checks the spine's median / median-CI match a direct local
    computation on the identical numbers. Guards the whole comparison: if the
    spine isn't doing what we think, the coverage study is meaningless.
    """
    rng = np.random.default_rng(12345)  # fixed gate seed
    xs = target.draw(rho, rng, N)
    samples = target.make_raw_samples(xs, probe=model_name, params={"model": model_name})

    summary = aggregate(samples)
    assert len(summary) == 1, "expected exactly one probe/param group"
    row = summary[0]

    # independent local reference (does not go through aggregate)
    ref_median = statistics.median(xs)
    ref_lo, ref_hi = bootstrap_ci_median(xs)  # same defaults aggregate uses

    checks = {
        "median": (row["median"], ref_median),
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


def run_model(rho: float, model_name: str, true_median: float) -> dict:
    block_len = target.default_block_len(N)

    per_exp_median = []
    iid_widths = []
    block_widths = []

    n_cov_iid = 0  # spine i.i.d. median CI covers TRUE median
    n_cov_block = 0  # reference block CI covers TRUE median

    for k in range(K):
        # fresh, independent stationary path per experiment
        rng = np.random.default_rng(BASE_SEED + k)
        xs = target.draw(rho, rng, N)
        samples = target.make_raw_samples(
            xs, probe=model_name, params={"model": model_name, "exp": k}
        )

        # The spine, unchanged, on a correlated trajectory.
        row = aggregate(samples)[0]
        i_lo, i_hi = row["ci_low"], row["ci_high"]
        median = row["median"]

        # Reference block CI — defined only in the experiment.
        b_lo, b_hi = target.block_bootstrap_ci_median(
            xs, block_len=block_len, iters=BOOT_ITERS
        )

        per_exp_median.append(median)
        iid_widths.append(i_hi - i_lo)
        block_widths.append(b_hi - b_lo)
        n_cov_iid += covers(i_lo, i_hi, true_median)
        n_cov_block += covers(b_lo, b_hi, true_median)

    # The empirical truth the CI should track: between-experiment SD of the
    # sample median. A correct 95% CI half-width ~ 1.96 * this SD.
    median_sampling_sd = statistics.pstdev(per_exp_median)
    mean_iid_width = statistics.fmean(iid_widths)
    mean_block_width = statistics.fmean(block_widths)

    return {
        "model": model_name,
        "rho": rho,
        "K": K,
        "n_per_experiment": N,
        "block_len": block_len,
        "true_median": true_median,
        "cov_iid": n_cov_iid / K,
        "cov_block": n_cov_block / K,
        "mean_iid_ci_width": mean_iid_width,
        "mean_block_ci_width": mean_block_width,
        "iid_over_block_width_ratio": mean_iid_width / mean_block_width,
        "median_sampling_sd": median_sampling_sd,
        "implied_correct_width": 2 * 1.96 * median_sampling_sd,
        "iid_width_over_correct": mean_iid_width / (2 * 1.96 * median_sampling_sd),
        "block_width_over_correct": mean_block_width / (2 * 1.96 * median_sampling_sd),
        # array for plotting
        "_per_exp_median": per_exp_median,
    }


def verdict(results: list[dict]) -> str:
    """Apply the plan's success criteria across the AR(1) models."""
    by = {r["model"]: r for r in results}
    ctrl = by["iid_rho0.0"]
    mid = by["ar1_rho0.7"]
    hi = by["ar1_rho0.9"]

    confirm = (
        0.90 <= ctrl["cov_iid"] <= 0.98  # harness unbiased on i.i.d. control
        and hi["cov_iid"] < 0.85  # material under-coverage under strong AR(1)
        and 0.88 <= hi["cov_block"] <= 0.97  # block fixes it
        and hi["iid_over_block_width_ratio"] < 0.75  # i.i.d. CI too narrow
        and hi["cov_iid"] < mid["cov_iid"] < ctrl["cov_iid"]  # monotone degradation
    )
    refute = hi["cov_iid"] >= 0.90 or hi["cov_block"] <= hi["cov_iid"]
    if confirm:
        return "CONFIRMS IID-BOOTSTRAP blind spot"
    if refute:
        return "REFUTES IID-BOOTSTRAP blind spot"
    return "INCONCLUSIVE"


def plot(results: list[dict], out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(results), figsize=(6.5 * len(results), 5.2))
    if len(results) == 1:
        axes = [axes]

    for ax, r in zip(axes, results):
        us = 1e6  # plot in microseconds
        meds = [v * us for v in r["_per_exp_median"]]
        true_median = r["true_median"] * us

        ax.hist(
            meds,
            bins=40,
            color="#888",
            alpha=0.55,
            label="per-experiment sample medians (spine)",
        )
        ax.axvline(
            true_median, color="black", lw=2, label=f"TRUE median = {true_median:.3f} us"
        )

        # The spine's i.i.d. CI band, centered at the true median.
        i_half = (r["mean_iid_ci_width"] * us) / 2
        ax.axvspan(
            true_median - i_half,
            true_median + i_half,
            color="tab:red",
            alpha=0.35,
            label=f"spine i.i.d. CI band (w={r['mean_iid_ci_width']*us:.4f} us)",
        )

        # The reference block CI band, centered at the true median.
        b_half = (r["mean_block_ci_width"] * us) / 2
        ax.axvspan(
            true_median - b_half,
            true_median + b_half,
            color="tab:green",
            alpha=0.25,
            label=f"block CI band (w={r['mean_block_ci_width']*us:.4f} us)",
        )

        ax.set_title(
            f"{r['model']}  (rho={r['rho']})\n"
            f"cov_iid={r['cov_iid']:.2f}  cov_block={r['cov_block']:.2f}  "
            f"iid/block width={r['iid_over_block_width_ratio']:.2f}x"
        )
        ax.set_xlabel("median seconds_per_op (microseconds)")
        ax.set_ylabel(f"count over K={r['K']} experiments")
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(True, ls=":", alpha=0.5)

    fig.suptitle(
        "Spine's i.i.d. bootstrap CI under-covers the median when ops are "
        "autocorrelated; a moving-block bootstrap restores coverage",
        fontsize=12,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)

    # TRUE marginal median: closed form (= BASE), cross-checked against a huge
    # i.i.d. reference draw of the marginal lognormal.
    true_median = target.true_median()
    ref_rng = np.random.default_rng(BASE_SEED + 999)
    ref_draw = target.draw(0.0, ref_rng, REF_N)  # rho=0 => i.i.d. marginal draw
    ref_median = statistics.median(ref_draw)
    rel_err = abs(ref_median - true_median) / true_median
    print(
        f"[true median] closed-form={true_median:.6e}  "
        f"ref-draw(N={REF_N})={ref_median:.6e}  rel-err={rel_err:.2e}"
    )
    assert rel_err < 0.01, "closed-form TRUE median disagrees with reference draw"

    # --- validity gate: spine reproduces an independent computation ---------
    gates = [validity_gate(rho, name) for name, rho in target.RHOS.items()]
    for g in gates:
        status = "PASS" if g["passed"] else "FAIL"
        print(f"[validity gate] {g['model']:<14} {status}  (checked {g['checked']})")
        if not g["passed"]:
            raise SystemExit(
                f"CORRECTNESS GATE FAILED: spine disagrees with reference on "
                f"{g['model']}: {g['mismatches']}"
            )

    # --- coverage study -----------------------------------------------------
    results = [run_model(rho, name, true_median) for name, rho in target.RHOS.items()]
    final = verdict(results)

    payload = {
        "claim_id": "IID-BOOTSTRAP",
        "verdict": final,
        "K": K,
        "n_per_experiment": N,
        "bootstrap_iters": BOOT_ITERS,
        "block_len": target.default_block_len(N),
        "reference_draw_N": REF_N,
        "true_median_closed_form": true_median,
        "true_median_reference_draw": ref_median,
        "validity_gate": gates,
        "models": [
            {k: v for k, v in r.items() if not k.startswith("_")} for r in results
        ],
    }
    (RESULTS / "coverage.json").write_text(json.dumps(payload, indent=2))

    plot(results, RESULTS / "iid_bootstrap.png")

    # --- console report -----------------------------------------------------
    print()
    hdr = (
        f"{'model':<14}{'rho':>6}{'cov_iid':>9}{'cov_block':>11}"
        f"{'iid/blk w':>11}{'medianSD(us)':>14}"
    )
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        print(
            f"{r['model']:<14}{r['rho']:>6.1f}{r['cov_iid']:>9.2f}"
            f"{r['cov_block']:>11.2f}{r['iid_over_block_width_ratio']:>11.2f}"
            f"{r['median_sampling_sd']*1e6:>14.4f}"
        )
    print()
    for r in results:
        print(
            f"{r['model']}: iid width/correct={r['iid_width_over_correct']:.2f}  "
            f"block width/correct={r['block_width_over_correct']:.2f}  "
            f"(correct = 2*1.96*between-exp median SD)"
        )
    print(f"\nVERDICT: {final}")
    print(f"Artifacts written to {RESULTS}/")
    print("  coverage.json  iid_bootstrap.png")


if __name__ == "__main__":
    main()
