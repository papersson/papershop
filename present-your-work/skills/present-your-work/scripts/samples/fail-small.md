## What we did

The crowded misses were the main problem, so this report starts with them. On Monday we first ran
the spotter over the clips and wrote its output with the run_queue driver. On Tuesday we ran the
B8 configuration on dev40 and looked at the scores again, and then we compared them with the scores
from the week before, which had come from an older version of the same configuration. On Wednesday
we tried a second reader, which did not help, and then a vote between two readers, which did not
help either. On Thursday we tried a larger picture of the ball, which helped a little on some clips
and not at all on others, and we also tried the TCN as a replacement for the first stage.

## Results

A **crowded miss** is a missed event beside an event that is credited to another one. A
**receipt** is the moment a player first controls the ball. A **duplicate** is a second event for
one touch. The score went from 0.692 to 0.838 on the development clips and reached 0.827 on the
test clips, while the human reference stood at 0.91 on the same clips.

Each of these numbers comes with an interval, and each of the intervals is wide, because there are
few clips, and the clips come from few matches, and the matches come from one season, so the result
may not hold for other seasons, other leagues or other broadcasters, and it may change when the
labels are checked again, and it may change when the model is updated, which happens often, and it
may change when the picture tool changes, which it did twice during the work described here.

## Next

We will keep trying things. There are many ideas left, and some of them may work better than the
ones tried so far, although it is hard to say which ones in advance, and the order in which they
are tried will depend on what the next runs show and on how much time is left this week.
