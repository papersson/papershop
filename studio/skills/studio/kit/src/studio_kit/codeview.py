"""The code view: what the typed-code editor shows of a program over time, apart from any renderer.

data/codeview.json, authored beside the typing plan, names the program's displayed source (a burst
of data/typing.json) and how the teaching shows it. Times are cue names, or [name, offset seconds],
so a moved narration moves the view with it. Line numbers are the program's own, from 1.

  {"source": "loop",                     the burst whose `after` is the finished program
   "open":   [["type-s2", "type-s2-end"], …]      the editor is open in these spans, collapsed between
   "folds":  [{"lines": [3, 9], "label": "fn draw(…)", "from": "cue", "to": "cue"}]
                                         lines shown as one row (the label) between from and to
   "highlights": [{"lines": [12, 14], "from": ["cue", 0], "to": "cue2", "refer": "cue"}]
                                         lit from `from`; `refer` is when a sentence first names them
   "helpers": [{"id", "title", "text", "from", "to"}]       a card for a piece folded away or external
   "payoff": "cue",                      from here the complete program shows, no folds, nothing hidden
   "externals": ["Instant", …],          names the program uses that are not defined in it
   "lead": 0.6}                          seconds a highlight precedes the words that refer to it

Source order is kept by construction: the view only hides ranges, it never reorders lines.
`project` is the model read by the live Editor (engines/live/src/code.js). `check` is the code-view check of `studio check`.
"""
import json
import re
from pathlib import Path

LEAD = 0.6
KEYWORDS = set("""as break const continue crate else enum false fn for if impl in let loop match mod move mut pub
ref return self Self static struct super trait true type unsafe use where while int float double char bool void
def var function import from class new None True False and or not lambda print""".split())
PRIMITIVES = set("i8 i16 i32 i64 u8 u16 u32 u64 usize isize f32 f64 str String Vec Option Some Ok Err Result bool".split())


def load(video):
    f = Path(video) / "data" / "codeview.json"
    return json.loads(f.read_text()) if f.exists() else None


def when(spec, cues):
    """A time spec (a cue name, or [name, offset]) in timeline seconds, or None for no spec."""
    if spec is None:
        return None
    name, offset = (spec, 0.0) if isinstance(spec, str) else (spec[0], float(spec[1]))
    if name not in cues:
        raise ValueError(f"codeview.json names the cue {name!r}, which the timeline does not have")
    return cues[name] + offset


def is_open(view, cues, t):
    spans = view.get("open")
    return True if not spans else any(when(a, cues) <= t < when(b, cues) for a, b in spans)


def project(lines, view, cues, t):
    """The rows the editor shows at time t: [{"n": first line number, "to": last, "text", "kind"}] with
    kind "line", "fold" (text is the fold's label) or "lit" (a highlighted line). Complete from `payoff`."""
    payoff = when(view.get("payoff"), cues)
    complete = payoff is not None and t >= payoff
    folds = [] if complete else [f for f in view.get("folds", [])
                                 if when(f.get("from"), cues) is None or when(f["from"], cues) <= t
                                 if when(f.get("to"), cues) is None or t < when(f["to"], cues)]
    lit = set()
    for h in ([] if complete else view.get("highlights", [])):
        if when(h["from"], cues) <= t < (when(h.get("to"), cues) or float("inf")):
            lit.update(range(h["lines"][0], h["lines"][1] + 1))
    rows, n = [], 1
    starts = {f["lines"][0]: f for f in folds}
    while n <= len(lines):
        f = starts.get(n)
        if f:
            rows.append({"n": n, "to": f["lines"][1], "text": f["label"], "kind": "fold"})
            n = f["lines"][1] + 1
        else:
            rows.append({"n": n, "to": n, "text": lines[n - 1], "kind": "lit" if n in lit else "line"})
            n += 1
    return rows


def names(text):
    """Identifiers used in a line of code, without comments, strings, keywords, fields after a dot or paths' tails."""
    text = re.sub(r"//.*", "", re.sub(r'"[^"]*"', '""', text))
    if re.match(r"\s*(use|import|from|#include)\b", text):
        return []
    return [m.group(2) for m in re.finditer(r"(?<![\w.])(\.?)([A-Za-z_]\w*)", text) if not m.group(1)
            and m.group(2) not in KEYWORDS | PRIMITIVES and not text[max(0, m.start() - 2):m.start()] == "::"]


def defined(text):
    """Names a program defines: let/const/static/fn/struct/enum/type bindings, and parameters or fields (name: type)."""
    text = re.sub(r"//.*", "", text)
    out = set(re.findall(r"\b(?:let[ \t]+(?:mut[ \t]+)?|const[ \t]+|static[ \t]+|struct[ \t]+|enum[ \t]+|fn[ \t]+|type[ \t]+|for[ \t]+)(\w+)", text))
    out |= set(re.findall(r"\b(\w+)\s*:(?!:)", text))
    for use in re.findall(r"^\s*use\s+([^;]+);", text, re.M):         # what a use brings in: the last segments
        out |= set(re.findall(r"(\w+)(?=\s*[,}]|\s*$)", use))
    return out


def closure(lines, folds=(), externals=()):
    """[(line number, name)] of names a program's lines use that nothing defines, no fold declares and no
    external is listed for. A heuristic on the text, not a compiler: it finds a name that is simply not
    there."""
    known = set(externals) | defined("\n".join(lines))
    for f in folds:
        known |= set(re.findall(r"[A-Za-z_]\w*", f.get("label", "")))
    return [(i, nm) for i, line in enumerate(lines, 1) for nm in names(line) if nm not in known]


def check(video):
    """check rows for data/codeview.json (none without it): ranges and order, highlight lead, a payoff, closure."""
    view = load(video)
    if view is None:
        return []
    from . import timeline as tl
    bad = lambda detail, t=0.0: {"check": "code-view", "clip": "code", "ok": False, "t": round(t, 2), "detail": detail}   # noqa: E731
    typing = json.loads((Path(video) / "data" / "typing.json").read_text())
    if view.get("source") not in typing:
        return [bad(f"source {view.get('source')!r} is not a burst of data/typing.json")]
    lines = typing[view["source"]]["after"]
    cues = tl.build(video, quiet=True)["cues"]
    rows = []
    try:
        for f in view.get("folds", []):
            a, b = f["lines"]
            if not (1 <= a <= b <= len(lines)):
                rows.append(bad(f"fold {f['lines']} is outside the program's {len(lines)} lines"))
            when(f.get("from"), cues), when(f.get("to"), cues)
        ordered = sorted(view.get("folds", []), key=lambda f: f["lines"][0])
        for p, q in zip(ordered, ordered[1:]):
            if q["lines"][0] <= p["lines"][1] and (when(q.get("from"), cues) or 0) < (when(p.get("to"), cues) or 1e9):
                rows.append(bad(f"folds {p['lines']} and {q['lines']} overlap while both show"))
        lead = view.get("lead", LEAD)
        for h in view.get("highlights", []):
            a, b = h["lines"]
            if not (1 <= a <= b <= len(lines)):
                rows.append(bad(f"highlight {h['lines']} is outside the program's {len(lines)} lines"))
            if h.get("refer") is not None:
                gap = when(h["refer"], cues) - when(h["from"], cues)
                if gap < lead - 1e-6:
                    rows.append(bad(f"highlight {h['lines']} lights {gap:.2f} s before the words that name it; it leads by "
                                    f"{lead:g} s", when(h["from"], cues)))
        if view.get("payoff") is None:
            rows.append(bad("no payoff: the video should end on the complete program (set `payoff` to its cue)"))
        else:
            t = when(view["payoff"], cues)
            if any(r["kind"] == "fold" for r in project(lines, view, cues, t)):
                rows.append(bad("the payoff view still has a fold", t))
        for i, nm in closure(lines, (), view.get("externals", [])):
            rows.append(bad(f"line {i} uses {nm!r}, which the program does not define (list it in `externals` if it is a library name)"))
        # what an earlier view shows must close too: a fold has to declare what the lines around it use
        for f in view.get("folds", []):
            shown = [l for i, l in enumerate(lines, 1) if not f["lines"][0] <= i <= f["lines"][1]]
            gone = {nm for _, nm in closure(shown, [f], view.get("externals", []))}
            if gone:
                rows.append(bad(f"with lines {f['lines']} folded, {', '.join(sorted(gone))} is used but neither defined nor "
                                "named in the fold's label", when(f.get("from"), cues) or 0.0))
    except (ValueError, KeyError, TypeError) as e:
        return [bad(f"codeview.json: {e}")]
    return rows or [{"check": "code-view", "clip": "code", "ok": True,
                     "detail": f"{len(view.get('folds', []))} folds, {len(view.get('highlights', []))} highlights, a payoff, closed names"}]
