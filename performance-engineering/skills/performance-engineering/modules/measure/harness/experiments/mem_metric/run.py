"""Falsification test: does the spine's raw-sample schema generalize past seconds?

Claim under attack (NONTIME-METRIC): "the schema generalizes past seconds without
a spine rewrite." Predicted outcome: REFUTATION, because ``stats.aggregate`` reads
``s["seconds_per_op"]`` (stats.py:97) and nothing in the spine carries a
metric/unit or a metric-neutral value channel.

Procedure:
  STEP 0  hash the three spine files (we must not edit them).
  STEP 1  feed HONEST bytes samples (metric=peak_rss_bytes, value in bytes)
          straight into aggregate(). Record what happens (expect KeyError).
  STEP 2  probe the only spine-free workaround: copy the same bytes into a
          ``seconds_per_op`` field and re-run aggregate(). Record whether it
          "succeeds" while silently mislabeling bytes as seconds.
  STEP 3  re-hash the spine files; confirm byte-identity (no edits were made).

Run from the repo root:  uv run python experiments/mem_metric/run.py
"""

from __future__ import annotations

import hashlib
import json
import traceback
from pathlib import Path

import target  # same directory; on sys.path because this file is the entrypoint

from harness.stats import aggregate

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "mem_metric"
SPINE = [
    ROOT / "src" / "harness" / "core.py",
    ROOT / "src" / "harness" / "stats.py",
    ROOT / "src" / "harness" / "report.py",
]


def _hash_spine() -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in SPINE}


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)

    # STEP 0 ---------------------------------------------------------------
    before = _hash_spine()

    # Measure honest non-time samples (peak RSS in bytes).
    samples = target.measure_samples()
    (RESULTS / "raw_samples.json").write_text(json.dumps(samples, indent=2))

    findings: list[str] = []
    findings.append("NONTIME-METRIC falsification test")
    findings.append("=" * 60)
    findings.append("")
    findings.append("Honest sample shape (no seconds_per_op key):")
    findings.append("  " + json.dumps(samples[0]))
    findings.append("")

    # STEP 1: honest samples straight into the spine ----------------------
    findings.append("STEP 1 — feed honest bytes samples to aggregate() unchanged")
    findings.append("-" * 60)
    step1_branch = None
    try:
        stats = aggregate(samples)
        # If we get here the claim is CONFIRMED — the spine ingested bytes.
        step1_branch = "CONFIRMED"
        (RESULTS / "stats.json").write_text(json.dumps(stats, indent=2))
        findings.append(
            "aggregate() ACCEPTED honest bytes samples and produced summary "
            "stats with zero spine edits. Claim CONFIRMED."
        )
    except KeyError as e:
        step1_branch = "KeyError"
        findings.append(
            f"aggregate() raised KeyError({e!r}). The honest non-time sample "
            "cannot pass through the spine at all: 'seconds_per_op' is baked in."
        )
        findings.append("")
        findings.append("Traceback:")
        findings.append(traceback.format_exc().rstrip())
    findings.append("")

    # STEP 2: the only spine-free workaround — lie about units ------------
    findings.append("STEP 2 — re-map bytes into seconds_per_op and re-run")
    findings.append("-" * 60)
    lied = [
        {
            "probe": s["probe"],
            "params": s["params"],
            "rep": s["rep"],
            "batch": s["batch"],
            "seconds_per_op": s["value"],  # bytes stuffed into a seconds field
        }
        for s in samples
    ]
    step2_branch = None
    try:
        lied_stats = aggregate(lied)
        step2_branch = "units-lie-accepted"
        (RESULTS / "stats_units_lie.json").write_text(json.dumps(lied_stats, indent=2))
        findings.append(
            "aggregate() ACCEPTED the mislabeled samples WITHOUT complaint. It "
            "now reports median/min/p99/CI of BYTES under field names that mean "
            "SECONDS. No guard objected. The 'summary' below is bytes wearing a "
            "seconds label:"
        )
        findings.append("")
        for r in sorted(lied_stats, key=lambda r: r["params"]["size_mb"]):
            findings.append(
                f"  size_mb={r['params']['size_mb']:>4}  "
                f"median={r['median']:,.0f} (bytes, labelled 'seconds')  "
                f"p99={r['p99']:,.0f}  "
                f"CI=[{r['ci_low']:,.0f}, {r['ci_high']:,.0f}]"
            )
    except Exception as e:  # noqa: BLE001 - record whatever happened
        step2_branch = f"rejected:{type(e).__name__}"
        findings.append(f"aggregate() rejected the mislabeled samples: {e!r}")
    findings.append("")

    # STEP 3: confirm the spine was never touched -------------------------
    after = _hash_spine()
    findings.append("STEP 3 — spine byte-identity (no edits were made)")
    findings.append("-" * 60)
    spine_unchanged = before == after
    for name in before:
        same = "identical" if before[name] == after[name] else "CHANGED"
        findings.append(f"  {name:<10} {same}  {before[name][:16]}...")
    findings.append("")

    # Verdict -------------------------------------------------------------
    findings.append("=" * 60)
    if step1_branch == "CONFIRMED":
        verdict = (
            "CONFIRMED: the schema generalizes past seconds with no spine rewrite."
        )
    elif (
        step1_branch == "KeyError"
        and step2_branch == "units-lie-accepted"
        and spine_unchanged
    ):
        verdict = (
            "REFUTED (as predicted, and productive): a non-time headline metric "
            "cannot flow through the spine honestly — aggregate() KeyErrors on the "
            "honest sample because 'seconds_per_op' is hardcoded (stats.py:97). The "
            "only spine-free path is to mislabel bytes as seconds, which aggregate() "
            "accepts silently. The schema carries no metric/unit and there is no "
            "metric-neutral value channel, so the Q0 metric-type gate is unenforced. "
            "This motivates the PROVENANCE spine evolution: add metric/unit + a "
            "neutral 'value' channel, and have aggregate() refuse to pool mismatched "
            "units."
        )
    else:
        verdict = (
            f"INCONCLUSIVE: step1={step1_branch}, step2={step2_branch}, "
            f"spine_unchanged={spine_unchanged}. Inspect transcript above."
        )
    findings.append("VERDICT: " + verdict)

    text = "\n".join(findings) + "\n"
    (RESULTS / "findings.txt").write_text(text)
    print(text)
    print(f"Artifacts written to {RESULTS}/")


if __name__ == "__main__":
    main()
