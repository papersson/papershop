"""`studio typing VIDEO PLAN.json`: code typed into an editor, one keystroke stream for picture and sound.

Code the story writes is typed, not revealed (references/code.md). A plan lists bursts of edits,
each turning one recorded version of a file into the next (a `studio steps` output, or any file in
the video). The generator replays each burst's edits on the version before, stops with a diff unless
the result is the recorded version byte for byte, and schedules every keystroke with a human rhythm
(bursts within a word, pauses at punctuation and before a hard line, a typo put right where the plan
asks for one) so each edit is finished by the words that discuss it. It writes:

  data/typing.json    per burst: its cue, the file before and after, and the steps the editor replays
                      (frames after the cue: a keystroke's kind and what it does to the buffer), and the
                      run beat when there is one (the recalled command, Enter, the compile's breath,
                      the program's recorded output, the window opening)
  cues.json           type-<burst> (its first key), -save, -run and -pop: anchored on the sentence they
                      fall in, so they follow the narration; other cues are kept
  audio/sfx.json      per burst one stream (every keystroke, Enter and output tick; streams.py) and an
                      accent on the save and the window opening; effects other generators or the
                      builder made are kept (each generated one carries "source": "typing")

The editor in a Remotion scene (engines/remotion/src/kit/editor.tsx: Editor, Term, ProgramWindow)
reads data/typing.json, so a key and its sound share a frame. The plan:

  {"sources": {"v1": "data/steps/run/v1/main.c", "v2": {"path": "…", "first": 1}},
   "file": "main.c",                                   the name the editor shows
   "run": {"command": "$ cc main.c -o game && ./game", "log": "data/run.txt", "lines_before_window": 9},
   "bursts": [{"id": "s1-window", "clip": "s1", "file": "v2", "before": "v1", "ops": [OP, …]}],
   "sounds": {…}}                                      optional: the stream's sounds (streams.py)

An OP is one edit, in Vim's terms, each with an optional "due" (an anchor its edit is finished by),
"start" (an anchor it doesn't begin before) and "think" (seconds of hesitation before it):
paste {after_lines: [[a, b], …], below?}, open {below | above, text | segments: [{text, typo?, due?}]},
put {below | above, text}, change {line, from, to, nth?}, subst {line, count, from, to},
delete {line}, yank {line}, save, run {pop_due | run_at, breath?}. A segment's "typo": N types its
text with the last N characters wrong, then backspaces them and types them right.
"""
import json
import math
import random
from difflib import SequenceMatcher
from pathlib import Path

from . import timeline as tl
from .workspace import atomic_json

PREFIX = "type-"
SOURCE = "typing"
KEY = "kit:keys-typing-cherry-blue"
# The stream's sounds by default: grains of a take of real typing (a space is darker, a backspace
# brighter), a recorded Enter, and soft ticks for the program's output. Levels set against the grains
# (streams.GRAIN_PEAK): an Enter about 5 dB over a key, a tick well under it.
SOUNDS = {"key": f"grains:{KEY}", "space": f"grains:{KEY}#low", "back": f"grains:{KEY}#high",
          "enter": {"sound": "kit:keys-enter-press", "gain": -16}, "tick": {"sound": "synth:soft-tick", "gain": -24}}
SAVE = {"type": "tap", "sound": "kit:impact-generic-light-002", "gain": -12}
POP = {"type": "thump", "sound": "kit:impact-soft-heavy-000", "gain": -5}


def char_lead(rng, prev, ch):
    """Seconds before a key: a word's letters come in bursts, a pause follows punctuation and a space."""
    if prev is None:
        return rng.uniform(.12, .2)
    if prev in ",;(){}\"=!":
        return rng.uniform(.08, .14)
    if prev == " ":
        return rng.uniform(.06, .1)
    if ch in "(),;{}":
        return rng.choice([.04, .055, .07])
    return rng.choices([.035, .05, .065, .085], weights=[2, 4, 3, 1])[0]


def find(buf, needle, nth=0):
    hits = [i for i, line in enumerate(buf) if needle in line]
    if len(hits) <= nth:
        raise SystemExit(f"no line containing {needle!r}" + (f" (occurrence {nth + 1})" if nth else ""))
    return hits[nth]


class Burst:
    """One burst of edits: units of keystrokes [lead seconds, kind, effects on the buffer], each unit
    with the anchor it is due by and the one it starts after."""

    def __init__(self, spec, sources, timeline):
        self.spec, self.T = spec, timeline
        self.rng = random.Random(spec["id"])
        self.after = list(sources[spec["file"]])
        self.buf = list(sources[spec["before"]]) if spec.get("before") else []
        self.units, self.run = [], None

    def at(self, anchor):
        return tl.event_time(self.T, anchor) if anchor is not None else None

    def unit(self, label, due=None, start=None):
        u = {"keys": [], "due": self.at(due), "start": self.at(start), "label": label}
        self.units.append(u)
        return u["keys"]

    def build(self):
        ops, insert = self.spec["ops"], False
        for n, op in enumerate(ops):
            kind, nxt = op["op"], ops[n + 1] if n + 1 < len(ops) else None
            if kind == "paste":
                lines = [line for a, b in op["after_lines"] for line in self.after[a - 1:b]]
                i = find(self.buf, op["below"]) + 1 if "below" in op else 0
                k = self.unit("paste", op.get("due"), op.get("start"))
                k.append([.2 + op.get("think", 0), "key", [["mode", "NORMAL"], ["ins", i, lines], ["caret", i + len(lines) - 1, 0]]])
                self.buf[i:i] = lines
            elif kind in ("open", "put"):
                insert = self._open(op, nxt, insert)
            elif kind == "change":
                self._change(op)
            elif kind == "subst":
                self._subst(op)
            elif kind == "delete":
                i = find(self.buf, op["line"])
                k = self.unit("dd", op.get("due"), op.get("start"))
                k.append([.25 + op.get("think", 0), "key", [["mode", "NORMAL"], ["caret", i, 0]]])
                k.append([.11, "key", [["del", i], ["caret", max(0, min(i, len(self.buf) - 2)), 0]]])
                del self.buf[i]
            elif kind == "yank":
                i = find(self.buf, op["line"])
                k = self.unit("yy", op.get("due"), op.get("start"))
                k.append([.3, "key", [["caret", i, 0]]])
                k.append([.1, "key", [["mode", "MSG:yanked"]]])
            elif kind == "save":
                body = "\n".join(self.buf) + "\n"
                k = self.unit("save", op.get("due"), op.get("start"))
                k.append([.3, "key", [["mode", "CMD:"]]])
                k.append([.12, "key", [["mode", "CMD::w"]]])
                k.append([.14, "enter", [["mode", f'WRITTEN:"{self.spec.get("name", "file")}" {len(self.buf)}L, '
                                                   f'{len(body.encode())}B written'], ["save"]]])
            elif kind == "run":
                self.run = op
            else:
                raise SystemExit(f"{self.spec['id']}: unknown op {kind!r}")
        if self.buf != self.after:
            import difflib
            raise SystemExit(f"{self.spec['id']}: the typed file differs from {self.spec['file']}:\n"
                             + "\n".join(difflib.unified_diff(self.after, self.buf, "recorded", "typed", lineterm="")))

    def _open(self, op, nxt, insert):
        i = find(self.buf, op["below"]) + 1 if "below" in op else find(self.buf, op["above"])
        segs = op.get("segments") or [{"text": op["text"]}]
        full = "".join(s["text"] for s in segs)
        indent = len(full) - len(full.lstrip(" "))
        due = segs[0].get("due") or op.get("due") if len(segs) == 1 else None
        k = self.unit(f"{op['op']} {full.strip()[:24]}", due, op.get("start"))
        think = op.get("think", 0)
        if op["op"] == "put":
            k.append([.25 + think, "key", [["mode", "NORMAL"], ["ins", i, [full]], ["caret", i, indent]]])
            self.buf.insert(i, full)
            return False
        k.append([(.18 if insert else .25) + think, "enter" if insert else "key",
                  [["mode", "INSERT"], ["ins", i, [" " * indent]], ["caret", i, indent]]])
        self.buf.insert(i, " " * indent)
        text, prev = " " * indent, None
        for si, s in enumerate(segs):
            if si and (s.get("due") or s.get("typo")):
                k = self.unit(f"seg {s['text'].strip()[:16]}", s.get("due"), s.get("start"))
            elif si == 0 and len(segs) > 1:
                self.units[-1]["due"] = self.at(s.get("due"))
            body = s["text"][indent:] if si == 0 else s["text"]
            wrong = s.get("typo", 0)
            typed = body[:-wrong] + _typo(body[-wrong:], self.rng) if wrong else body
            for ch in typed:
                text += ch
                k.append([char_lead(self.rng, prev, ch), "space" if ch == " " else "key", [["set", i, text], ["caret", i, len(text)]]])
                prev = ch
            for j in range(wrong):
                text = text[:-1]
                k.append([.32 if j == 0 else .07, "back", [["set", i, text], ["caret", i, len(text)]]])
            for ch in body[len(body) - wrong:] if wrong else "":
                text += ch
                k.append([char_lead(self.rng, prev if prev else None, ch), "key", [["set", i, text], ["caret", i, len(text)]]])
                prev = ch
        self.buf[i] = text
        cont = (nxt is not None and nxt["op"] == "open" and "below" in nxt and nxt["below"].strip()
                and nxt["below"].strip() in text and not nxt.get("start") and not nxt.get("think"))
        if not cont:
            k.append([.16, "key", [["mode", "NORMAL"], ["caret", i, max(0, len(text) - 1)]]])
        return bool(cont)

    def _change(self, op):
        i = find(self.buf, op["line"], op.get("nth", 0))
        old = self.buf[i]
        if op["from"] not in old:
            raise SystemExit(f"{self.spec['id']}: {op['from']!r} is not in line {old!r}")
        pos = old.index(op["from"])
        new = old[:pos] + op["to"] + old[pos + len(op["from"]):]
        k = self.unit(f"change {op['from'][:16]}", op.get("due"), op.get("start"))
        cur, first, shift, c = old, True, 0, pos
        for tag, a1, a2, b1, b2 in SequenceMatcher(None, op["from"], op["to"], autojunk=False).get_opcodes():
            if tag == "equal":
                continue
            end = pos + shift + a2
            k.append([(.3 + op.get("think", 0)) if first else .12, "key", [["mode", "INSERT"], ["caret", i, end]]])
            first = False
            for j in range(a2 - a1):
                cur = cur[:end - 1 - j] + cur[end - j:]
                k.append([self.rng.choice([.045, .055, .07]), "back", [["set", i, cur], ["caret", i, end - 1 - j]]])
            c, prev = end - (a2 - a1), None
            for ch in op["to"][b1:b2]:
                cur = cur[:c] + ch + cur[c:]
                c += 1
                k.append([char_lead(self.rng, prev, ch) if prev else .1, "space" if ch == " " else "key", [["set", i, cur], ["caret", i, c]]])
                prev = ch
            shift += (b2 - b1) - (a2 - a1)
        assert cur == new, (cur, new)
        self.buf[i] = new
        k.append([.16, "key", [["mode", "NORMAL"], ["caret", i, max(0, c - 1)]]])

    def _subst(self, op):
        i = find(self.buf, op["line"])
        last = i + op["count"] - 1
        cmd = f":.,+{op['count'] - 1}s/{op['from']}/{op['to']}/"
        k = self.unit("subst", op.get("due"), op.get("start"))
        k.append([.3, "key", [["mode", "NORMAL"], ["caret", i, 0]]])
        typed, prev = "", None
        for ch in cmd:
            typed += ch
            k.append([char_lead(self.rng, prev, ch) if prev else .25, "key", [["mode", "CMD:" + typed]]])
            prev = ch
        fx = []
        for j in range(i, last + 1):
            if op["from"] not in self.buf[j]:
                raise SystemExit(f"{self.spec['id']}: {op['from']!r} is not in line {self.buf[j]!r}")
            self.buf[j] = self.buf[j].replace(op["from"], op["to"], 1)
            fx.append(["set", j, self.buf[j]])
        n = op["count"]
        k.append([.14, "enter", fx + [["mode", f"MSG:{n} substitution{'s' if n != 1 else ''} on {n} line{'s' if n != 1 else ''}"],
                                       ["caret", last, 0]]])

    def schedule(self, earliest, report):
        """Seconds for every key. Each unit ends by its due (as late as allowed, so a line lands with its
        words) and starts after the unit before it and its own start; a unit with too little time is
        typed faster, never more than twice as fast, and the report says when it is late."""
        n = len(self.units)
        durs = [sum(x[0] for x in u["keys"]) for u in self.units]
        latest_end, nxt = [math.inf] * n, math.inf
        for i in range(n - 1, -1, -1):
            u = self.units[i]
            latest_end[i] = min(u["due"] if u["due"] is not None else math.inf, nxt)
            nxt = latest_end[i] - durs[i]
        t = earliest
        for i, u in enumerate(self.units):
            start = max(t, u["start"] if u["start"] is not None else -math.inf)
            if latest_end[i] < math.inf:
                start = max(start, latest_end[i] - durs[i])
            scale = 1.0
            if latest_end[i] < math.inf and durs[i] and start + durs[i] > latest_end[i] + 1e-6:
                scale = max(.5, (latest_end[i] - start) / durs[i])
                late = start + durs[i] * scale - latest_end[i]
                report.append(f"{self.spec['id']}: {u['label']!r} " + (f"late by {late:+.2f} s, typed at x{1 / scale:.2f}"
                                                                       if late > .02 else f"typed faster, x{1 / scale:.2f}"))
            s = start
            for item in u["keys"]:
                s += item[0] * scale
                item.append(s)
            t = s
        return t


def _typo(right, rng):
    """`right` mistyped: each letter swapped for a neighbour on the keyboard, or doubled."""
    rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
    near = {c: (r[max(0, i - 1)] + r[min(len(r) - 1, i + 1)]).replace(c, "") for r in rows for i, c in enumerate(r)}
    return "".join(rng.choice(near.get(c.lower()) or c) for c in right)


def frames_of(burst, fps):
    """The keys on the frame grid, at least one frame apart: [(frame, kind, effects, seconds)]."""
    out, last = [], -1
    for u in burst.units:
        for lead, kind, fx, s in u["keys"]:
            f = max(last + 1, int(math.floor(s * fps + .5)))
            out.append((f, kind, fx, s))
            last = f
    return out


def run_beat(burst, plan, video, after_keys, fps, report):
    """The run: the command recalled (↑), Enter, a breath while it builds, the program's recorded output
    a line a frame, and the window opening `lines_before_window` lines in. Frames, absolute."""
    op, run = burst.run, plan.get("run") or {}
    log = []
    if run.get("log"):
        log = [line for line in (Path(video) / run["log"]).read_text().splitlines() if line.strip()][:run.get("max_lines", 40)]
    lead = min(run.get("lines_before_window", 9), len(log))
    breath = op.get("breath", .4)
    if op.get("run_at"):
        enter = int(math.floor(burst.at(op["run_at"]) * fps + .5))
    elif op.get("pop_due"):
        enter = int(math.floor(burst.at(op["pop_due"]) * fps + .5)) - int(round(breath * fps)) - lead
    else:
        enter = after_keys + int(round(.5 * fps))
    up = max(after_keys + 5, enter - 9)
    if enter < up + 4:
        report.append(f"{burst.spec['id']}: the run's Enter moved from frame {enter} to {up + 6}, after the typing")
        enter = up + 6
    log0 = enter + int(round(breath * fps))
    return {"cmd": run.get("command", "$ ./run"), "up": up, "enter": enter, "pop": log0 + lead,
            "log": [[log0 + i, line] for i, line in enumerate(log)]}


def sentence_anchor(T, t):
    """A cues.json anchor for time t: the latest sentence start at or before it, plus an offset."""
    best = None
    for s in T["tracks"]["narration"]:
        if s["start"] <= t + 1e-9:
            best = s
    if best is None:
        return round(t, 6)
    return {"sentence": best["id"], "at": "start", "offset": round(t - best["start"], 6)}


def load_sources(video, plan):
    out = {}
    for sid, src in plan["sources"].items():
        src = src if isinstance(src, dict) else {"path": src}
        text = src["text"] if "text" in src else (Path(video) / src["path"]).read_text()
        out[sid] = text.rstrip("\n").split("\n") if text.strip() else []
    return out


def speaking(T, a, b):
    return any(w["end"] >= a and w["start"] <= b for s in T["tracks"]["narration"] for w in s.get("words", []))


def build(video, plan, report=None):
    """Write data/typing.json, the type- cues and the typing effects; returns {burst: item}."""
    from . import sfx
    video = Path(video)
    report = [] if report is None else report
    T = tl.build(video, quiet=True)
    fps = T["fps"]
    sources = load_sources(video, plan)
    clips = {c["id"]: c for c in T["tracks"]["scene"]}
    data, cues, streams, accents, ends = {}, {}, [], [], {}
    for spec in plan["bursts"]:
        spec = {**spec, "name": spec.get("name", plan.get("file", "main"))}
        if spec["clip"] not in clips:
            raise SystemExit(f"{spec['id']}: no clip {spec['clip']!r} in the timeline")
        b = Burst(spec, sources, T)
        b.build()
        b.schedule(ends.get(spec["clip"], clips[spec["clip"]]["start"]), report)
        keys = frames_of(b, fps)
        if not keys:
            raise SystemExit(f"{spec['id']}: no keystrokes")
        f0 = keys[0][0]
        run = run_beat(b, plan, video, keys[-1][0], fps, report) if b.run else None
        ends[spec["clip"]] = (run["pop"] / fps + .5) if run else keys[-1][3] + .3
        cue = PREFIX + spec["id"]
        cues[cue] = sentence_anchor(T, f0 / fps)
        save = next((f for f, _, fx, _ in keys if any(x[0] == "save" for x in fx)), None)
        if save is not None:
            cues[cue + "-save"] = sentence_anchor(T, save / fps)
        rel = lambda f: f - f0                                              # noqa: E731
        src = plan["sources"][spec["file"]]
        item = {"cue": cue, "clip": spec["clip"], "file": spec["name"], "before": sources[spec["before"]] if spec.get("before") else [],
                "after": b.after, "steps": [[rel(f), kind, fx] for f, kind, fx, _ in keys], "end": rel(keys[-1][0]),
                "first": src.get("first", 1) if isinstance(src, dict) else 1}
        events = [[round((f - f0) / fps, 4), kind] for f, kind, _, _ in keys]       # the displayed frame is the time
        if run:
            cues[cue + "-run"] = sentence_anchor(T, run["enter"] / fps)
            cues[cue + "-pop"] = sentence_anchor(T, run["pop"] / fps)
            item["run"] = {"cmd": run["cmd"], "up": rel(run["up"]), "enter": rel(run["enter"]), "pop": rel(run["pop"]),
                           "log": [[rel(f), line] for f, line in run["log"]]}
            events += [[round((run["up"] - f0) / fps, 4), "key"], [round((run["enter"] - f0) / fps, 4), "enter"]]
            events += [[round((f - f0) / fps, 4), "tick"] for f, _ in run["log"]]
        data[spec["id"]] = item
        streams.append({"t": cue, "type": "key-tick", "stream": f"typing:{spec['id']}", "events": sorted(events), "exact": True,
                        "sounds": plan.get("sounds", SOUNDS), "source": SOURCE})
        report.append(f"{spec['id']}: {sum(1 for k in keys if k[1] != 'tick')} keys, {keys[0][3]:.2f}-{keys[-1][3]:.2f} s"
                      + (f", run Enter {run['enter'] / fps:.2f} s, window {run['pop'] / fps:.2f} s" if run else ""))
    atomic_json(video / "data" / "typing.json", data)
    cj = json.loads((video / "cues.json").read_text()) if (video / "cues.json").exists() else {}
    clash = [k for k in cues if k in cj and not k.startswith(PREFIX)]
    if clash:
        raise SystemExit(f"cues.json already has {', '.join(clash)}")
    cj = {**{k: v for k, v in cj.items() if not k.startswith(PREFIX)}, **cues}
    atomic_json(video / "cues.json", cj)
    T = tl.build(video, quiet=True)
    for name in cues:
        t = T["cues"][name]
        if name.endswith("-save") and not speaking(T, t - .02, t + .25):
            accents.append({"t": name, **SAVE, "source": SOURCE})       # under a word, the Enter key and the mode line carry it
        elif name.endswith("-pop"):
            accents.append({"t": name, **POP, **({"gain": -14} if speaking(T, t - .02, t + .25) else {}), "source": SOURCE})
    f = video / "audio" / "sfx.json"
    kept = [e for e in (json.loads(f.read_text()) if f.exists() else []) if e.get("source") != SOURCE]
    effects = [sfx.pinned(e, video) for e in kept + streams + accents]
    sfx.check(effects, T)
    copied = sfx.copy_in(video, effects)
    atomic_json(f, effects)
    report += [f"copied in assets/{c} from the sound kit" for c in copied]
    return data


def main(args):
    report = []
    data = build(args.video, json.loads(Path(args.plan).read_text()), report)
    print(f"{len(data)} burst(s) → data/typing.json; cues type-*; their key streams and accents in audio/sfx.json")
    print("\n".join(report))
    return 0
