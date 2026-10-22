"""Staging: when things are introduced, explained and left alone, checked against the narration.

staging.json is authored beside cues.json. Its times are cues.json values (seconds, or an anchor on
a sentence or phrase), so a re-voiced narration moves them and the check then reports what no longer
fits, by name, instead of passing silently.

  {"settle": 1.0, "question_pause": 2.0,
   "events": [
     {"id": "clock", "kind": "intro", "start": {...}, "end": {...}},      something new appears
     {"id": "clock-again", "kind": "replay", "start": ..., "end": ...,    a familiar demonstration again
      "introduced_by": "clock", "describes": ["s2_03"]},                  and the sentence(s) it may run under
     {"id": "k1", "kind": "typing", "start": ..., "end": ...},            keys being typed
     {"id": "q1", "kind": "question", "start": ..., "end": ...},          a pause for the viewer to answer
     {"id": "spin", "kind": "loop", "start": ..., "end": ..., "stop": ...}  repeats until its stop
   ]}

kinds     intro, replay, typing, question, loop; `group` on an intro puts it with the others of its group
          (a cause and its effect are one thing). Every event has an `end`, or `seconds` after its start.
conflicts (each reported by event id, one row apiece, with the seconds):
  intro-under-voice     an intro or typing overlaps spoken words
  replay-under-voice    a replay overlaps a sentence it does not describe, or it was never introduced
                        before it started
  unsettled             voice, or another intro, starts less than `settle` s after an intro ends
  question-not-held     the question's pause is shorter than `question_pause`, or something happens in it
  loop-runs-on          a loop has no stop, or runs past the next intro
  unknown-reference     introduced_by names no event

The rules are references/session.md's; the numbers are starting values to be tuned by watching.
"""
import json
from pathlib import Path

from . import timeline as tl

KINDS = ("intro", "replay", "typing", "question", "loop")
SETTLE, QUESTION_PAUSE = 1.0, 2.0


def load(video):
    f = Path(video) / "staging.json"
    if not f.exists():
        return None
    raw = json.loads(f.read_text())
    return raw if isinstance(raw, dict) else {"events": raw}


def sentences(T):
    """[(id, first word start, last word end)] of the narration: where the voice is."""
    out = []
    for s in T["tracks"]["narration"]:
        words = s.get("words") or []
        a, b = (words[0]["start"], words[-1]["end"]) if words else (s["start"], s["end"])
        out.append((s["id"], a, b))
    return out


def resolved(T, spec):
    """The events with their times resolved against the timeline; ValueError names the first that has none."""
    events = []
    for e in spec.get("events", []):
        if e.get("kind") not in KINDS or not e.get("id"):
            raise ValueError(f"staging event {e!r} needs an id and a kind among {', '.join(KINDS)}")
        try:
            a = tl.event_time(T, e["start"])
            b = tl.event_time(T, e["end"]) if "end" in e else round(a + float(e["seconds"]), 6)
            stop = tl.event_time(T, e["stop"]) if e.get("stop") is not None else None
        except (KeyError, TypeError) as ex:
            raise ValueError(f"staging event {e['id']!r} needs a start and an end or seconds ({ex})")
        except ValueError as ex:
            raise ValueError(f"staging event {e['id']!r} has no time: {ex}")
        events.append({**e, "a": a, "b": b, "stop_at": stop})
    return events


def conflicts(T, spec):
    """[(kind of conflict, event ids, seconds, detail)] for a timeline."""
    settle, pause = spec.get("settle", SETTLE), spec.get("question_pause", QUESTION_PAUSE)
    ev, voice = resolved(T, spec), sentences(T)
    by_id = {e["id"]: e for e in ev}
    out = []
    first_voice_after = lambda t: min((a for _, a, _ in voice if a >= t - 1e-9), default=None)      # noqa: E731
    for e in ev:
        over = [(sid, a, b) for sid, a, b in voice if a < e["b"] and b > e["a"]]
        ref = e.get("introduced_by")
        if ref is not None and ref not in by_id:
            out.append(("unknown-reference", [e["id"]], e["a"], f"introduced_by names {ref!r}, which is not an event"))
        if e["kind"] in ("intro", "typing") and over:
            out.append(("intro-under-voice", [e["id"]], over[0][1],
                        f"{e['kind']} {e['a']:.2f}-{e['b']:.2f} s runs under {', '.join(s for s, _, _ in over)}: "
                        "show it first and explain it after it settles"))
        if e["kind"] == "replay":
            origin = by_id.get(ref)
            if over and (origin is None or origin["kind"] != "intro" or origin["b"] > e["a"]):
                out.append(("replay-under-voice", [e["id"]], e["a"],
                            f"a replay under {', '.join(s for s, _, _ in over)} must follow its introduction (introduced_by an "
                            "intro that has ended)"))
            wrong = [s for s, _, _ in over if s not in e.get("describes", [])]
            if wrong:
                out.append(("replay-under-voice", [e["id"]], e["a"],
                            f"runs under {', '.join(wrong)}, which it does not describe (describes: {e.get('describes', [])})"))
        if e["kind"] == "intro":
            nxt = first_voice_after(e["b"])
            if nxt is not None and nxt - e["b"] < settle - 1e-9 and not any(a < e["b"] and b > e["a"] for _, a, b in voice):
                out.append(("unsettled", [e["id"]], e["b"],
                            f"voice starts {nxt - e['b']:.2f} s after it ends; it needs {settle:g} s to settle"))
        if e["kind"] == "question":
            busy = [o["id"] for o in ev if o is not e and o["a"] < e["b"] and o["b"] > e["a"]]
            talk = [s for s, a, b in voice if a < e["b"] and b > e["a"]]
            if e["b"] - e["a"] < pause - 1e-9 or busy or talk:
                out.append(("question-not-held", [e["id"], *busy], e["a"],
                            f"the pause is {e['b'] - e['a']:.2f} s (needs {pause:g} s)" +
                            (f" and {', '.join(busy + talk)} happens in it" if busy or talk else "")))
        if e["kind"] == "loop":
            nxt = min((o["a"] for o in ev if o["kind"] == "intro" and o["a"] >= e["a"] and o is not e), default=None)
            if e["stop_at"] is None:
                out.append(("loop-runs-on", [e["id"]], e["a"], "a loop names the moment it stops"))
            elif nxt is not None and e["stop_at"] > nxt + 1e-9:
                out.append(("loop-runs-on", [e["id"]], nxt, f"still running at {nxt:.2f} s when the next concept is introduced"))
    ev_intros = sorted((e for e in ev if e["kind"] == "intro"), key=lambda e: e["a"])
    for p, q in zip(ev_intros, ev_intros[1:]):
        if q["a"] - p["b"] < settle - 1e-9 and (not p.get("group") or p.get("group") != q.get("group")):
            out.append(("unsettled", [p["id"], q["id"]], q["a"],
                        f"{q['id']} starts {max(q['a'] - p['b'], 0):.2f} s after {p['id']} ends; one new thing at a time "
                        f"needs {settle:g} s (or the same group)"))
    return sorted(out, key=lambda c: c[2])


def check(video):
    """check rows for staging.json (none without the file): one failure per conflict, else one ok row."""
    spec = load(video)
    if spec is None:
        return []
    T = tl.build(video, quiet=True)
    try:
        found = conflicts(T, spec)
    except ValueError as e:
        return [{"check": "staging", "clip": "staging", "ok": False, "t": 0.0, "detail": str(e)}]
    rows = [{"check": "staging", "clip": "staging", "ok": False, "t": round(t, 2), "conflict": kind, "events": ids,
             "detail": f"{kind}: {detail}"} for kind, ids, t, detail in found]
    return rows or [{"check": "staging", "clip": "staging", "ok": True,
                     "detail": f"{len(spec.get('events', []))} staged events, no conflicts with the narration"}]
