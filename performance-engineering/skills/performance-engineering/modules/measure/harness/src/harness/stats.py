"""The aggregator: raw samples in, honest statistics out.

It reads the raw-sample schema from ``core`` and emits a summary schema that the
reporter reads. It reports the *median* (robust to the occasional slow sample
from a scheduler hiccup) with a bootstrap confidence interval, plus the spread,
so a reader can see not just the central estimate but how trustworthy it is.

Summary schema (one dict per probe/param group):

    {
        "probe":   str,
        "params":  dict,
        "n":       int,     # number of raw samples
        "min":     float,   # often the cleanest estimate of true cost
        "median":  float,
        "mean":    float,
        "stdev":   float,
        "p90":     float,
        "p99":     float,
        "ci_low":  float,   # 95% bootstrap CI for the median
        "ci_high": float,
        "p90_ci_low":  float,   # 95% bootstrap CI for p90 (the tail-CI rule)
        "p90_ci_high": float,
        "p99_ci_low":  float,   # 95% bootstrap CI for p99
        "p99_ci_high": float,
        # --- provenance (additive; carried through from the raw samples) ---
        "metric":           str,   # what was measured, e.g. "seconds_per_op", "peak_rss_bytes"
        "unit":             str,   # the unit the numbers above are in, e.g. "seconds", "bytes"
        "clock":            str,   # measurement source, e.g. "wall", "cpu"
        "includes_startup": bool,  # did the measurement include process startup?
        "overhead_removed": bool,  # was a measured loop/timer overhead subtracted?
    }

Provenance and the metric-neutral value channel
-----------------------------------------------
A raw sample carries its measurement in a metric-neutral ``value`` key when the
metric is not time; legacy samples that predate that channel carry it in
``seconds_per_op`` instead. ``_value`` reads ``value`` and falls back to
``seconds_per_op``, so every pre-existing ``raw_samples.json`` flows through
unchanged. Each sample may also declare its provenance — ``unit``, ``clock``,
``includes_startup``, ``overhead_removed`` (with time-defaults for legacy
samples). ``aggregate`` refuses to pool a ``(probe, params)`` group whose samples
disagree on that provenance: pooling bytes with seconds, or warm with
cold-start, is a category error, so it raises ``ValueError`` rather than emit a
number that silently averages incompatible measurements.

The tail percentiles (p90/p99) carry their *own* bootstrap CIs, not the median's.
A median CI is far too narrow to describe a tail: when a reader's headline is a
tail statistic, banding it with the median's CI is misleading (see
``results/tail_ci`` and the tail-CI rule in THEORY.md). ``bootstrap_ci_quantile``
is the general statistic; ``bootstrap_ci_median`` is the ``q=0.5`` special case.
"""

from __future__ import annotations

import json
import random
import statistics


def _percentile(xs: list[float], p: float) -> float:
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def _bootstrap_ci(xs, stat, *, iters: int, alpha: float, seed: int):
    """Percentile bootstrap CI for an arbitrary statistic ``stat(resample)``.

    Resamples the data with replacement many times to estimate how much the
    statistic would wobble if the experiment were repeated, then takes the
    central ``1-alpha`` band of those resampled values. No distributional
    assumptions — appropriate for timing data, which is rarely normal. This is
    the one recipe behind every CI we report; only ``stat`` changes.
    """
    rng = random.Random(seed)
    n = len(xs)
    vals = []
    for _ in range(iters):
        resample = [xs[rng.randrange(n)] for _ in range(n)]
        vals.append(stat(resample))
    return _percentile(vals, alpha / 2), _percentile(vals, 1 - alpha / 2)


def bootstrap_ci_median(
    xs: list[float], *, iters: int = 2000, alpha: float = 0.05, seed: int = 1
) -> tuple[float, float]:
    """Percentile bootstrap 95% confidence interval for the median."""
    return _bootstrap_ci(xs, statistics.median, iters=iters, alpha=alpha, seed=seed)


def bootstrap_ci_quantile(
    xs: list[float], q: float, *, iters: int = 2000, alpha: float = 0.05, seed: int = 1
) -> tuple[float, float]:
    """Percentile bootstrap 95% CI for the ``q``-quantile (e.g. q=0.99 for p99).

    The tail-CI rule made general: when the headline is a tail percentile, band
    *that* percentile, never the median. ``bootstrap_ci_quantile(xs, 0.5)``
    coincides with ``bootstrap_ci_median(xs)`` (``_percentile`` at 0.5 is the
    median), so this subsumes the median case rather than competing with it.
    """
    return _bootstrap_ci(
        xs, lambda r: _percentile(r, q), iters=iters, alpha=alpha, seed=seed
    )


def ratio_of_totals_ci(
    nums: list[float],
    dens: list[float],
    *,
    iters: int = 2000,
    alpha: float = 0.05,
    seed: int = 1,
) -> tuple[float, float]:
    """Paired bootstrap 95% CI for a ratio-of-totals headline (throughput etc.).

    A ratio metric (requests/second, hit-rate, error-rate, utilization) is
    ``sum(num) / sum(den)`` — the denominator-weighted answer — NOT the mean or
    median of the per-window rates ``num_i/den_i``, which is biased whenever the
    denominators vary. The CI must keep each ``(num_i, den_i)`` together:
    resample whole *pairs* with replacement and recompute the ratio of the
    resampled totals, so the spread reflects the real uncertainty of the
    estimator. (Resampling the rate list instead is the trap this fixes.) Uses
    the same percentile convention as every other CI here.
    """
    rng = random.Random(seed)
    n = len(nums)
    ratios = []
    for _ in range(iters):
        sn = 0.0
        sd = 0.0
        for _ in range(n):
            j = rng.randrange(n)
            sn += nums[j]
            sd += dens[j]
        ratios.append(sn / sd)
    ratios.sort()
    return _percentile(ratios, alpha / 2.0), _percentile(ratios, 1.0 - alpha / 2.0)


# Provenance defaults for legacy samples that predate the provenance fields.
# A pre-provenance sample is, by construction, a time measurement.
_PROV_DEFAULTS = {
    "metric": "seconds_per_op",
    "unit": "seconds",
    "clock": "wall",
    "includes_startup": False,
    "overhead_removed": False,
}

# Fields that decide whether two samples may be pooled. ``metric`` is excluded
# on purpose: it is a label carried alongside, while ``unit`` is the thing that
# makes numbers (in)commensurable. In practice they agree, but unit is the
# load-bearing guard.
_POOL_KEYS = ("unit", "clock", "includes_startup", "overhead_removed")


def _value(s: dict) -> float:
    """The metric-neutral measurement channel.

    Prefers the explicit ``value`` key (whatever the metric), and falls back to
    the legacy ``seconds_per_op`` so every pre-provenance ``raw_samples.json``
    still flows through aggregate() unchanged.
    """
    return s["value"] if "value" in s else s["seconds_per_op"]


def _provenance(s: dict) -> dict:
    """The provenance a sample declares, with time-defaults filled in."""
    return {k: s.get(k, _PROV_DEFAULTS[k]) for k in _PROV_DEFAULTS}


def _is_ratio(s: dict) -> bool:
    """A sample is a ratio measurement iff it carries both totals channels."""
    return "numerator" in s and "denominator" in s


def aggregate(samples: list[dict]) -> list[dict]:
    """Group raw samples by (probe, params) and compute summary statistics.

    Refuses to pool a group whose samples disagree on provenance (unit, clock,
    includes_startup, overhead_removed) or on ``batch`` size: such a pool would
    average incommensurable measurements, so it raises ``ValueError`` instead.

    A group whose every sample carries the ratio channels (``numerator`` and
    ``denominator``) is a ratio-of-totals metric (throughput, hit-rate, …): its
    headline is ``sum(num)/sum(den)`` with a paired bootstrap CI, NOT the median
    of per-window rates (which is biased when denominators vary). Such rows are
    flagged ``is_ratio``; the central estimate and CI carry the honest ratio, and
    the biased per-rate estimators are kept as ``naive_*`` for contrast.
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for s in samples:
        key = (s["probe"], json.dumps(s["params"], sort_keys=True))
        groups.setdefault(key, []).append(s)

    out: list[dict] = []
    for (probe, params_json), members in groups.items():
        provs = [_provenance(s) for s in members]
        seen = {tuple(p[k] for k in _POOL_KEYS) for p in provs}
        if len(seen) > 1:
            raise ValueError(
                f"refusing to pool mismatched provenance in group "
                f"{probe}/{params_json}: {sorted(seen)} (keys {_POOL_KEYS})"
            )
        batches = {s["batch"] for s in members if "batch" in s}
        if len(batches) > 1:
            raise ValueError(
                f"refusing to pool mismatched batch sizes in group "
                f"{probe}/{params_json}: {sorted(batches)}. Samples averaged over "
                f"different batch counts carry different variance and cannot share "
                f"one bootstrap; measure the group at a single batch size, or "
                f"slope-fit across batches deliberately."
            )
        prov = provs[0]
        params = json.loads(params_json)
        xs = [_value(s) for s in members]

        if members and all(_is_ratio(s) for s in members):
            nums = [s["numerator"] for s in members]
            dens = [s["denominator"] for s in members]
            ratio = sum(nums) / sum(dens)
            r_lo, r_hi = ratio_of_totals_ci(nums, dens)
            out.append(
                {
                    "probe": probe,
                    "params": params,
                    "n": len(members),
                    "is_ratio": True,
                    "ratio": ratio,
                    "ratio_ci_low": r_lo,
                    "ratio_ci_high": r_hi,
                    "naive_median_of_rates": statistics.median(xs),
                    "naive_mean_of_rates": statistics.fmean(xs),
                    # central estimate + CI = the honest ratio, so a reader (or
                    # report.py) that asks for the headline gets the right number.
                    "median": ratio,
                    "ci_low": r_lo,
                    "ci_high": r_hi,
                    "min": min(xs),
                    "mean": ratio,
                    "stdev": statistics.pstdev(xs),
                    "metric": prov["metric"],
                    "unit": prov["unit"],
                    "clock": prov["clock"],
                    "includes_startup": prov["includes_startup"],
                    "overhead_removed": prov["overhead_removed"],
                }
            )
            continue

        lo, hi = bootstrap_ci_median(xs)
        p90_lo, p90_hi = bootstrap_ci_quantile(xs, 0.90)
        p99_lo, p99_hi = bootstrap_ci_quantile(xs, 0.99)
        out.append(
            {
                "probe": probe,
                "params": params,
                "n": len(xs),
                "min": min(xs),
                "median": statistics.median(xs),
                "mean": statistics.fmean(xs),
                "stdev": statistics.pstdev(xs),
                "p90": _percentile(xs, 0.90),
                "p99": _percentile(xs, 0.99),
                "ci_low": lo,
                "ci_high": hi,
                "p90_ci_low": p90_lo,
                "p90_ci_high": p90_hi,
                "p99_ci_low": p99_lo,
                "p99_ci_high": p99_hi,
                "metric": prov["metric"],
                "unit": prov["unit"],
                "clock": prov["clock"],
                "includes_startup": prov["includes_startup"],
                "overhead_removed": prov["overhead_removed"],
            }
        )
    return out
