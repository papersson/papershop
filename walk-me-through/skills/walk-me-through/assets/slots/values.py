"""The timings the page shows, measured: three calls without the cache, three with it. Run it and
compare with the TOOK values in page.html (rounded to a tenth of a second)."""
import time
from functools import cache

TABLE = {"tea": 4.50, "milk": 1.20}


def price(item):
    time.sleep(2)  # the slow lookup
    return TABLE[item]


cached = cache(price)
for f, calls in ((price, ["tea", "tea"]), (cached, ["tea", "tea", "milk"])):
    for item in calls:
        t = time.perf_counter()
        f(item)
        print(f.__name__ if f is price else "cached", item, f"{time.perf_counter() - t:.1f} s")
