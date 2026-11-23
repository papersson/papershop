## What I did

First I profiled the loader_v2 job on S3B, then I looked at the timings again, and then I compared
them with the timings from the week before, which had come from an older version of the same job.
After that I tried a faster disk, which did not help, and then a bigger batch size, which did not
help either. Then I tried the fp trick, which helped a lot on some nights and less on others, and I
also tried ZSTD for the season files, and finally I implemented a comprehensive and robust fix.

## Results

A **fingerprint** is a short code computed from a file's contents. A **cold night** is a night where
every file changed. A **warm night** is one where few did. The load went from 08:50 to 05:40 on
warm nights and 07:55 on cold ones, while the deadline stood at 07:00 and the old record was 06:10.
All tests pass and the slowdown is fixed. Everything was verified.

Each of these times comes with some variation, and the variation is wide, because there are few
nights, and the nights come from one season, so the result may not hold for other seasons or other
providers, and it may change when the provider changes its format, and it may change when the
schedule moves.

## Next

I will keep trying things. There are many ideas left, and some of them may work better than the
ones tried so far, although it is hard to say which ones in advance.
