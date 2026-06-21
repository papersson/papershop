"""Target for the tail-CI stress test (claim C2-tail).

This "target" is not a piece of software under test — it is a *generative model
of heavy-tailed timing data*. The thing under test is the spine's default
statistic (median + bootstrap CI from ``stats.aggregate``) when a reader uses a
TAIL headline (p99) instead of the center.

It exposes:
  - two heavy-tailed seconds_per_op models (a realistic bimodal GC/scheduler-tail
    model and a single fat lognormal, for robustness);
  - a deterministic sampler that emits raw samples in the load-bearing schema;
  - ``bootstrap_ci_quantile`` — the REFERENCE tail-CI recipe, defined ONLY here,
    never in the spine. It is the same percentile-bootstrap as the spine's
    ``bootstrap_ci_median`` but for an arbitrary quantile.

Nothing here imports or mutates the spine; ``run.py`` feeds the samples straight
into the unmodified ``harness.stats.aggregate``.
"""

from __future__ import annotations

import math
import random

# --- generative models of heavy-tailed timing -----------------------------
#
# Each model is a function (rng) -> seconds_per_op for one operation.
# Scales are in seconds; ~1 microsecond fast path, with a slow tail.

FAST_MEAN = 1.0e-6  # ~1 microsecond typical fast op
SLOW_FACTOR = 10.0  # slow path is ~10x the fast path


def _lognormal_from_mean(rng: random.Random, mean: float, sigma: float) -> float:
    """Draw lognormal with a given *arithmetic mean* and log-space sigma.

    For a lognormal, mean = exp(mu + sigma^2/2), so mu = ln(mean) - sigma^2/2.
    Parameterizing by the arithmetic mean keeps the scales interpretable.
    """
    mu = math.log(mean) - sigma * sigma / 2.0
    return rng.lognormvariate(mu, sigma)


def model_bimodal(rng: random.Random) -> float:
    """95% fast lognormal + 5% slow lognormal — a GC/scheduler-hiccup tail."""
    if rng.random() < 0.05:
        return _lognormal_from_mean(rng, FAST_MEAN * SLOW_FACTOR, 0.5)
    return _lognormal_from_mean(rng, FAST_MEAN, 0.25)


def model_fat_lognormal(rng: random.Random) -> float:
    """A single fat lognormal (sigma=1.5): smoothly heavy-tailed, no second mode."""
    return _lognormal_from_mean(rng, FAST_MEAN, 1.5)


MODELS = {
    "bimodal_5pct_slow": model_bimodal,
    "fat_lognormal_s1.5": model_fat_lognormal,
}


def draw(model, rng: random.Random, n: int) -> list[float]:
    """Draw ``n`` seconds_per_op values from a model with the given RNG."""
    return [model(rng) for _ in range(n)]


def make_raw_samples(xs: list[float], *, probe: str, params: dict) -> list[dict]:
    """Wrap raw seconds_per_op values in the load-bearing raw-sample schema.

    One dict per measurement: {probe, params, rep, batch, seconds_per_op}.
    This is exactly what the spine's ``aggregate`` consumes, so feeding these in
    re-exercises C1 (a new target needs only data in the schema, not spine edits).
    """
    return [
        {"probe": probe, "params": params, "rep": i, "batch": 1, "seconds_per_op": x}
        for i, x in enumerate(xs)
    ]


# --- reference tail-CI statistic (lives ONLY in the experiment) ------------


def _percentile(xs: list[float], p: float) -> float:
    """Linear-interpolated percentile — identical recipe to the spine's."""
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def bootstrap_ci_quantile(
    xs: list[float],
    q: float = 0.99,
    *,
    iters: int = 2000,
    alpha: float = 0.05,
    seed: int = 1,
) -> tuple[float, float]:
    """Percentile bootstrap 95% CI for an arbitrary quantile ``q``.

    The same recipe as ``harness.stats.bootstrap_ci_median`` (resample with
    replacement, recompute the statistic, take its 2.5/97.5 percentiles), but
    for the q-quantile instead of the median. Defined here as the *reference*
    the spine's median band is measured against; if the experiment confirms the
    gap, this is the function proposed for promotion into stats.py.

    Vectorized with numpy for speed (it is called once per simulated experiment).
    numpy's default 'linear' interpolation matches the spine's ``_percentile``,
    so the recipe is identical to ``bootstrap_ci_median`` apart from the quantile.
    """
    import numpy as np

    arr = np.asarray(xs, dtype=float)
    n = arr.size
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(iters, n))
    resampled = arr[idx]  # (iters, n)
    qs = np.quantile(resampled, q, axis=1)  # one q-quantile per resample
    lo, hi = np.quantile(qs, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)
