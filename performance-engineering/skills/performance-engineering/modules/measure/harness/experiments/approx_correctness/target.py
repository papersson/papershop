"""Target: approximate nearest-neighbor search (correct *in distribution*).

This target deliberately violates the spine's implicit assumption that "correct"
means "bit-identical output". Two implementations here are both correct by the
domain's real acceptance test -- recall@k against brute-force ground truth -- yet
they return different neighbor lists. The exact probe returns the true top-k; the
approximate probe (random-projection LSH + re-rank) returns a top-k that overlaps
the truth at recall in [0.90, 0.99] but is not identical.

Exposed for the runner:
  * ``probes``      -- [exact, approx]  (the pair the correctness gate must judge)
  * ``param_grid``  -- one input point
  * helper builders so run.py can compute recall and a stochastic variant.
"""

from __future__ import annotations

import numpy as np

from harness.core import Probe

SEED = 20260620
DIM = 16
PROJ_DIM = 8
CANDIDATES = 600
K = 10


def build_dataset(params: dict) -> dict:
    """Untimed setup: deterministic dataset + queries for this param point."""
    m, q = params["m"], params["q"]
    rng = np.random.default_rng(SEED)
    data = rng.standard_normal((m, DIM)).astype(np.float32)
    queries = rng.standard_normal((q, DIM)).astype(np.float32)
    return {"data": data, "queries": queries, "k": K}


def exact_topk(fixture: dict) -> list[list[int]]:
    """Brute-force exact L2 top-k -- the domain ground truth."""
    data, queries, k = fixture["data"], fixture["queries"], fixture["k"]
    d2 = ((queries[:, None, :] - data[None, :, :]) ** 2).sum(-1)
    idx = np.argsort(d2, axis=1)[:, :k]
    return [row.tolist() for row in idx]


def approx_topk(fixture: dict, *, rng_seed: int | None = SEED + 1) -> list[list[int]]:
    """Random-projection ANN: project to PROJ_DIM, keep CANDIDATES nearest in the
    reduced space, re-rank those in full space, return top-k.

    Correct only in distribution (recall in [0.90, 0.99]). ``rng_seed=None`` draws
    fresh entropy each call, making the probe non-self-consistent (step C).
    """
    data, queries, k = fixture["data"], fixture["queries"], fixture["k"]
    rng = np.random.default_rng(rng_seed)
    proj = rng.standard_normal((DIM, PROJ_DIM)).astype(np.float32)
    data_p = data @ proj
    queries_p = queries @ proj
    out: list[list[int]] = []
    cand_count = min(CANDIDATES, data.shape[0])
    for i in range(len(queries)):
        dp = ((queries_p[i] - data_p) ** 2).sum(-1)
        cand = np.argpartition(dp, cand_count - 1)[:cand_count]
        df = ((queries[i] - data[cand]) ** 2).sum(-1)
        order = np.argsort(df)[:k]
        out.append(cand[order].tolist())
    return out


# The pair the correctness gate is asked to compare.
exact = Probe(name="exact", prepare=build_dataset, invoke=exact_topk)
approx = Probe(name="approx", prepare=build_dataset, invoke=approx_topk)

# A stochastic probe: fresh RNG inside invoke -> output differs across calls.
approx_stochastic = Probe(
    name="approx_rng",
    prepare=build_dataset,
    invoke=lambda fx: approx_topk(fx, rng_seed=None),
)

probes = [exact, approx]
param_grid = [{"m": 2000, "q": 50}]
