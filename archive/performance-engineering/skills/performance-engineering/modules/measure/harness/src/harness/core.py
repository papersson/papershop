"""The runner: the trust anchor of the harness.

It owns the clock, the measurement loop, warmup, and batch calibration, so the
thing under test never gets to time itself. The only target-specific code is a
``Probe`` (see below) — everything downstream depends on the raw-sample schema
this module emits, not on the probe.

Raw-sample schema (one dict per measurement), the contract every later stage reads:

    {
        "probe":           str,    # which implementation
        "params":          dict,   # the input point (e.g. {"n": 1000})
        "rep":             int,    # repetition index
        "batch":           int,    # iterations timed together (calibration)
        "seconds_per_op":  float,  # wall time / batch  -- the measurement
    }
"""

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass
from typing import Any, Callable

# A reference sink: keeping the last outputs alive stops a clever runtime from
# deciding the work is dead and removing it. In CPython this is belt-and-braces,
# but the harness should be honest about defeating the optimizer everywhere.
_SINK: list[Any] = []


@dataclass
class Probe:
    """The only target-specific code. ``prepare`` is untimed; ``invoke`` is timed.

    Two probes are comparable when, for the same ``params``, their ``invoke``
    returns equal output. The runner enforces that as a correctness gate.
    """

    name: str
    prepare: Callable[[dict], Any]  # params -> fixture  (setup, not measured)
    invoke: Callable[[Any], Any]    # fixture -> output  (measured)
    # Optional approximate-correctness hook. When a probe is approximate
    # (nearest-neighbour search, lossy compression, randomized or LLM output),
    # bit-identical agreement is the wrong test. Supply ``quality(output,
    # fixture) -> float`` and pass ``min_quality`` to ``run_suite``: the probe is
    # then admitted iff its quality clears the bar, and exempted from cross-probe
    # digest equality. Left ``None``, the probe uses the default exact gate.
    quality: Callable[[Any, Any], float] | None = None


@dataclass
class _Cell:
    probe: Probe
    params: dict
    fixture: Any
    batch: int


def _time_batch(invoke: Callable[[Any], Any], fixture: Any, batch: int) -> float:
    """Run ``invoke`` ``batch`` times under a monotonic clock; return seconds."""
    start = time.perf_counter()
    out = None
    for _ in range(batch):
        out = invoke(fixture)
    elapsed = time.perf_counter() - start
    _SINK.append(out)
    if len(_SINK) > 256:
        del _SINK[:128]
    return elapsed


def _calibrate(invoke, fixture, min_batch_time: float) -> int:
    """Grow the batch until one batch takes at least ``min_batch_time`` seconds.

    This lifts fast operations above the timer's resolution so the measurement
    is meaningful instead of dominated by clock granularity.
    """
    batch = 1
    while batch < 2**30:
        if _time_batch(invoke, fixture, batch) >= min_batch_time:
            return batch
        batch *= 2
    return batch


def _digest(value: Any) -> str:
    return hashlib.sha256(repr(value).encode()).hexdigest()[:16]


def run_suite(
    probes: list[Probe],
    param_grid: list[dict],
    *,
    min_batch_time: float = 0.002,
    warmup: int = 5,
    repetitions: int = 40,
    seed: int = 1234,
    min_quality: float | None = None,
) -> list[dict]:
    """Measure every probe at every point in ``param_grid``; return raw samples.

    Fairness measures baked in:
      * The runner owns the clock and loop (the probe cannot time itself).
      * Batch calibration lifts fast ops above timer resolution.
      * A correctness gate rejects probes that disagree on output, so we never
        compare a fast-but-wrong implementation against a correct one.
      * Warmup runs are discarded.
      * Repetitions are measured in randomized, interleaved order, so any
        system drift during the run is spread across all probes equally rather
        than penalizing whichever happened to run last.
    """
    rng = random.Random(seed)
    cells: list[_Cell] = []

    # Prepare every cell, run the correctness gate, calibrate, and warm up.
    for params in param_grid:
        oracle: str | None = None
        for probe in probes:
            fixture = probe.prepare(params)
            output = probe.invoke(fixture)
            if probe.quality is not None and min_quality is not None:
                # Approximate-correctness path: judge against a quality bar
                # rather than bit-equality, and exempt from cross-probe agreement.
                q = probe.quality(output, fixture)
                if q < min_quality:
                    raise ValueError(
                        f"QUALITY GATE FAILED at params={params}: probe "
                        f"{probe.name!r} scored quality {q:.4f} < min_quality "
                        f"{min_quality}. Refusing to benchmark a below-spec result."
                    )
            else:
                # Exact path: every probe must agree bit-for-bit (the default).
                digest = _digest(output)
                if oracle is None:
                    oracle = digest
                elif digest != oracle:
                    raise ValueError(
                        f"CORRECTNESS GATE FAILED at params={params}: probe "
                        f"{probe.name!r} produced output {digest} but a sibling "
                        f"produced {oracle}. Refusing to compare disagreeing probes."
                    )
            batch = _calibrate(probe.invoke, fixture, min_batch_time)
            for _ in range(warmup):
                _time_batch(probe.invoke, fixture, batch)
            cells.append(_Cell(probe, params, fixture, batch))

    # Measure: randomized, interleaved across repetitions.
    samples: list[dict] = []
    order = list(range(len(cells)))
    for rep in range(repetitions):
        rng.shuffle(order)
        for idx in order:
            cell = cells[idx]
            elapsed = _time_batch(cell.probe.invoke, cell.fixture, cell.batch)
            samples.append(
                {
                    "probe": cell.probe.name,
                    "params": cell.params,
                    "rep": rep,
                    "batch": cell.batch,
                    "seconds_per_op": elapsed / cell.batch,
                }
            )
    return samples
