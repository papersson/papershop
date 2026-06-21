"""A small, generalizable performance-evaluation harness.

The design separates four concerns behind stable contracts:

  1. The *probe* (target-specific): the ONLY code you write per project.
     It knows how to set up the thing under test and how to invoke it.
  2. The *runner* (core.py): owns the clock, warmup, batch calibration,
     randomized interleaving, and a correctness gate. Emits raw samples.
  3. The *aggregator* (stats.py): turns raw samples into honest statistics.
  4. The *reporter* (report.py): turns statistics into plots and tables.

Components talk only through plain data (lists of dicts / JSON files), so any
one of them can be swapped without disturbing the others.
"""

__version__ = "0.1.0"
