You asked for the nightly data load to finish before the analysts start at 07:00. It now finishes
by 05:40 on the staging copy, against 08:50 the week before, so there's an hour to spare. There's
one catch. When the provider changes its file format, the next night is as slow as before.

The time went into rereading files that hadn't changed. The load now keeps a **fingerprint** of each
file, a short code computed from its contents, and skips a file whose fingerprint matches last
night's. I'd expected the disk to be the problem, but a faster one made no difference. On a normal
night that leaves a handful of files to read instead of the whole season. I don't yet know why two
nights read four more files than the others.

What I need from you is whether to run it on production tonight. If you do, the next step is a
reload split by season, so that a format change slows one season instead of all of them. If the
analysts start earlier, that split comes first.
