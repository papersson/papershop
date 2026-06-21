"""Target for the ratio-of-totals estimator trap (claim RATIO-METRIC-ESTIMATOR).

This "target" is not software under test. It is a *generative model of a
throughput measurement* whose headline is a ratio of totals (requests served /
seconds elapsed). The thing under attack is the spine's implicit estimator: the
raw-sample schema has a single scalar ``value`` channel, so the only way to feed
a per-window throughput in is ``value = rate_i = num_i / den_i``. ``aggregate``
then reports the *median (and mean) of those per-window rates* with a bootstrap
CI built from the rate list alone. The denominators ``den_i`` are structurally
invisible to the spine -- they can ride along as extra keys, but ``_value`` never
reads them and the ``_POOL_KEYS`` provenance guard never inspects them.

The honest headline is the RATIO OF TOTALS, R* = sum(num_i) / sum(den_i), which
weights each window by its denominator. When window denominators vary and
correlate with rate (the congestion pattern: a few long, slow windows plus many
short, fast ones), the median/mean of per-window rates is a badly biased
estimator of R*, and its CI -- computed from the wrong quantity -- does not cover
R* at all.

Generative model (two window classes, the realistic congestion mix):

    FAST: N_FAST short windows, nominal rate RATE_FAST over duration D_FAST
          -> small denominator, many windows.
    SLOW: N_SLOW long windows,  nominal rate RATE_SLOW over duration D_SLOW
          -> large denominator, few windows.

Each window draws independent mean-1 lognormal multiplicative noise on its
duration and its request count, so denominators (and rates) genuinely vary:

    den_i = d0 * LN,   num_i = (rate0 * d0) * LN',   rate_i = num_i / den_i

with LN = exp(N(-s^2/2, s^2)) so E[LN] = 1. Hence E[den_i] = d0 and
E[num_i] = rate0 * d0, giving a clean closed-form population ratio

    R* = sum(rate0 * d0 * count) / sum(d0 * count)

(the denominator-weighted average of the class rates, ~180 req/s here), which is
the TRUE headline the estimators are scored against.

It exposes:
  - ``generate_windows`` -- one synthetic dataset of (num, den) windows;
  - ``true_ratio`` -- the closed-form population R* (cross-checked by run.py);
  - ``make_raw_samples`` -- maps windows into the load-bearing raw-sample schema
    the ONLY way the schema allows (value = rate_i), with num/den carried as
    extra keys that ``aggregate`` provably ignores -- re-exercising C1;
  - ``ratio_of_totals`` -- the correct point estimator (sum num / sum den);
  - ``paired_bootstrap_ci_ratio`` -- the REFERENCE estimator, a paired
    (num_i, den_i) window-resample bootstrap, defined ONLY here, never in the
    spine -- mirroring how ``iid_bootstrap`` and ``tail_ci`` kept their reference
    recipes out of the backbone until promotion.

Nothing here imports or mutates the spine.
"""

from __future__ import annotations

import math
import random

# --- generative model of a throughput trajectory --------------------------

# FAST class: many short windows, high rate, small denominator.
RATE_FAST = 1000.0  # req/s
D_FAST = 0.1  # s
N_FAST = 50

# SLOW class: few long windows, low rate, large denominator (congestion).
RATE_SLOW = 100.0  # req/s
D_SLOW = 10.0  # s
N_SLOW = 5

# Multiplicative lognormal spread on durations and counts, so denominators
# genuinely vary window to window (the trap must survive real variation, not
# just a noise-free toy).
SIGMA = 0.3


def _lognorm_mean1(rng: random.Random, sigma: float) -> float:
    """A multiplicative noise factor that is lognormal with mean exactly 1.

    Drawing the log from N(-sigma^2/2, sigma^2) makes E[exp(.)] = 1, so the
    factor neither inflates nor deflates expectations -- this is what keeps the
    closed-form population ratio R* exact.
    """
    return math.exp(rng.gauss(-0.5 * sigma * sigma, sigma))


def generate_windows(seed: int) -> list[dict]:
    """One synthetic dataset: a list of windows, each {num, den, rate, klass}.

    num_i = requests served in the window, den_i = seconds it spanned,
    rate_i = num_i / den_i. FAST and SLOW classes are concatenated; the order
    does not matter to any estimator here (all are exchangeable over windows).
    """
    rng = random.Random(seed)
    windows: list[dict] = []
    for rate0, d0, count, klass in (
        (RATE_FAST, D_FAST, N_FAST, "fast"),
        (RATE_SLOW, D_SLOW, N_SLOW, "slow"),
    ):
        for _ in range(count):
            den = d0 * _lognorm_mean1(rng, SIGMA)
            num = (rate0 * d0) * _lognorm_mean1(rng, SIGMA)
            windows.append(
                {"num": num, "den": den, "rate": num / den, "klass": klass}
            )
    return windows


def true_ratio() -> float:
    """Closed-form population headline R* = E[sum num] / E[sum den].

    Because the lognormal noise has mean 1, expectations are the noise-free
    totals: R* = (sum rate0*d0*count) / (sum d0*count). This is the
    denominator-weighted average of the class rates -- the honest throughput.
    """
    num = RATE_FAST * D_FAST * N_FAST + RATE_SLOW * D_SLOW * N_SLOW
    den = D_FAST * N_FAST + D_SLOW * N_SLOW
    return num / den


def make_raw_samples(windows: list[dict], *, probe: str, params: dict) -> list[dict]:
    """Map windows into the load-bearing raw-sample schema, the only way it allows.

    The schema has one scalar measurement slot, so the per-window throughput must
    enter as ``value = rate_i``. ``num`` and ``den`` ride along as extra keys to
    make the central point concrete: ``stats._value`` reads only ``value`` and the
    ``_POOL_KEYS`` provenance guard never inspects ``num``/``den``, so the
    denominator is *structurally* dropped before any statistic is computed.
    Provenance is declared honestly (throughput in req/s), which is exactly why
    provenance cannot catch the bug: every sample agrees on its unit.
    """
    return [
        {
            "probe": probe,
            "params": params,
            "rep": i,
            "batch": 1,
            "value": w["rate"],  # the ONLY channel the schema offers
            "seconds_per_op": w["rate"],  # legacy mirror; _value prefers `value`
            "num": w["num"],  # ignored by aggregate
            "den": w["den"],  # ignored by aggregate (the invisible denominator)
            "metric": "throughput",
            "unit": "req_per_s",
            "clock": "wall",
            "includes_startup": False,
            "overhead_removed": False,
        }
        for i, w in enumerate(windows)
    ]


# --- correct estimator + reference bootstrap (live ONLY in the experiment) --


def ratio_of_totals(windows: list[dict]) -> float:
    """The honest point estimate: total requests / total seconds."""
    return sum(w["num"] for w in windows) / sum(w["den"] for w in windows)


def paired_bootstrap_ci_ratio(
    windows: list[dict],
    *,
    iters: int = 2000,
    alpha: float = 0.05,
    seed: int = 1,
) -> tuple[float, float]:
    """Paired window-resample bootstrap 95% CI for the ratio of totals.

    The fix the spine cannot express: resample whole windows (the *pair*
    (num_i, den_i)) with replacement, and recompute sum(num)/sum(den) on each
    resample. Keeping num and den paired preserves the denominator weighting, so
    the resampled spread reflects the true uncertainty of the ratio estimator.
    Report the 2.5/97.5 percentiles. Defined here as the reference the spine's
    rate-list CI is measured against; if confirmed, the sanctioned spine
    evolution is a denominator/weight channel feeding this estimator.
    """
    rng = random.Random(seed)
    nums = [w["num"] for w in windows]
    dens = [w["den"] for w in windows]
    n = len(windows)
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


def _percentile(sorted_xs: list[float], p: float) -> float:
    """Linear-interpolation percentile, matching ``stats._percentile`` exactly.

    Reimplemented here (not imported) so the reference estimator is wholly
    self-contained, but deliberately identical so a CI difference can only come
    from the *estimand* (ratio of totals vs median of rates), never from a
    percentile-convention mismatch. Expects an already-sorted list.
    """
    s = sorted_xs
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)
