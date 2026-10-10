"""How a narration is delivered: its speaking and overall rates, its pauses and how its rate swings
minute by minute, next to three reference explainers, with a `delivery` warning when it is flat.

Measured on the word times in audio/timings.json (the engine's own timestamps). An estimate has no
words, so each sentence counts as one stretch of speech with its words spread evenly over it.

  speaking rate   words a minute while talking: time in pauses of PAUSE s or more left out
  overall rate    words a minute from the first word to the last
  pauses          silences of PAUSE s or more between words: their median, 90th percentile, and how
                  many run past 1.5 s and 2 s
  per minute      words in each whole minute from the first word (the last part minute left out),
                  and their spread: (most − fewest) / mean

The references are 3Blue1Brown "But what is a neural network?", Kurzgesagt "The Immune System
Explained I" and Sebastian Lague "Coding Adventure: Ray Tracing", measured from YouTube's automatic
captions, whose word ends are estimated from length. Both sides are approximate: read them as a
band, not a target.

The warning fires on flat delivery:
  - pauses over LONG_PAUSE s rarer than LONG_RATE a minute, or none for STRETCH s. The references
    pause that long about 0.7 (3B1B) and 1.2 (Lague) times a minute, at key moments, and Kurzgesagt,
    whose gaps sit under a continuous score, perhaps 0.3; a narration with a fixed beat and no
    chapter holds has none at all. A two-minute stretch alone would flag the references: thirteen
    long pauses in 18 minutes leave some gap over two minutes. Or
  - a per-minute spread under SPREAD_MIN in a narration longer than SPREAD_AFTER s (the references
    swing 28-32%), or
  - pauses all about one length, in a narration longer than SPREAD_AFTER s: among the pauses up to WITHIN s (inside ideas: chapter breaks and
    reveal holds left out), the 90th percentile under EVEN times the median. The references' ratio
    is 1.4-2.5 with every pause counted; a narration with a fixed 0.5 s beat reads about 1.1.
"""
import statistics

PAUSE = 0.5          # a silence this long between words is a pause (the references' threshold)
LONG_PAUSE = 1.5     # a pause that marks the end of an idea
LONG_RATE = 0.3      # long pauses a minute, at least, in a narration ...
LONG_AFTER = 120.0   # ... longer than this
STRETCH = 240.0      # seconds of narration with no long pause before delivery reads as flat
SPREAD_MIN = 0.08    # per-minute rate spread under this is flat ...
SPREAD_AFTER = 180.0  # ... in a narration longer than this
WITHIN = 2.5         # pauses up to this long are inside ideas
EVEN = 1.2           # their p90 / median under this is one pause length everywhere
EVEN_COUNT = 10      # ... judged on at least this many pauses

# From the benchmark of the three references (DESIGN.md); per-minute spread leaves out each video's
# last part minute, and long pauses a minute are estimated from each video's pause count and p90.
REFERENCE = {
    "speaking_wpm": (190, 212),
    "overall_wpm": (174, 180),
    "pause_median": (0.67, 0.75),
    "pause_p90": (0.93, 1.78),
    "long_pauses_per_min": (0.3, 1.2),   # over 1.5 s; Kurzgesagt's 0.3 is the least certain
    "per_minute_spread": (0.28, 0.32),
    "pause_evenness": (1.39, 2.54),      # p90 / median, every pause over 0.5 s counted
}


def word_spans(timings):
    """[(start, end)] of every spoken word, in order. Sentences without word times (an estimate) are
    split evenly into their words."""
    out = []
    for seg in timings["segments"]:
        for ln in seg["lines"]:
            if ln.get("words"):
                out += [(w["start"], w["end"]) for w in ln["words"]]
            else:
                n = max(1, len((ln.get("caption") or ln.get("text") or "").split()))
                step = (ln["end"] - ln["start"]) / n
                out += [(ln["start"] + i * step, ln["start"] + (i + 1) * step) for i in range(n)]
    return sorted(out)


def percentile(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    lo = int(k)
    return xs[lo] + (xs[min(lo + 1, len(xs) - 1)] - xs[lo]) * (k - lo)


def measure(timings):
    """The delivery numbers of laid-out timings, or None when there are fewer than two words."""
    words = word_spans(timings)
    if len(words) < 2:
        return None
    first, last = words[0][0], max(e for _, e in words)
    span = last - first
    gaps = [(b[0] - a[1], a[1]) for a, b in zip(words, words[1:])]
    pauses = [(g, at) for g, at in gaps if g >= PAUSE]
    lengths = [g for g, _ in pauses]
    talking = span - sum(lengths)
    minutes, t = [], first
    while t + 60 <= last + 1e-9:
        minutes.append(sum(1 for s, _ in words if t <= s < t + 60))
        t += 60
    long_at = [first] + [at for g, at in pauses if g > LONG_PAUSE] + [last]
    stretch = max(b - a for a, b in zip(long_at, long_at[1:]))
    longest_at = next(a for a, b in zip(long_at, long_at[1:]) if b - a == stretch)
    mean = statistics.mean(minutes) if minutes else None
    inner = [g for g in lengths if g <= WITHIN]
    return {
        "words": len(words),
        "seconds": round(span, 1),
        "speaking_wpm": round(len(words) / talking * 60, 1) if talking > 0 else None,
        "overall_wpm": round(len(words) / span * 60, 1) if span > 0 else None,
        "pauses": len(lengths),
        "pause_median": round(statistics.median(lengths), 2) if lengths else None,
        "pause_p90": round(percentile(lengths, 0.9), 2) if lengths else None,
        "pauses_over_1_5": sum(1 for g in lengths if g > 1.5),
        "pauses_over_2": sum(1 for g in lengths if g > 2.0),
        "long_pauses_per_min": round(sum(1 for g in lengths if g > LONG_PAUSE) / span * 60, 2) if span > 0 else None,
        "per_minute": minutes,
        "per_minute_spread": round((max(minutes) - min(minutes)) / mean, 3) if minutes and mean else None,
        "longest_without_long_pause": {"at": round(longest_at, 1), "seconds": round(stretch, 1)},
        "pause_evenness": round(percentile(inner, 0.9) / statistics.median(inner), 2) if len(inner) >= EVEN_COUNT else None,
        # whether the narration was laid out with pauses by role (None: timings from before they existed)
        "role_pauses": isinstance(timings.get("pauses"), dict) if "pauses" in timings else None,
    }


def from_timeline(timeline, pauses=None):
    """measure() on a timeline's narration track (its words carry the same times as the timings);
    `pauses` is the timings' own record of how its pauses were laid out, when known."""
    t = {"segments": [{"lines": timeline["tracks"].get("narration", [])}]}
    return measure({**t, "pauses": pauses} if pauses is not None else t)


def warnings(m):
    """Why a delivery reads as flat: [] when it doesn't."""
    if not m:
        return []
    out = []
    lw = m["longest_without_long_pause"]
    fix = "(let a question stand, or mark the sentence that matters [key])"
    if m["seconds"] > LONG_AFTER and m["long_pauses_per_min"] < LONG_RATE:
        out.append(f"{m['pauses_over_1_5']} pauses over {LONG_PAUSE:g}s in {m['seconds'] / 60:.1f} min, "
                   f"under {LONG_RATE:g} a minute {fix}")
    elif lw["seconds"] > STRETCH:
        out.append(f"no pause over {LONG_PAUSE:g}s for {lw['seconds']:.0f}s from {lw['at']:.0f}s {fix}")
    if m["seconds"] > SPREAD_AFTER and m["per_minute_spread"] is not None and m["per_minute_spread"] < SPREAD_MIN:
        out.append(f"the rate barely changes minute to minute ({m['per_minute_spread']:.0%} spread, under "
                   f"{SPREAD_MIN:.0%}); let key ideas breathe and asides move")
    if m["seconds"] > SPREAD_AFTER and m.get("pause_evenness") is not None and m["pause_evenness"] < EVEN:
        hint = "mark the sentence that matters [key]" if m.get("role_pauses") else \
            "re-narrate for pauses by role, and mark the sentence that matters [key]"
        out.append(f"the pauses are nearly all one length (p90 {m['pause_evenness']:.2f}× the median, under {EVEN:g}×); {hint}")
    return out


def band(key, fmt):
    lo, hi = REFERENCE[key]
    return f"{fmt.format(lo)}–{fmt.format(hi)}"


def describe(m):
    """Lines for a printed report, each next to the reference band (approximate on both sides)."""
    if not m:
        return ["delivery: too few words to measure"]
    pm = m["per_minute"]
    lines = [
        f"speaking {m['speaking_wpm']:.0f} wpm (references ~{band('speaking_wpm', '{:.0f}')}), "
        f"overall {m['overall_wpm']:.0f} wpm (~{band('overall_wpm', '{:.0f}')})",
        f"pauses over {PAUSE:g}s: {m['pauses']}, median {m['pause_median'] or 0:.2f}s (~{band('pause_median', '{:.2f}')}), "
        f"p90 {m['pause_p90'] or 0:.2f}s (~{band('pause_p90', '{:.2f}')}), "
        f"{m['pauses_over_1_5']} over 1.5s ({m['long_pauses_per_min']:.1f}/min, ~{band('long_pauses_per_min', '{:.1f}')}), "
        f"{m['pauses_over_2']} over 2s",
    ]
    if pm:
        spread = m["per_minute_spread"]
        lines.append(f"per minute {min(pm)}–{max(pm)} wpm, spread {spread:.0%} (~{band('per_minute_spread', '{:.0%}')})"
                     + ("" if len(pm) > 2 else ", too short to judge"))
    lines.append("(approximate: reference rates come from auto-captions, ours from the voice's timestamps)")
    return lines + [f"warn delivery: {w}" for w in warnings(m)]
