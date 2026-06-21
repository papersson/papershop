"""Attack on the correctness gate: APPROXIMATE-RANDOMIZED-CORRECTNESS-GATE.

Run from the repo root:  uv run python experiments/approx_correctness/run.py

The gate at core.py:114-122 admits only bit-identical outputs (sha256(repr(out))
equality). This experiment shows that an approximate nearest-neighbor target --
two implementations both correct by the domain's real test (recall@k vs ground
truth) -- cannot be placed by that gate. Four steps:

  (A) measure recall@10 of approx vs exact, assert >= 0.90 (both domain-correct);
  (B) run_suite([exact, approx], grid) and capture the ValueError the gate raises;
  (C) show a stochastic probe digests differently across two calls (not even
      self-consistent under the gate);
  (D) bypass the gate by running each probe ALONE, then aggregate() the approx
      samples and show a full summary WITH a bootstrap CI -- a confident
      performance number carrying zero correctness guarantee.

The spine is NOT modified (this is an attack, not a fix). run.py prints a sha256
of each spine file before and after to prove byte-identity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import target

from harness.core import _digest, run_suite
from harness.stats import aggregate

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "approx_correctness"
SPINE = [
    ROOT / "src" / "harness" / "core.py",
    ROOT / "src" / "harness" / "stats.py",
    ROOT / "src" / "harness" / "report.py",
]


def spine_hashes() -> dict:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in SPINE}


def recall_at_k(approx: list[list[int]], exact: list[list[int]]) -> float:
    hit = total = 0
    for a, e in zip(approx, exact):
        es = set(e)
        hit += len(es.intersection(a))
        total += len(es)
    return hit / total


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    params = target.param_grid[0]
    before = spine_hashes()
    report: dict = {
        "claim_id": "APPROXIMATE-RANDOMIZED-CORRECTNESS-GATE",
        "params": params,
        "spine_sha256_before": before,
    }

    # --- (A) both implementations are correct by the domain's real test -------
    fx = target.build_dataset(params)
    exact_out = target.exact_topk(fx)
    approx_out = target.approx_topk(fx)
    recall = recall_at_k(approx_out, exact_out)
    domain_correct = recall >= 0.90
    report["A_recall_at_k"] = {
        "k": target.K,
        "recall": recall,
        "threshold": 0.90,
        "both_domain_correct": domain_correct,
        "outputs_bit_identical": exact_out == approx_out,
    }
    print(f"(A) recall@{target.K} of approx vs exact = {recall:.4f} "
          f"(>= 0.90: {domain_correct}); outputs identical: {exact_out == approx_out}")

    # --- (B) the gate refuses to compare the two correct-in-distribution probes
    gate_raised = False
    gate_message = None
    try:
        run_suite(target.probes, target.param_grid, repetitions=5)
    except ValueError as e:
        gate_raised = True
        gate_message = str(e)
    report["B_gate"] = {
        "value_error_raised": gate_raised,
        "message": gate_message,
        "is_correctness_gate": bool(gate_message and "CORRECTNESS GATE FAILED" in gate_message),
    }
    print(f"(B) run_suite([exact, approx]) raised ValueError: {gate_raised}")
    if gate_message:
        print(f"    -> {gate_message.splitlines()[0]}")

    # --- (C) a stochastic probe is not even self-consistent under the gate ----
    d1 = _digest(target.approx_stochastic.invoke(fx))
    d2 = _digest(target.approx_stochastic.invoke(fx))
    report["C_self_consistency"] = {
        "digest_call_1": d1,
        "digest_call_2": d2,
        "digests_differ": d1 != d2,
    }
    print(f"(C) stochastic probe digests: {d1} vs {d2} -> differ: {d1 != d2}")

    # --- (D) bypass: run each probe ALONE; aggregate still emits a full CI -----
    # A single-probe list never trips the gate (no sibling to disagree with).
    approx_samples = run_suite([target.approx], target.param_grid, repetitions=40)
    exact_samples = run_suite([target.exact], target.param_grid, repetitions=40)
    all_samples = approx_samples + exact_samples
    (RESULTS / "raw_samples.json").write_text(json.dumps(all_samples, indent=2))

    stats = aggregate(all_samples)
    (RESULTS / "stats.json").write_text(json.dumps(stats, indent=2))
    approx_summary = next(s for s in stats if s["probe"] == "approx")
    report["D_bypass"] = {
        "single_probe_gate_tripped": False,
        "approx_summary_has_ci": "ci_low" in approx_summary and "ci_high" in approx_summary,
        "approx_median_s": approx_summary["median"],
        "approx_ci_low_s": approx_summary["ci_low"],
        "approx_ci_high_s": approx_summary["ci_high"],
        "correctness_guarantee_attached": False,
    }
    print(f"(D) approx alone -> full summary with CI: median={approx_summary['median']*1e9:,.0f} ns "
          f"CI=[{approx_summary['ci_low']*1e9:,.0f}, {approx_summary['ci_high']*1e9:,.0f}] ns "
          f"-- no correctness guarantee attached")

    # --- spine byte-identity proof + verdict ----------------------------------
    after = spine_hashes()
    report["spine_sha256_after"] = after
    report["spine_unchanged"] = before == after

    confirmed = (
        domain_correct
        and report["B_gate"]["is_correctness_gate"]
        and report["C_self_consistency"]["digests_differ"]
        and report["D_bypass"]["approx_summary_has_ci"]
    )
    report["verdict"] = "CONFIRMED" if confirmed else "REFUTED"
    (RESULTS / "report.json").write_text(json.dumps(report, indent=2))

    from harness.report import format_table  # spine reporter, unchanged
    print()
    print(format_table(stats, x_key="m"))
    print()
    print(f"spine unchanged (byte-identical): {before == after}")
    print(f"VERDICT: {report['verdict']}")
    print(f"Artifacts written to {RESULTS}/")
    print("  raw_samples.json  stats.json  report.json")


if __name__ == "__main__":
    main()
