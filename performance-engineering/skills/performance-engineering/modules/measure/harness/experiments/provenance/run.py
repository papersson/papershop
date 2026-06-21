"""PROVENANCE: attack the metric-neutral spine evolution with three predictions.

The spine (stats.py) was evolved additively: a metric-neutral ``value`` channel
(falling back to ``seconds_per_op``), provenance fields carried through, and a
refusal to pool a (probe, params) group whose samples disagree on provenance.
This script tries to break that evolution three ways:

  P1  back-compat / C1 not broken: re-aggregating every existing experiment's
      raw_samples.json yields BYTE-IDENTICAL values for every pre-existing
      summary field. Any change = the evolution mutated behaviour = a hack.
  P2  honesty as a hard error: a group mixing unit=seconds and unit=bytes must
      raise a clear ValueError, not silently pool (the stats.py:97 units-lie).
  P3  non-time flow: a unit=bytes / value-channel batch must aggregate without
      KeyError and stay LABELLED bytes (not relabelled seconds).

Refuted if P1 changes any pre-existing field, OR P2 silently pools, OR P3
KeyErrors or mislabels bytes. Run:  uv run python experiments/provenance/run.py
"""

from __future__ import annotations

import json
from pathlib import Path

import target  # same directory; on sys.path because this file is the entrypoint

from harness.stats import aggregate

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "provenance"

# The pre-existing summary fields that MUST be byte-identical after the evolution.
PREEXISTING_FIELDS = [
    "probe", "params", "n", "min", "median", "mean", "stdev", "p90", "p99",
    "ci_low", "ci_high", "p90_ci_low", "p90_ci_high", "p99_ci_low", "p99_ci_high",
]
LEGACY_EXPERIMENTS = ["membership", "cli_search", "service_regime"]


def _key(row: dict) -> str:
    return f"{row['probe']}|{json.dumps(row['params'], sort_keys=True)}"


def _preexisting(row: dict) -> dict:
    return {k: row[k] for k in PREEXISTING_FIELDS}


def check_p1_back_compat() -> tuple[bool, dict]:
    """Re-aggregate each legacy experiment; diff pre-existing fields vs baseline."""
    baseline = json.loads((RESULTS / "baseline_summaries.json").read_text())
    diff: dict = {}
    for name in LEGACY_EXPERIMENTS:
        samples = json.loads((ROOT / "results" / name / "raw_samples.json").read_text())
        now = {_key(r): _preexisting(r) for r in aggregate(samples)}
        base = {_key(r): _preexisting(r) for r in baseline[name]}
        exp_diff = {}
        for k in set(now) | set(base):
            a = json.dumps(base.get(k), sort_keys=True)
            b = json.dumps(now.get(k), sort_keys=True)
            if a != b:
                exp_diff[k] = {"baseline": base.get(k), "evolved": now.get(k)}
        if exp_diff:
            diff[name] = exp_diff
    return (len(diff) == 0), diff


def check_p2_refusal() -> tuple[bool, str]:
    """A unit-mismatched group must raise a clear ValueError."""
    group = target.mismatched_unit_group()
    try:
        aggregate(group)
    except ValueError as e:
        return True, f"ValueError: {e}"
    except Exception as e:  # noqa: BLE001
        return False, f"WRONG EXCEPTION {type(e).__name__}: {e}"
    return False, "NO EXCEPTION: aggregate() silently pooled mismatched units"


def check_p3_nontime() -> tuple[bool, list, str]:
    """A bytes/value-channel batch must aggregate, stay bytes, be in byte-range."""
    samples = target.bytes_samples()
    try:
        stats = aggregate(samples)
    except KeyError as e:
        return False, [], f"KeyError on honest bytes sample: {e!r}"
    units = {r["unit"] for r in stats}
    metrics = {r["metric"] for r in stats}
    medians = [r["median"] for r in stats]
    in_byte_range = all(1e6 <= m <= 1e12 for m in medians)
    ok = units == {"bytes"} and metrics == {"peak_rss_bytes"} and in_byte_range
    note = (
        f"units={sorted(units)} metrics={sorted(metrics)} "
        f"medians={[f'{m:,.0f}' for m in medians]} byte_range_ok={in_byte_range}"
    )
    return ok, stats, note


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    if not (RESULTS / "baseline_summaries.json").exists():
        raise SystemExit(
            "baseline_summaries.json missing: it must be captured with the "
            "PRE-edit aggregate before the spine is evolved."
        )

    lines: list[str] = ["PROVENANCE spine-evolution falsification", "=" * 60, ""]

    # P1 -----------------------------------------------------------------
    p1_ok, p1_diff = check_p1_back_compat()
    (RESULTS / "back_compat_diff.json").write_text(json.dumps(p1_diff, indent=2))
    lines += [
        "P1 back-compat (byte-identical pre-existing fields, all 3 legacy expts)",
        "-" * 60,
        f"  result: {'PASS (empty diff)' if p1_ok else 'FAIL'}",
        f"  experiments checked: {LEGACY_EXPERIMENTS}",
        f"  diff written to back_compat_diff.json ({len(p1_diff)} experiment(s) differ)",
        "",
    ]

    # P2 -----------------------------------------------------------------
    p2_ok, p2_msg = check_p2_refusal()
    (RESULTS / "refusal_log.txt").write_text(p2_msg + "\n")
    lines += [
        "P2 refusal on mismatched provenance (units-lie -> hard error)",
        "-" * 60,
        f"  result: {'PASS' if p2_ok else 'FAIL'}",
        f"  {p2_msg}",
        "",
    ]

    # P3 -----------------------------------------------------------------
    p3_ok, p3_stats, p3_note = check_p3_nontime()
    if p3_stats:
        (RESULTS / "bytes_summary.json").write_text(json.dumps(p3_stats, indent=2))
    lines += [
        "P3 non-time flow (value channel, unit=bytes, labelled bytes)",
        "-" * 60,
        f"  result: {'PASS' if p3_ok else 'FAIL'}",
        f"  {p3_note}",
        "",
    ]

    # Verdict ------------------------------------------------------------
    all_ok = p1_ok and p2_ok and p3_ok
    lines += ["=" * 60]
    if all_ok:
        lines.append(
            "VERDICT: CONFIRMED. The evolution is additive (P1 byte-identical), "
            "honest (P2 refuses mismatched units), and metric-neutral (P3 carries "
            "bytes without KeyError or relabelling). C1 preserved; NONTIME-METRIC "
            "and the units-lie are fixed by deliberate infrastructure, not a hack."
        )
    else:
        lines.append(
            f"VERDICT: REFUTED. P1={p1_ok} P2={p2_ok} P3={p3_ok}. "
            "Inspect the failing prediction above."
        )

    text = "\n".join(lines) + "\n"
    (RESULTS / "findings.txt").write_text(text)
    print(text)
    print(f"Artifacts written to {RESULTS}/")
    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
