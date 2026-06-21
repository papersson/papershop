"""Batch-homogeneity enforcement probe against the spine's aggregate().

Claim under attack (BATCH-HOMOGENEITY): THEORY.md states "all samples in a group
share a batch" as an invariant, but the spine never enforces it. ``aggregate()``
groups by (probe, params) and guards only the provenance pool-keys
(unit, clock, includes_startup, overhead_removed); ``batch`` lives in the
raw-sample schema yet is never read.

Part A  enforcement probe: does aggregate(mixed batch) raise? (prediction: no)
Part B  harm: pooled n=120 with a CI that misrepresents both cohorts.
Part C  control: homogeneous group is fine; a unit mismatch DOES raise, proving
        the guard machinery works and only the batch dimension is unguarded.

Spine is READ-ONLY this iteration: we only call aggregate(). Any fix (adding a
batch-homogeneity guard parallel to _POOL_KEYS) is proposed in the writeup.
"""

from __future__ import annotations

import copy
import json
import random
from pathlib import Path

from harness.stats import aggregate

import sys

sys.path.insert(0, str(Path(__file__).parent))
from target import cohort_coarse, cohort_fine  # noqa: E402

RESULTS = Path(__file__).resolve().parents[2] / "results" / "batch_homogeneity"


def _try_aggregate(samples):
    """Return (raised: bool, summaries_or_msg)."""
    try:
        return False, aggregate(samples)
    except ValueError as e:
        return True, str(e)


def _ci_width(summary: dict) -> float:
    return summary["ci_high"] - summary["ci_low"]


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    rng = random.Random(0)

    fine = cohort_fine(rng)
    coarse = cohort_coarse(rng)
    mixed = fine + coarse  # one (probe, params) group, two batch sizes

    # --- Part A: enforcement probe -------------------------------------------
    raised_mixed, mixed_out = _try_aggregate(mixed)
    pooled = None
    if not raised_mixed:
        assert len(mixed_out) == 1, "expected a single pooled (probe,params) group"
        pooled = mixed_out[0]

    # --- Part B: homogeneous baselines + harm --------------------------------
    fine_sum = aggregate(fine)[0]
    coarse_sum = aggregate(coarse)[0]

    # --- Part C: controls ----------------------------------------------------
    # C1: a homogeneous group (all batch=1000) aggregates cleanly.
    raised_homog, _ = _try_aggregate(fine)
    # C2: inject a provenance mismatch (one sample in bytes) into an otherwise
    # homogeneous-batch group -> the existing guard must fire.
    prov_mismatch = copy.deepcopy(fine)
    prov_mismatch[0]["unit"] = "bytes"
    raised_unit, unit_msg = _try_aggregate(prov_mismatch)

    # --- persist artifacts ---------------------------------------------------
    (RESULTS / "raw_samples.json").write_text(json.dumps(mixed, indent=2))

    stats_blob = {
        "pooled_mixed": pooled,  # None if it raised
        "baseline_fine": fine_sum,
        "baseline_coarse": coarse_sum,
    }
    (RESULTS / "stats.json").write_text(json.dumps(stats_blob, indent=2))

    findings = {
        "raised": raised_mixed,
        "pooled_n": (pooled["n"] if pooled else None),
        "pooled_median": (pooled["median"] if pooled else None),
        "pooled_ci_width": (_ci_width(pooled) if pooled else None),
        "fine_n": fine_sum["n"],
        "fine_ci_width": _ci_width(fine_sum),
        "coarse_n": coarse_sum["n"],
        "coarse_ci_width": _ci_width(coarse_sum),
        "control_homogeneous_raised": raised_homog,
        "control_unit_mismatch_raised": raised_unit,
        "control_unit_mismatch_msg": unit_msg if raised_unit else None,
    }
    (RESULTS / "findings.json").write_text(json.dumps(findings, indent=2))

    # --- gate + verdict ------------------------------------------------------
    # Validity gate: the harm comparison is only meaningful if the two cohorts
    # share the same TRUE central value (so any CI difference is variance, not
    # bias) and the coarse cohort is genuinely noisier than the fine one. The
    # coarse median is *expected* to wobble (that is the point), so "same central
    # value" means the medians agree within the coarse cohort's OWN CI width, not
    # within an arbitrary absolute tolerance.
    gate_central = abs(fine_sum["median"] - coarse_sum["median"]) < _ci_width(coarse_sum)
    gate_spread = coarse_sum["stdev"] > 5 * fine_sum["stdev"]
    gate_pass = gate_central and gate_spread

    verdict = "REFUTED (invariant unenforced)" if (
        not raised_mixed and pooled and pooled["n"] == 120 and raised_unit
    ) else "CONFIRMED (guard present)" if raised_mixed else "INCONCLUSIVE"

    print("=== BATCH-HOMOGENEITY enforcement probe ===")
    print(f"Part A  aggregate(mixed batch=1+1000) raised ValueError? {raised_mixed}")
    if pooled:
        print(f"        -> pooled silently: n={pooled['n']} "
              f"median={pooled['median']:.4e} "
              f"ci=[{pooled['ci_low']:.4e},{pooled['ci_high']:.4e}] "
              f"width={_ci_width(pooled):.4e}")
    print("Part B  homogeneous baselines:")
    print(f"        fine   (batch=1000) n={fine_sum['n']} "
          f"median={fine_sum['median']:.4e} ci_width={_ci_width(fine_sum):.4e} "
          f"stdev={fine_sum['stdev']:.4e}")
    print(f"        coarse (batch=1)    n={coarse_sum['n']} "
          f"median={coarse_sum['median']:.4e} ci_width={_ci_width(coarse_sum):.4e} "
          f"stdev={coarse_sum['stdev']:.4e}")
    if pooled:
        print(f"        pooled ci_width={_ci_width(pooled):.4e} sits between "
              f"fine={_ci_width(fine_sum):.4e} and coarse={_ci_width(coarse_sum):.4e} "
              f"-> answers neither cohort's question")
    print("Part C  controls:")
    print(f"        homogeneous batch group raised? {raised_homog} (expect False)")
    print(f"        unit-mismatch group raised?     {raised_unit} (expect True)")
    print(f"VALIDITY GATE: central-match={gate_central} spread-mismatch={gate_spread} "
          f"-> {'PASS' if gate_pass else 'FAIL'}")
    print(f"VERDICT: {verdict}")


if __name__ == "__main__":
    main()
