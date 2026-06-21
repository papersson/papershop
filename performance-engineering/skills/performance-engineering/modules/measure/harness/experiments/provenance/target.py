"""Synthetic fixtures for the PROVENANCE spine-evolution falsification.

No live measurement is needed: the evolution is a re-aggregation of existing
raw samples plus two tiny hand-built groups that probe the new guards. The real
``/usr/bin/time -l`` peak-RSS re-run is deferred to PROVENANCE-VALIDATE-NONTIME;
the synthetic bytes batch here is sufficient to falsify P3.
"""

from __future__ import annotations


def mismatched_unit_group() -> list[dict]:
    """Two samples in one (probe, params) group that disagree on unit.

    One claims seconds, one claims bytes. A spine that still silently pools
    these (the stats.py:97 units-lie) would average a second with a byte;
    aggregate() must refuse with a ValueError (prediction P2).
    """
    base = {"probe": "mixed", "params": {"n": 1}, "rep": 0, "batch": 1}
    return [
        {**base, "rep": 0, "value": 1.0e-6, "metric": "time", "unit": "seconds"},
        {**base, "rep": 1, "value": 1_000_000, "metric": "peak_rss_bytes", "unit": "bytes"},
    ]


def bytes_samples() -> list[dict]:
    """A small honest non-time batch: peak RSS in bytes via the value channel.

    Deterministic by construction. Each (probe, params) group is internally
    consistent (all bytes), so it must aggregate cleanly and stay labelled bytes
    (prediction P3) rather than being relabelled seconds.
    """
    # Hand-picked byte values per size, well inside byte range (tens of MB).
    table = {
        8: [15_466_952, 15_470_000, 15_460_000, 15_472_000, 15_468_000],
        32: [40_120_000, 40_140_000, 40_100_000, 40_160_000, 40_130_000],
        128: [141_900_000, 141_950_000, 141_880_000, 141_970_000, 141_920_000],
    }
    samples: list[dict] = []
    for size_mb, vals in table.items():
        for rep, v in enumerate(vals):
            samples.append(
                {
                    "probe": "peak_rss",
                    "params": {"size_mb": size_mb},
                    "rep": rep,
                    "batch": 1,
                    "metric": "peak_rss_bytes",
                    "unit": "bytes",
                    "clock": "wall",
                    "value": v,
                }
            )
    return samples
