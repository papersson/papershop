"""Non-time metric target: peak resident set size (bytes) of a subprocess.

The headline metric here is NOT seconds. We measure the peak memory footprint of
a child process that allocates a known amount of memory, using macOS
``/usr/bin/time -l`` (which prints a "peak memory footprint" line in bytes).

This target deliberately produces *honest* raw samples: each measurement carries
its value under a metric-neutral ``value`` key plus ``metric``/``unit``
provenance, instead of pretending bytes are ``seconds_per_op``. The point of the
experiment (see run.py) is to feed these honest samples into the shared spine and
record whether the spine can ingest a non-time metric without being rewritten.

This is a regime adapter (subprocess measured by an external tool), so it does
not use the in-process ``run_suite`` clock; it owns its own measurement loop but
emits the same *shape* of raw-sample dict the rest of the harness consumes.
"""

from __future__ import annotations

import re
import subprocess
import sys

# Scaling axis: how many MiB the child allocates. Deterministic by construction.
param_grid = [{"size_mb": n} for n in (8, 32, 128, 256)]

REPS = 5

_PEAK_RE = re.compile(r"^\s*(\d+)\s+peak memory footprint\s*$", re.MULTILINE)


def _measure_peak_rss_bytes(size_mb: int) -> int:
    """Spawn a child that allocates ``size_mb`` MiB, return its peak RSS in bytes.

    The child touches every page (bytearray is zero-filled and resident) and then
    exits immediately, so the peak footprint reflects the allocation, not Python
    teardown. ``/usr/bin/time -l`` writes its report to stderr.
    """
    n = size_mb * 1024 * 1024
    child = (
        f"b = bytearray({n}); "
        "b[::4096] = b'\\x01' * len(b[::4096]); "  # touch one byte per page
        "import os; os._exit(0)"
    )
    proc = subprocess.run(
        ["/usr/bin/time", "-l", sys.executable, "-c", child],
        capture_output=True,
        text=True,
    )
    m = _PEAK_RE.search(proc.stderr)
    if m is None:
        raise RuntimeError(
            f"could not parse peak memory footprint from /usr/bin/time output:\n"
            f"{proc.stderr}"
        )
    return int(m.group(1))


def measure_samples() -> list[dict]:
    """Return honest non-time raw samples (peak RSS in bytes).

    Schema is the harness raw-sample shape with provenance added and the value in
    a metric-neutral channel:

        {"probe", "params", "rep", "batch", "metric", "unit", "value"}

    Crucially there is NO ``seconds_per_op`` key, because the metric is not time.
    """
    samples: list[dict] = []
    for params in param_grid:
        size_mb = params["size_mb"]
        for rep in range(REPS):
            value = _measure_peak_rss_bytes(size_mb)
            samples.append(
                {
                    "probe": "peak_rss",
                    "params": dict(params),
                    "rep": rep,
                    "batch": 1,
                    "metric": "peak_rss_bytes",
                    "unit": "bytes",
                    "value": value,
                }
            )
    return samples
