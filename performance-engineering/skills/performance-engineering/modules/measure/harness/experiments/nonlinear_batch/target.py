"""Targets for the NONLINEAR-BATCH-AMORTIZATION attack.

Claim under attack: the LIBRARY headline ``value = elapsed/N`` (core.py:142) is
treated as batch-invariant -- a property of the operation, independent of the
calibrated batch size N. The schema records ``batch`` but the value is pooled by
``aggregate()`` as if N-independent.

Two workload classes, both PURE/idempotent so the correctness gate passes:

* ``tiny``  -- minimal integer arithmetic (~tens of ns/op). Per-op cost is the
  same order as the fixed per-batch timer overhead (two ``perf_counter`` calls in
  ``_time_batch``), so ``seconds_per_op = per_op + overhead/B`` should fall
  visibly as B grows. This is the loop/timer-overhead amortization channel.

* ``mem``   -- an int64 reduction over a ~512 KB working set (past L1). Per-op
  cost (~microseconds) dwarfs the fixed overhead, so ``elapsed/N`` should be
  roughly flat in B. This is the contrast: it shows where elapsed/N is sound.

Each workload exposes TWO byte-identical implementations (different code paths,
same output) so ``run_suite``'s correctness gate genuinely compares them and
passes while we vary the calibration knob.
"""

from __future__ import annotations

import numpy as np

from harness.core import Probe

# ---- tiny arithmetic workload -------------------------------------------------
TINY_X = 1_234_567


def _tiny_a(x: int) -> int:
    # x*x + x
    return x * x + x


def _tiny_b(x: int) -> int:
    # algebraically identical: x*(x+1) == x*x + x  (exact for integers)
    return x * (x + 1)


def _prepare_tiny(params: dict) -> int:
    return params.get("x", TINY_X)


# ---- memory-bandwidth workload ------------------------------------------------
MEM_N = 1 << 16  # 65536 int64 = 512 KB working set (past L1)


def _prepare_mem(params: dict):
    n = params.get("mem_n", MEM_N)
    rng = np.random.default_rng(42)
    # small positive integers -> exact int64 sum, no overflow (<= n*1000 ~ 6.5e7)
    return rng.integers(0, 1000, size=n, dtype=np.int64)


def _mem_whole(arr) -> int:
    return int(arr.sum())


def _mem_split(arr) -> int:
    # different code path (strided halves), exact-identical result for int64
    return int(arr[::2].sum() + arr[1::2].sum())


# Probes used for the controlled fixed-batch sweep (Part 2): one impl per class.
sweep_probes = [
    Probe(name="tiny", prepare=_prepare_tiny, invoke=_tiny_a),
    Probe(name="mem", prepare=_prepare_mem, invoke=_mem_whole),
]

# Probe sets for the knob sweep (Part 3): two equivalent impls per class so the
# correctness gate in run_suite is real, not vacuous. (label, probes, param_grid)
gate_sets = [
    (
        "tiny",
        [
            Probe(name="tiny_a", prepare=_prepare_tiny, invoke=_tiny_a),
            Probe(name="tiny_b", prepare=_prepare_tiny, invoke=_tiny_b),
        ],
        [{"x": TINY_X}],
    ),
    (
        "mem",
        [
            Probe(name="mem_whole", prepare=_prepare_mem, invoke=_mem_whole),
            Probe(name="mem_split", prepare=_prepare_mem, invoke=_mem_split),
        ],
        [{"mem_n": MEM_N}],
    ),
]

# The controlled batch grid (Part 2).
BATCH_GRID = [1, 2, 4, 16, 64, 256, 1024, 4096, 16384]

# The calibration knob values (Part 3).
KNOB_GRID = [0.0002, 0.002, 0.02, 0.2]
