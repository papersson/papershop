"""Synthetic cohorts for the batch-homogeneity enforcement probe.

This experiment targets the *spine itself* (``stats.aggregate``), not a piece of
code under test, so the "target" is a deterministic generator of raw samples
rather than a runnable workload. Both cohorts describe the SAME operation with the
SAME true cost (1.0 microsecond per op); they differ only in ``batch`` — the
number of ops each measurement averaged over — and therefore in their spread.

A batch=1000 measurement averages a microsecond cost over 1000 ops, so per-call
jitter is divided down and the sample-to-sample spread is tight. A batch=1
measurement times a single op, so it carries the full per-call jitter and is
noisy. Pooling the two answers no honest question: the result is neither the
clean estimate the fine cohort earned nor the wide band the coarse cohort needs.
"""

from __future__ import annotations

import random

TRUE_SPO = 1.0e-6  # true seconds per op, identical for both cohorts
FINE_SD = 0.02e-6  # batch=1000: jitter averaged down -> tight
COARSE_SD = 0.40e-6  # batch=1: full per-call jitter -> noisy


def _cohort(probe: str, params: dict, *, batch: int, sd: float, n: int, rng: random.Random) -> list[dict]:
    out = []
    for rep in range(n):
        spo = rng.gauss(TRUE_SPO, sd)
        if spo <= 0:  # clamp: a duration cannot be <= 0
            spo = 1e-12
        out.append(
            {
                "probe": probe,
                "params": params,
                "rep": rep,
                "batch": batch,
                "seconds_per_op": spo,
            }
        )
    return out


def cohort_fine(rng: random.Random, n: int = 60) -> list[dict]:
    """Tight cohort: each sample is averaged over batch=1000 ops."""
    return _cohort("op", {"size": 1}, batch=1000, sd=FINE_SD, n=n, rng=rng)


def cohort_coarse(rng: random.Random, n: int = 60) -> list[dict]:
    """Noisy cohort: each sample times batch=1 op, full per-call jitter."""
    return _cohort("op", {"size": 1}, batch=1, sd=COARSE_SD, n=n, rng=rng)
