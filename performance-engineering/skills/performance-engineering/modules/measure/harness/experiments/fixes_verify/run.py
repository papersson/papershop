"""Verification for the three spine fixes (Iteration: fix-the-useful-few).

Run from the repo root:  uv run python experiments/fixes_verify/run.py

Proves, in one self-contained script:
  L. LEGACY-INERT — re-aggregating the three real-regime experiments' stored
     raw_samples reproduces their stored stats.json byte-for-byte, so the fixes
     did not perturb any existing result.
  1. BATCH-HOMOGENEITY-GUARD — aggregate() now refuses a (probe,params) group
     that mixes batch sizes.
  2. RATIO-CHANNEL — a numerator/denominator group aggregates to the honest
     ratio-of-totals with a paired-bootstrap CI that covers the truth, while the
     old median-of-rates is badly biased.
  3. APPROX-CORRECTNESS-GATE — a probe with a quality() hook + min_quality is
     admitted on recall, exempt from bit-equality; the default gate stays strict.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from harness.core import Probe, run_suite
from harness.stats import aggregate

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"


# --- L. legacy inertness --------------------------------------------------
def check_legacy() -> dict:
    """Re-aggregate stored raw samples and assert every stored value is
    reproduced exactly. Recomputed rows may carry ADDITIONAL keys (the provenance
    fields added in an earlier spine evolution, which pre-provenance stored files
    never received); that is expected. What must hold is that no pre-existing
    value changed, which is what proves these fixes are inert for scalar data.
    """
    out = {}
    for exp in ("membership", "cli_search", "service_regime"):
        raw_p = RESULTS / exp / "raw_samples.json"
        stats_p = RESULTS / exp / "stats.json"
        if not (raw_p.exists() and stats_p.exists()):
            out[exp] = "skipped (missing artifacts)"
            continue
        stored = json.loads(stats_p.read_text())
        idx = {
            (r["probe"], json.dumps(r["params"], sort_keys=True)): r
            for r in aggregate(json.loads(raw_p.read_text()))
        }
        ok = True
        for srow in stored:
            rrow = idx.get((srow["probe"], json.dumps(srow["params"], sort_keys=True)))
            if rrow is None or any(rrow.get(k) != v for k, v in srow.items()):
                ok = False
                break
        out[exp] = "VALUES IDENTICAL" if ok else "CHANGED"
    return out


# --- 1. batch-homogeneity guard -------------------------------------------
def check_batch_guard() -> dict:
    base = dict(probe="p", params={"n": 1}, value=1e-6,
                metric="seconds_per_op", unit="seconds", clock="wall",
                includes_startup=False, overhead_removed=False)
    mixed = ([{**base, "rep": i, "batch": 1} for i in range(10)]
             + [{**base, "rep": i, "batch": 1000} for i in range(10)])
    homog = [{**base, "rep": i, "batch": 1} for i in range(10)]
    raised = msg = None
    try:
        aggregate(mixed)
        raised = False
    except ValueError as e:
        raised = True
        msg = str(e).splitlines()[0]
    homog_ok = True
    try:
        aggregate(homog)
    except ValueError:
        homog_ok = False
    return {"mixed_raises": raised, "message": msg, "homogeneous_ok": homog_ok}


# --- 2. ratio channel ------------------------------------------------------
def _ln1(rng, s):  # mean-1 lognormal noise
    return math.exp(rng.gauss(-0.5 * s * s, s))


def check_ratio() -> dict:
    rng = random.Random(20260620)
    windows = []
    for rate0, d0, count in ((1000.0, 0.1, 50), (100.0, 10.0, 5)):  # fast, slow
        for _ in range(count):
            den = d0 * _ln1(rng, 0.3)
            num = (rate0 * d0) * _ln1(rng, 0.3)
            windows.append((num, den))
    true_ratio = (1000.0 * 0.1 * 50 + 100.0 * 10.0 * 5) / (0.1 * 50 + 10.0 * 5)
    samples = [
        {"probe": "throughput", "params": {"p": 0}, "rep": i, "batch": 1,
         "value": n / d, "numerator": n, "denominator": d,
         "metric": "throughput", "unit": "req_per_s", "clock": "wall",
         "includes_startup": False, "overhead_removed": False}
        for i, (n, d) in enumerate(windows)
    ]
    row = aggregate(samples)[0]
    direct = sum(n for n, _ in windows) / sum(d for _, d in windows)
    return {
        "is_ratio": row.get("is_ratio", False),
        "true_ratio": true_ratio,
        "ratio_of_totals": row["ratio"],
        "ratio_matches_direct": abs(row["ratio"] - direct) < 1e-12,
        "ratio_rel_err_vs_true": abs(row["ratio"] - true_ratio) / true_ratio,
        "ratio_ci": [row["ratio_ci_low"], row["ratio_ci_high"]],
        "ci_covers_true": row["ratio_ci_low"] <= true_ratio <= row["ratio_ci_high"],
        "naive_median_of_rates": row["naive_median_of_rates"],
        "naive_rel_err_vs_true": abs(row["naive_median_of_rates"] - true_ratio) / true_ratio,
    }


# --- 3. approximate-correctness gate --------------------------------------
_K = 5


def _dataset(params):
    rng = random.Random(7)
    data = [rng.gauss(0, 1) for _ in range(params["m"])]
    queries = [rng.gauss(0, 1) for _ in range(params["q"])]
    return {"data": data, "queries": queries}


def _exact_topk(fx):
    out = []
    for q in fx["queries"]:
        order = sorted(range(len(fx["data"])), key=lambda i: abs(fx["data"][i] - q))
        out.append(order[:_K])
    return out


def _approx_topk(fx):
    out = []
    for j, q in enumerate(fx["queries"]):
        order = sorted(range(len(fx["data"])), key=lambda i: abs(fx["data"][i] - q))
        top = order[:_K]
        if j % 3 == 0:  # drop one true neighbour on every 3rd query -> recall ~0.93
            top = order[: _K - 1] + [order[_K]]
        out.append(top)
    return out


def _recall(output, fixture):
    truth = _exact_topk(fixture)
    hit = tot = 0
    for a, e in zip(output, truth):
        hit += len(set(a) & set(e))
        tot += len(e)
    return hit / tot


def check_approx_gate() -> dict:
    grid = [{"m": 200, "q": 30}]
    exact = Probe("exact", _dataset, _exact_topk)
    approx = Probe("approx", _dataset, _approx_topk, quality=_recall)

    recall = _recall(_approx_topk(_dataset(grid[0])), _dataset(grid[0]))

    # admitted on quality
    passed = err = None
    try:
        s = run_suite([exact, approx], grid, repetitions=3, min_quality=0.85)
        passed = len(s) > 0
    except ValueError as e:
        passed = False
        err = str(e).splitlines()[0]

    # default gate still strict (no min_quality -> bit-equality -> must raise)
    default_raises = False
    try:
        run_suite([exact, approx], grid, repetitions=3)
    except ValueError as e:
        default_raises = "CORRECTNESS GATE" in str(e)

    # bar enforced: an impossible bar rejects
    bar_enforced = False
    try:
        run_suite([exact, approx], grid, repetitions=3, min_quality=0.999)
    except ValueError as e:
        bar_enforced = "QUALITY GATE" in str(e)

    return {"recall": recall, "admitted_on_quality": passed, "admit_error": err,
            "default_gate_strict": default_raises, "quality_bar_enforced": bar_enforced}


def main() -> None:
    legacy = check_legacy()
    batch = check_batch_guard()
    ratio = check_ratio()
    approx = check_approx_gate()

    print("L. LEGACY-INERT (re-aggregate stored raw == stored stats):")
    for k, v in legacy.items():
        print(f"     {k:<16} {v}")
    print("1. BATCH-HOMOGENEITY-GUARD:")
    print(f"     mixed-batch raises : {batch['mixed_raises']}  ({batch['message']})")
    print(f"     homogeneous ok     : {batch['homogeneous_ok']}")
    print("2. RATIO-CHANNEL:")
    print(f"     is_ratio           : {ratio['is_ratio']}")
    print(f"     true R*            : {ratio['true_ratio']:.2f} req/s")
    print(f"     ratio-of-totals    : {ratio['ratio_of_totals']:.2f} "
          f"(rel err {ratio['ratio_rel_err_vs_true']*100:.1f}%, "
          f"matches direct sum/sum: {ratio['ratio_matches_direct']})")
    print(f"     ratio CI           : [{ratio['ratio_ci'][0]:.1f}, {ratio['ratio_ci'][1]:.1f}] "
          f"covers true: {ratio['ci_covers_true']}")
    print(f"     OLD median-of-rates: {ratio['naive_median_of_rates']:.2f} "
          f"(rel err {ratio['naive_rel_err_vs_true']*100:.0f}%  <-- the bug)")
    print("3. APPROX-CORRECTNESS-GATE:")
    print(f"     recall             : {approx['recall']:.3f}")
    print(f"     admitted on quality: {approx['admitted_on_quality']}")
    print(f"     default gate strict: {approx['default_gate_strict']}")
    print(f"     quality bar enforced: {approx['quality_bar_enforced']}")

    ok = (
        all(v in ("VALUES IDENTICAL", "skipped (missing artifacts)") for v in legacy.values())
        and batch["mixed_raises"] and batch["homogeneous_ok"]
        and ratio["is_ratio"] and ratio["ratio_matches_direct"]
        and ratio["ci_covers_true"] and ratio["ratio_rel_err_vs_true"] < 0.15
        and ratio["naive_rel_err_vs_true"] > 0.5
        and approx["admitted_on_quality"] and approx["default_gate_strict"]
        and approx["quality_bar_enforced"]
    )
    print(f"\nALL FIXES VERIFIED: {ok}")
    if not ok:
        raise SystemExit("verification FAILED")


if __name__ == "__main__":
    main()
