"""`studio screens VIDEO`: the screens layer's sounds from data/screens.json, and its check.

A film made of working screens (editors, terminals, browsers on desktops; references/screens.md)
writes one log of what happens on them, data/screens.json. The live engine replays it for every frame
(engines/live/src/screens.js), and this command runs the same code in node so the sounds come from
the same schedule as the picture:

  audio/sfx.json      one key-tick stream per action that makes a sound (each typed character, the
                      Enter, the chord of a tab or desktop switch, a click or a drag's press and
                      release), on the action's cue; effects other generators or the builder made are
                      kept (each generated one carries "source": "screens")

and reports where each desktop switch landed: moved into the nearest gap between sentences, or not
placeable without sitting on a spoken word.

The check (`studio check`, kind `screens`, whenever data/screens.json exists):

  a failure    a name the log doesn't declare (a desktop, tab, file, run or cue); a switch that can't
               land between sentences; an action on a desktop before it arrives; screens streams in
               audio/sfx.json that differ from what the log makes now (run `studio screens` again)
  a warning    a terminal line that has to wrap inside a token at its window's width (widen the window,
               shorten the line or lower the type size); typing faster than MAX_KEYS a second

It also hands `studio check` the moments worth sampling (each command typed, each output shown, each
landing), so legibility and bounds are checked where the screens change, not only at sentence ends.
"""
import json
from pathlib import Path

from . import proc
from . import timeline as tl
from .env import engine_dir
from .workspace import atomic_json

SOURCE = "screens"
FILE = Path("data") / "screens.json"

BRIDGE = r"""
import { compile, streams, moments, rates, MAX_KEYS, SOUNDS } from %(model)s
import { wrapLine, terminalCols, INSET, GAP } from %(draw)s
const input = JSON.parse(await new Promise(r => { let s = ''; process.stdin.on('data', d => s += d); process.stdin.on('end', () => r(s)) }))
const { spec, runs, timeline, width } = input
let k
try { k = compile(spec, timeline, runs) } catch (e) { console.log(JSON.stringify({ error: e.message })); process.exit(0) }
const wraps = []
for (const d of k.desktops) {
  const term = d.kind === 'terminal' ? { size: d.size ?? 30, frac: (d.frame ?? [0, 0, 1, 1])[2] }
    : d.kind === 'editor' && d.panel ? { size: d.panel.size ?? 22, frac: (d.frame ?? [0, 0, 1, 1])[2] } : null
  if (!term) continue
  const cols = terminalCols(term.frac * (width - 2 * INSET) - (term.frac < 1 ? GAP / 2 : 0), term.size)
  const opened = Object.fromEntries(k.actions.filter(a => a.on === d.id && a.new).map(a => [a.tab, a.new]))
  const tab = id => (d.tabs ?? []).find(t => t.id === id) ?? opened[id] ?? d.tabs?.[0] ?? d.panel ?? {}
  for (const a of k.actions.filter(a => a.on === d.id)) {
    const texts = []
    if (a.kind === 'type') String(a.type).split('\n').forEach((part, j) => texts.push((j ? tab(a.tab).cont ?? '' : tab(a.tab).prompt ?? '$ ') + part))
    for (const l of a.output ?? []) texts.push(l.text)
    for (const text of texts) if (wrapLine(text, cols).midToken) wraps.push({ i: a.i, on: d.id, t: a.t, cols, text })
  }
}
console.log(JSON.stringify({
  streams: streams(k, { ...SOUNDS, ...(spec.sounds ?? {}) }), moments: moments(k), rates: rates(k), problems: k.problems, wraps, maxKeys: MAX_KEYS,
  switches: k.actions.filter(a => a.kind === 'switch').map(a => ({ i: a.i, to: a.on, cue: a.cueAt, t: a.t, ms: a.ms, gap: a.gap })),
  actions: k.actions.length,
}))
"""


def exists(video):
    return (Path(video) / FILE).exists()


def load(video):
    """data/screens.json and the runs it names, as the engine loads them (screens-draw.js loadScreens)."""
    video = Path(video)
    spec = json.loads((video / FILE).read_text())
    for d in spec.get("desktops", []):
        for name, p in (d.get("files") or {}).items():
            if isinstance(p, str) and "\n" not in p and Path(p).suffix:
                f = video / p
                if not f.exists():
                    raise SystemExit(f"{FILE}: desktop {d.get('id')} file {name}: no {p}")
                d["files"][name] = f.read_text()
    runs = {}
    for name, p in (spec.get("runs") or {}).items():
        if isinstance(p, str):
            f = video / p
            if not f.exists():
                raise SystemExit(f"{FILE}: run {name}: no {p}")
            runs[name] = json.loads(f.read_text())
        else:
            runs[name] = p
    return spec, runs


def replay(video, timeline=None):
    """The log compiled in node against the timeline: streams, moments, rates, problems, wraps, switches."""
    video = Path(video)
    spec, runs = load(video)
    T = timeline or tl.load(video)
    src = engine_dir("live") / "src"
    script = BRIDGE % {"model": json.dumps((src / "screens.js").as_uri()), "draw": json.dumps((src / "screens-draw.js").as_uri())}
    width = tl.layout(video).get("width", 1920)
    r = proc.run([proc.tool("node"), "--input-type=module", "-e", script], text=True, capture_output=True,
                       input=json.dumps({"spec": spec, "runs": runs, "timeline": T, "width": width}))
    if r.returncode != 0:
        raise SystemExit(f"screens: node failed: {r.stderr.strip()[-800:]}")
    out = json.loads(r.stdout)
    if "error" in out:
        raise SystemExit(f"{FILE}: {out['error']}")
    return out


def build(video, report=None):
    """Write the log's sounds into audio/sfx.json; returns the replay."""
    from . import sfx
    video = Path(video)
    report = [] if report is None else report
    T = tl.build(video, quiet=True)
    got = replay(video, T)
    f = video / "audio" / "sfx.json"
    kept = [e for e in (json.loads(f.read_text()) if f.exists() else []) if e.get("source") != SOURCE]
    effects = [sfx.pinned(e, video) for e in kept + got["streams"]]
    sfx.check(effects, T)
    copied = sfx.copy_in(video, effects)
    f.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(f, effects)
    for s in got["switches"]:
        moved = s["t"] - s["cue"]
        report.append(f"switch to {s['to']} ({s['ms'] * 1000:.0f} ms): "
                      + (f"moved {moved:+.2f} s into a gap between sentences" if abs(moved) > 1e-3 and s["gap"]
                         else "lands in a gap" if s["gap"] else "NO gap within reach: it sits on a spoken word"))
    report += [f"problem: action {p['i'] + 1} ({p['kind']}): {p['why']}" for p in got["problems"]]
    report += [f"copied in assets/{c} from the sound kit" for c in copied]
    return got


def check(video, timeline=None):
    """The screens check's rows (see the module docstring)."""
    video = Path(video)
    if not exists(video):
        return []
    try:
        got = replay(video, timeline)
    except SystemExit as e:
        return [{"check": "screens", "clip": "screens", "ok": False, "detail": str(e)}]
    rows = []
    for p in got["problems"]:
        rows.append({"check": "screens", "clip": "screens", "t": round(p["t"], 2), "ok": False,
                     "detail": f"action {p['i'] + 1} ({p['kind']}): {p['why']}"})
    for w in got["wraps"]:
        rows.append({"check": "screens", "clip": "screens", "t": round(w["t"], 2), "ok": True, "severity": "warning",
                     "detail": f"action {w['i'] + 1} on {w['on']}: {w['text'][:48]!r} wraps inside a token at {w['cols']} columns; "
                               "widen the window, shorten the line or lower the type size"})
    for r in got["rates"]:
        if r["rate"] > got["maxKeys"] + .5:
            rows.append({"check": "screens", "clip": "screens", "t": round(r["t"], 2), "ok": True, "severity": "warning",
                         "detail": f"action {r['i'] + 1} on {r['on']} types {r['rate']:.0f} keys a second; "
                                   f"over {got['maxKeys']} reads as autotype"})
    f = video / "audio" / "sfx.json"
    have = [e for e in (json.loads(f.read_text()) if f.exists() else []) if e.get("source") == SOURCE]
    strip = lambda e: {k: v for k, v in e.items() if k in ("t", "stream", "events")}       # noqa: E731
    if [strip(e) for e in have] != [strip(e) for e in got["streams"]]:
        rows.append({"check": "screens", "clip": "screens", "ok": False,
                     "detail": f"audio/sfx.json's screens sounds ({len(have)}) differ from the log's ({len(got['streams'])}); "
                               "run `studio screens VIDEO`"})
    if not rows or all(r["ok"] for r in rows):
        rows.append({"check": "screens", "clip": "screens", "ok": True,
                     "detail": f"{got['actions']} actions, {len(got['switches'])} switches, all between sentences"})
    return rows


def sample_requests(video, timeline, clips=None):
    """[{clip, t}] at the moments the screens change (moments in screens.js), for the boxed checks."""
    if not exists(video):
        return []
    try:
        got = replay(video, timeline)
    except SystemExit:
        return []
    out = []
    for m in got["moments"]:
        c = next((c for c in timeline["tracks"]["scene"] if c["start"] <= m["t"] < c["end"]), None)
        if c and (clips is None or c["id"] in clips):
            out.append({"clip": c["id"], "t": round(m["t"] - c["start"], 3)})
    return out


def main(args):
    report = []
    got = build(args.video, report)
    print(f"{got['actions']} screen action(s) → {len(got['streams'])} sound stream(s) in audio/sfx.json")
    print("\n".join(report))
    return 0
