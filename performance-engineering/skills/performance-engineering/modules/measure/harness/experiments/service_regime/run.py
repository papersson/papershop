"""SERVICE/load regime experiment (claim SERVICE-REGIME / C1 for the 3rd regime).

Run from the repo root:  uv run python experiments/service_regime/run.py

Question under test: can a SERVICE/load target be added to the harness with ONLY
an adapter -- no spine edits -- by mapping an open-loop generator's per-request
latencies into the existing raw-sample schema, so they flow unchanged through
``stats.aggregate`` and ``report``?

What this script does, end to end:
  1. records the sha256 of the three spine files (core/stats/report),
  2. stands up the local endpoint and drives it open-loop with vegeta over a
     small arrival-rate sweep, running a per-rate correctness gate,
  3. feeds the raw samples straight into the UNMODIFIED ``stats.aggregate``,
  4. runs a validity gate: the spine must reproduce an independent local
     computation of median / p99 / median-CI on the identical numbers,
  5. writes raw_samples.json + stats.json, renders a PNG with the spine's
     ``report.plot_scaling`` and prints ``report.format_table``,
  6. re-records the three sha256 and asserts byte-identity (the C1 invariant).
"""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path

import target  # same directory; on sys.path because this file is the entrypoint

from harness import report
from harness.stats import aggregate, bootstrap_ci_median

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "service_regime"
SPINE = {
    name: ROOT / "src" / "harness" / f"{name}.py"
    for name in ("core", "stats", "report")
}

# Experiment knobs (kept modest: one short attack per rate, ~24s of traffic).
RATES = [100, 200, 300]
DURATION_S = 8


def spine_digests() -> dict[str, str]:
    return {name: hashlib.sha256(p.read_bytes()).hexdigest() for name, p in SPINE.items()}


def validity_gate(samples: list[dict], summary_row: dict) -> dict:
    """Spine must reproduce an independent local computation on the same numbers.

    Guards the whole claim: if ``aggregate`` is not computing what we think on
    this real latency data, the headline tail numbers are meaningless. We
    recompute median / p99 / median-CI locally (NOT through aggregate) and check
    they match the spine's summary for the same probe/param group.
    """
    xs = [s["seconds_per_op"] for s in samples]
    ref_median = statistics.median(xs)
    ref_p99 = target_percentile(xs, 0.99)
    ref_lo, ref_hi = bootstrap_ci_median(xs)  # same defaults aggregate uses
    checks = {
        "median": (summary_row["median"], ref_median),
        "p99": (summary_row["p99"], ref_p99),
        "ci_low": (summary_row["ci_low"], ref_lo),
        "ci_high": (summary_row["ci_high"], ref_hi),
    }
    mismatches = {
        k: {"spine": a, "reference": b}
        for k, (a, b) in checks.items()
        if abs(a - b) > 1e-18
    }
    return {"passed": not mismatches, "mismatches": mismatches, "checked": list(checks)}


def target_percentile(xs, p):
    # mirror stats._percentile so the validity gate is an INDEPENDENT recompute
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)

    before = spine_digests()

    # --- drive the endpoint open-loop over the rate sweep -------------------
    all_samples: list[dict] = []
    gates: list[dict] = []
    samples_by_rate: dict[int, list[dict]] = {}
    with target.LocalEndpoint() as ep:
        print(f"[service] endpoint up at {ep.url}")
        for rate in RATES:
            samples, gate = target.collect_samples(ep.url, rate, DURATION_S)
            status = "PASS" if gate["passed"] else "FAIL"
            print(
                f"[correctness gate] rate={rate:>4}  {status}  "
                f"n={gate['n_requests']}  non200={gate['n_non_200']}  "
                f"err={gate['n_errored']}"
            )
            if not gate["passed"]:
                raise SystemExit(
                    f"CORRECTNESS GATE FAILED at rate={rate}: the endpoint did "
                    f"not serve all requests cleanly: {gate}"
                )
            all_samples.extend(samples)
            gates.append(gate)
            samples_by_rate[rate] = samples

    # --- spine, unchanged: aggregate the real latency samples --------------
    stats = aggregate(all_samples)

    # --- validity gate: spine reproduces an independent local computation ---
    val_gates = []
    for row in stats:
        rate = row["params"]["rate"]
        vg = validity_gate(samples_by_rate[rate], row)
        vg["rate"] = rate
        val_gates.append(vg)
        status = "PASS" if vg["passed"] else "FAIL"
        print(f"[validity gate]    rate={rate:>4}  {status}  (checked {vg['checked']})")
        if not vg["passed"]:
            raise SystemExit(f"VALIDITY GATE FAILED at rate={rate}: {vg['mismatches']}")

    # --- artifacts ----------------------------------------------------------
    (RESULTS / "raw_samples.json").write_text(json.dumps(all_samples))
    (RESULTS / "stats.json").write_text(json.dumps(stats, indent=2))

    # spine reporter, unchanged: scaling plot (median latency vs arrival rate)
    report.plot_scaling(
        stats,
        x_key="rate",
        out_path=RESULTS / "latency_scaling.png",
        title="SERVICE regime: open-loop request latency vs arrival rate",
        x_label="vegeta arrival rate (requests/s, open-loop)",
        per_call_label="request",
    )

    after = spine_digests()
    spine_unchanged = before == after

    # --- headline numbers ---------------------------------------------------
    headline = []
    for row in sorted(stats, key=lambda r: r["params"]["rate"]):
        med = row["median"]
        p99 = row["p99"]
        med_ciw = row["ci_high"] - row["ci_low"]
        p99_ciw = row["p99_ci_high"] - row["p99_ci_low"]
        headline.append(
            {
                "rate": row["params"]["rate"],
                "n": row["n"],
                "median_s": med,
                "p99_s": p99,
                "p99_over_median": p99 / med,
                "median_ci_width_s": med_ciw,
                "p99_ci_width_s": p99_ciw,
                "p99_ciw_over_median_ciw": p99_ciw / med_ciw,
            }
        )

    # plan's success criteria, applied to every rate group
    tail_is_heavy = all(h["p99_over_median"] > 3.0 for h in headline)
    tail_ci_wider = all(h["p99_ciw_over_median_ciw"] > 1.0 for h in headline)
    p99_populated = all(
        row["p99"] is not None
        and row["p99_ci_low"] is not None
        and row["p99_ci_high"] is not None
        for row in stats
    )
    confirm = spine_unchanged and tail_is_heavy and tail_ci_wider and p99_populated
    verdict = "CONFIRMS C1-for-SERVICE" if confirm else "REFUTES / INCONCLUSIVE"

    payload = {
        "claim_id": "SERVICE-REGIME",
        "verdict": verdict,
        "spine_unchanged": spine_unchanged,
        "spine_digests_before": before,
        "spine_digests_after": after,
        "rates": RATES,
        "duration_s": DURATION_S,
        "correctness_gates": gates,
        "validity_gates": val_gates,
        "headline": headline,
        "criteria": {
            "spine_unchanged": spine_unchanged,
            "tail_is_heavy_p99_over_median_gt_3": tail_is_heavy,
            "p99_ci_wider_than_median_ci": tail_ci_wider,
            "p99_and_ci_populated": p99_populated,
        },
    }
    (RESULTS / "verdict.json").write_text(json.dumps(payload, indent=2))

    # --- console report -----------------------------------------------------
    print()
    print(report.format_table(stats, x_key="rate"))
    print()
    print(f"{'rate':>6}{'n':>8}{'median(ms)':>13}{'p99(ms)':>11}"
          f"{'p99/median':>13}{'medCIw(ms)':>13}{'p99CIw(ms)':>13}{'p99CIw/medCIw':>15}")
    for h in headline:
        print(
            f"{h['rate']:>6}{h['n']:>8}{h['median_s']*1e3:>13.3f}{h['p99_s']*1e3:>11.3f}"
            f"{h['p99_over_median']:>13.1f}{h['median_ci_width_s']*1e3:>13.4f}"
            f"{h['p99_ci_width_s']*1e3:>13.4f}{h['p99_ciw_over_median_ciw']:>15.1f}"
        )
    print()
    print(f"spine byte-identical (core/stats/report): {spine_unchanged}")
    print(f"VERDICT: {verdict}")
    print(f"Artifacts written to {RESULTS}/")
    print("  raw_samples.json  stats.json  verdict.json  latency_scaling.png")


if __name__ == "__main__":
    main()
