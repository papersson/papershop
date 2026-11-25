"""Target for the i.i.d.-bootstrap blind-spot test (claim IID-BOOTSTRAP).

This "target" is not software under test — it is a *generative model of a
serially correlated timing trajectory*. The thing under attack is the spine's
default resampling assumption: ``stats._bootstrap_ci`` resamples raw samples
i.i.d. (draws indices uniformly with replacement), which presumes the per-op
samples are exchangeable. Real op trajectories often are not: consecutive ops
share drifting cache/GC/thermal/JIT state, so costs are autocorrelated.

Generative model (a stationary, non-exchangeable path):

    latency_i = BASE * exp(z_i),   z_i = rho * z_{i-1} + eps_i,  eps_i ~ N(0, sigma^2)

with z_0 drawn from the stationary distribution N(0, sigma^2 / (1 - rho^2)) so
each run is a fair independent stationary sample path. The marginal of each
latency_i is lognormal with log-median 0, so the TRUE marginal median is exactly
BASE (closed form), cross-checked against a huge i.i.d. reference draw.

It exposes:
  - ``draw`` — a numpy-vectorized stationary AR(1) sampler returning one path of
    seconds_per_op values (rho=0 is the i.i.d. control);
  - ``make_raw_samples`` — wraps a path in the load-bearing raw-sample schema,
    re-exercising C1 (a new target needs only schema-conforming data);
  - ``block_bootstrap_ci_median`` — the REFERENCE moving-block-bootstrap recipe,
    defined ONLY here, never in the spine. It mirrors how ``tail_ci`` kept its
    ``bootstrap_ci_quantile`` reference out of the backbone.

Nothing here imports or mutates the spine; ``run.py`` feeds the samples straight
into the unmodified ``harness.stats.aggregate``.
"""

from __future__ import annotations

import math
import random

import numpy as np

# --- generative model of a correlated trajectory --------------------------

BASE = 1.0e-6  # ~1 microsecond typical op; TRUE marginal median (log-median 0)
SIGMA = 0.4  # innovation / log-space spread

# AR(1) autocorrelation coefficients. rho=0 is the i.i.d. control: the path is
# exchangeable, so the spine's i.i.d. bootstrap must be unbiased there.
RHOS = {
    "iid_rho0.0": 0.0,
    "ar1_rho0.7": 0.7,
    "ar1_rho0.9": 0.9,
}


def draw(rho: float, rng: np.random.Generator, n: int) -> list[float]:
    """Draw one stationary AR(1) trajectory of ``n`` seconds_per_op values.

    z is a stationary AR(1) Gaussian process; z_0 is seeded from the stationary
    distribution N(0, sigma^2/(1-rho^2)) so every path is an independent draw of
    the *same* stationary process (no warmup transient to bias the marginal).
    latency = BASE * exp(z), whose marginal is lognormal with median BASE.
    """
    if rho == 0.0:
        z = rng.normal(0.0, SIGMA, size=n)
    else:
        stat_sd = SIGMA / math.sqrt(1.0 - rho * rho)
        eps = rng.normal(0.0, SIGMA, size=n)
        z = np.empty(n, dtype=float)
        z[0] = rng.normal(0.0, stat_sd)
        for i in range(1, n):
            z[i] = rho * z[i - 1] + eps[i]
    return (BASE * np.exp(z)).tolist()


def true_median() -> float:
    """Closed-form TRUE marginal median: median of lognormal(0, .) is exp(0)=1."""
    return BASE


def make_raw_samples(xs: list[float], *, probe: str, params: dict) -> list[dict]:
    """Wrap a trajectory in the load-bearing raw-sample schema.

    One dict per measurement: {probe, params, rep, batch, seconds_per_op}.
    This is exactly what the spine's ``aggregate`` consumes, so feeding these in
    re-exercises C1 (a new target needs only data in the schema, not spine edits).
    ``rep`` preserves trajectory order, which is what the block bootstrap relies on.
    """
    return [
        {"probe": probe, "params": params, "rep": i, "batch": 1, "seconds_per_op": x}
        for i, x in enumerate(xs)
    ]


# --- reference block-bootstrap statistic (lives ONLY in the experiment) ----


def default_block_len(n: int) -> int:
    """L ~ round(n**(1/3)): a few correlation lengths, the textbook MBB rate."""
    return max(2, round(n ** (1.0 / 3.0)))


def block_bootstrap_ci_median(
    xs: list[float],
    *,
    block_len: int | None = None,
    iters: int = 2000,
    alpha: float = 0.05,
    seed: int = 1,
) -> tuple[float, float]:
    """Moving-block-bootstrap 95% CI for the median of a serially dependent path.

    Unlike the spine's i.i.d. resample (which destroys serial structure by
    drawing single samples uniformly), this resamples *contiguous blocks* of
    length L and concatenates them, preserving within-block correlation so the
    resampled spread reflects the path's true autocorrelation. Recipe: take all
    overlapping length-L blocks of the ordered path, draw ceil(n/L) of them with
    replacement, concatenate, truncate to n, take the median; repeat ``iters``
    times; report the 2.5/97.5 percentiles.

    Defined here as the *reference* the spine's i.i.d. band is measured against.
    If the experiment confirms the under-coverage, this is the sanctioned,
    general option proposed for the backbone. Vectorized with numpy for speed
    (called once per simulated experiment); numpy's default 'linear' quantile
    interpolation matches the spine's ``_percentile`` at q=0.5.
    """
    arr = np.asarray(xs, dtype=float)
    n = arr.size
    L = block_len if block_len is not None else default_block_len(n)
    rng = np.random.default_rng(seed)

    n_starts = n - L + 1  # overlapping moving blocks
    n_blocks = math.ceil(n / L)  # blocks per resample to cover n
    # offsets within a block: shape (1, 1, L)
    offsets = np.arange(L).reshape(1, 1, L)
    # random block starts: shape (iters, n_blocks, 1)
    starts = rng.integers(0, n_starts, size=(iters, n_blocks, 1))
    idx = (starts + offsets).reshape(iters, n_blocks * L)[:, :n]  # (iters, n)
    resampled = arr[idx]
    meds = np.median(resampled, axis=1)
    lo, hi = np.quantile(meds, [alpha / 2.0, 1.0 - alpha / 2.0])
    return float(lo), float(hi)
