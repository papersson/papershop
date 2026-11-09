#!/usr/bin/env python3
"""Compute every number the hash-table page shows, print them, and check the page shows exactly these.

    python3 -I values.py

The stock counts are an example. Everything else (bytes, hashes, buckets, comparisons) is computed
here with the same FNV-1a lookup the page's last chapter shows, line for line. The fruit were chosen
by running this: mango, fig and pear all land in bucket 5, so a hit and a miss share one bucket.
"""
import inspect
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "page.html"
BUCKETS = 8
STOCK = [("apple", 3), ("date", 12), ("mango", 2), ("orange", 9), ("lime", 6), ("fig", 4), ("peach", 7)]
MISSING = "pear"


def fnv1a(key):
    h = 2166136261
    for b in key.encode():
        h = (h ^ b) * 16777619 % 2**32
    return h


def lookup(buckets, key):
    h = 2166136261
    for b in key.encode():
        h = (h ^ b) * 16777619 % 2**32
    bucket = buckets[h % 8]
    for k, v in bucket:
        if k == key:
            return v
    return None


def compared(buckets, key):
    """How many keys a lookup compares before it returns."""
    bucket = buckets[fnv1a(key) % BUCKETS]
    for i, (k, _) in enumerate(bucket, 1):
        if k == key:
            return i
    return len(bucket)


def main():
    buckets = [[] for _ in range(BUCKETS)]
    for key, count in STOCK:
        buckets[fnv1a(key) % BUCKETS].append((key, count))

    print(f"{'key':8} {'bytes':18} {'FNV-1a':12} bucket")
    for key in [k for k, _ in STOCK] + [MISSING]:
        h = fnv1a(key)
        print(f"{key:8} {key.encode().hex(' '):18} {h:#010x}   {h % BUCKETS}" + ("   (not stored)" if key == MISSING else ""))
    for b, entries in enumerate(buckets):
        print(f"bucket {b}: {', '.join(f'{k} {v}' for k, v in entries) or 'empty'}")

    page = PAGE.read_text()
    fig, pear = fnv1a("fig"), fnv1a(MISSING)
    expected = [f"  ['{k}', {v}, {fnv1a(k) % BUCKETS}]," for k, v in STOCK]
    expected += [
        f"const FIG = {{ bytes: '{'fig'.encode().hex(' ')}', hash: '{fig:#010x}', bucket: {fig % BUCKETS} }};",
        f"const PEAR = {{ hash: '{pear:#010x}', bucket: {pear % BUCKETS} }};",
        f"const TALLY = '{compared(buckets, 'fig')} of {len(STOCK)} keys compared';",
    ]
    # The code chapter is this file's lookup, line for line.
    expected += [f"'{line}']" for line in inspect.getsource(lookup).rstrip().splitlines()]
    missing = [e for e in expected if e not in page]
    assert not missing, "page.html does not show these computed values:\n" + "\n".join(missing)

    assert lookup(buckets, "fig") == 4 and lookup(buckets, MISSING) is None
    assert [k for k, _ in buckets[fig % BUCKETS]] == ["mango", "fig"], "fig's bucket should hold mango then fig"
    assert pear % BUCKETS == fig % BUCKETS, "the missing key should land in fig's bucket"
    assert compared(buckets, "fig") == compared(buckets, MISSING) == 2
    assert sum(len(b) > 1 for b in buckets) == 1, "only one bucket should hold two fruits"
    print(f"ok: {len(expected)} values and code lines on the page match")


if __name__ == "__main__":
    main()
