You asked for the nightly data load to finish before the analysts start at 07:00. It now finishes by
05:40 on the staging copy, against 08:50 the week before, so the deadline holds with an hour to
spare. The one catch: when the provider changes its file format, the next night is as slow as before.

The time went into rereading files that had not changed. The load now keeps a **fingerprint** of each
file, a short code computed from its contents, and skips a file whose fingerprint matches last
night's. I chose this over a faster disk, which made no measurable difference. On a normal night
that leaves a handful of files to read instead of the whole season.

Not verified on production: the five nights were on staging, whose data is a week old. I don't yet
know why two nights read four files more than the others.

What you need to decide: whether to run it on production tonight. If you do, the next step is a
reload split by season, so that a format change slows one season instead of all of them. If the
analysts start earlier, that split comes first.

Evidence:
- `make load-nightly` on staging, five nights: finished between 05:31 and 05:40
- `pytest tests/test_fingerprint.py`: 6 passed (a new file)
- changed: `load/fingerprint.py`, `load/run.py`, `tests/test_fingerprint.py`
