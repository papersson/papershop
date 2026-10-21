You asked for the nightly data load to finish before the analysts start at 07:00. It now finishes
by 05:40 on each of the last five nights, against 08:50 on average in the week before, so the goal
is met with more than an hour to spare.

The time went into one step. Each night the load read every match file again, although only the
files that changed since the night before can give a different result. The load now keeps a
**fingerprint** of each file, a short code computed from its contents, and skips a file whose
fingerprint has not changed since the last run. On a normal night that leaves a handful of files to
read instead of the whole season.

One thing still stands in the way of keeping the load this fast. When the provider changes its file
format, every fingerprint changes at once, and the load reads the whole season as slowly as before.
Nothing in the data gives warning of such a change.

The next steps, in order of what they gain for what they cost:

- Make the fingerprint check part of the tests. It takes an hour and protects the gain.
- Split the full reload by season, so that a format change reloads one season instead of all of
  them. It takes about a day.

If the analysts move their start earlier, the second step becomes the first.
