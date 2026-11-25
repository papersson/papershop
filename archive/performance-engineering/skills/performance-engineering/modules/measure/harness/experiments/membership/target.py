"""The thing under test: three ways to answer "is this value present?"

This is a deliberately classic performance lesson. Looking a value up in a list
is a linear scan; looking it up in a set or dict is a hash probe. The harness
should make the asymptotic difference (O(n) vs O(1)) visible and quantified.

Crucially, all three probes build their container from the *same* underlying
data and answer the *same* queries, so they must return the same hit count. The
runner's correctness gate depends on that — it refuses to compare implementations
that disagree.
"""

from __future__ import annotations

import random

from harness.core import Probe

_QUERIES = 200  # lookups performed per timed call


def _build_data(n: int) -> tuple[list[int], list[int]]:
    """Deterministic data + queries for a given size, identical across probes."""
    rng = random.Random(42)
    universe = n * 2  # so roughly half the queries miss
    data = rng.sample(range(universe), n)
    queries = [rng.randrange(universe) for _ in range(_QUERIES)]
    return data, queries


def _count_hits(fixture):
    container, queries = fixture
    hits = 0
    for q in queries:
        if q in container:
            hits += 1
    return hits


def _make_probe(kind: str) -> Probe:
    def prepare(params: dict):
        data, queries = _build_data(params["n"])
        if kind == "list":
            container = data
        elif kind == "set":
            container = set(data)
        elif kind == "dict":
            container = dict.fromkeys(data)
        else:  # pragma: no cover - guards typos
            raise ValueError(f"unknown kind {kind!r}")
        return container, queries

    return Probe(name=f"{kind}_lookup", prepare=prepare, invoke=_count_hits)


probes = [_make_probe("list"), _make_probe("set"), _make_probe("dict")]

param_grid = [{"n": n} for n in (100, 300, 1_000, 3_000, 10_000, 30_000, 100_000)]
