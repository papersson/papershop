"""The colour legend check (`studio check --only legend`): one colour, one meaning, for the whole video.

A video declares its legend in video.json, meaning -> colour, the colour a theme name of the video's
engine (live: "hot", "cold", "bad", ...; Remotion: "amber", "ice", "coral", ...) or "#rrggbb":

  "legend": {"request": "warm", "error": "bad", "focus": "hot"}

An element carries a meaning by its `means` tag (live: any drawing call's {means: 'request'};
Remotion: Txt, Rect and Box take means="request"), or by its name, when the meaning's words appear
in it ("box request" means request). The engines' boxes report each named element's fill and stroke
as the browser resolves them, so at the check's sample times (moments.check_samples, the boxes the
other checks gather) the check knows every named element's colours and meaning, and warns when

  (a) one colour stands for two meanings: the legend gives two meanings one colour, or elements
      tagged with two meanings share a colour the legend leaves free
  (b) one meaning is drawn in two colours: in a colour other than its own in the legend, or, for a
      meaning the legend leaves out, in two colours
  (c) a colour the legend reserves for a meaning is on an element tagged with another meaning or
      none. A neutral colour (ink, dim, faint, the panels and outlines) is never reserved

Only accent colours count (and those the legend names): a neutral, a blend mid-transition and a tint
(alpha under 0.5) are never a meaning. Warnings, since names and tags are partly heuristic. A video
with no legend is not checked; when its elements carry `means` tags, one line says the legend is
missing. A legend colour that is no theme colour fails.

Video-wide but incremental: each chapter's elements are kept per clip key in .cache/check/, so a
check that samples only the changed chapters still compares the whole video.
"""
import json
import re
from functools import lru_cache

from . import settings
from .env import engine_dir

THEMES = {"live": ("live", "src/theme.css"), "remotion": ("remotion", "src/kit/theme.ts"),
          "motion-canvas": ("motion-canvas", "src/base.ts")}
ACCENTS = {"live": ("hot", "warm", "cold", "bad", "good", "log", "key"),
           "remotion": ("amber", "ice", "coral"), "motion-canvas": ("amber", "ice", "coral")}
TINT = 0.5          # alpha below which a colour is a tint, not the colour
FAINT = 0.05        # opacity below which an element is not shown
EXAMPLES = 3        # elements named per warning


def _key(name):
    return name.strip().lower().replace("_", "-")


@lru_cache(maxsize=None)
def theme(engine):
    """{"colours": {name: hex}, "names": {hex: first name}, "accents": {hex}, "neutral": {hex}} of an
    engine's theme file."""
    folder, rel = THEMES.get(engine, THEMES["live"])
    text = (engine_dir(folder) / rel).read_text()
    found = re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", text) or re.findall(r"export const (\w+) = '(#[0-9A-Fa-f]{6})'", text)
    colours = {_key(k): v.upper() for k, v in found}
    names = {}
    for k, v in colours.items():
        names.setdefault(v, k)
    accents = {colours[a] for a in ACCENTS.get(engine, ACCENTS["live"]) if a in colours}
    return {"colours": colours, "names": names, "accents": accents, "neutral": set(colours.values()) - accents}


def hex_of(value):
    """A colour as an engine reports it ("rgb(r, g, b)", "rgba(r, g, b, a)" or "#rrggbb") as
    "#RRGGBB"; None for none, transparent, a gradient or a tint."""
    v = str(value or "").strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", v):
        return v.upper()
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)", v)
    if not m:
        return None
    alpha = m.group(4)
    if alpha is not None and (float(alpha.rstrip("%")) / (100 if alpha.endswith("%") else 1)) < TINT:
        return None
    return "#" + "".join(f"{round(float(m.group(i))):02X}" for i in (1, 2, 3))


def declared(video):
    """video.json's legend as ({meaning: hex}, [problems]), resolved against the video's engine theme."""
    cfg = settings.load(video)
    written = cfg.get("legend") or {}
    if not isinstance(written, dict):
        return {}, ["video.json legend must map each meaning to a colour, e.g. {\"request\": \"warm\"}"]
    colours = theme(cfg["engine"])["colours"]
    legend, problems = {}, []
    for meaning, colour in written.items():
        c = hex_of(colour) if str(colour).startswith("#") else colours.get(_key(str(colour)))
        if c:
            legend[meaning] = c
        else:
            problems.append(f"legend {meaning!r}: {colour!r} is not a {cfg['engine']} theme colour "
                            f"({', '.join(sorted(colours))}) or #rrggbb")
    return legend, problems


def seen(frames):
    """{clip: [{t, name, means?, colours}]}: every shown, named element once per clip (at its first
    sample) with its colours as hex; every sampled clip has an entry."""
    out = {}
    for f in frames:
        items = out.setdefault(f["clip"], [])
        have = {(o["name"], o.get("means"), tuple(o["colours"])) for o in items}
        for b in f["boxes"]:
            if b["name"] == "caption" or b.get("opacity", 1) < FAINT:
                continue
            colours = sorted({c for c in (hex_of(b.get("fill")), hex_of(b.get("stroke"))) if c})
            key = (b["name"], b.get("means"), tuple(colours))
            if (colours or b.get("means")) and key not in have:
                have.add(key)
                items.append({"t": f["t"], "name": b["name"], "colours": colours, **({"means": b["means"]} if b.get("means") else {})})
    return out


def _words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def meaning(o, legend):
    """An element's meaning: its `means` tag, else the legend meaning whose words its name contains
    (the longest when several do), else None."""
    if o.get("means"):
        return o["means"]
    words = _words(o["name"])
    hits = [m for m in legend if (w := _words(m)) and any(words[i:i + len(w)] == w for i in range(len(words) - len(w) + 1))]
    return max(hits, key=len, default=None)


def findings(legend, obs, engine):
    """The warnings for observations `obs` ({clip: seen items}) against `legend` ({meaning: hex}):
    [{"detail", "clip", "t"?}], one per colour or meaning at fault."""
    th = theme(engine)
    name = lambda c: th["names"].get(c, c)
    owners = {}
    for m, c in legend.items():
        owners.setdefault(c, []).append(m)
    reserved = {c: ms for c, ms in owners.items() if c not in th["neutral"]}
    colours_of = {m: {c: None} for m, c in legend.items()}               # meaning -> {hex: first example}
    meanings_of = {c: {m: None for m in ms} for c, ms in owners.items()}  # hex -> {meaning: first example}
    misused = {}                                                         # hex -> [examples]
    for clip, items in obs.items():
        for o in items:
            m = meaning(o, legend)
            at = {"clip": clip, "t": o["t"], "what": f"{o['name'][:32]!r}" + (f" (means {m})" if m else "") + f" at {clip} t={o['t']}"}
            for c in o["colours"]:
                if c in reserved and m not in reserved[c]:
                    misused.setdefault(c, []).append(at)
                elif m and (c in th["accents"] or legend.get(m) == c):
                    colours_of.setdefault(m, {}).setdefault(c, at)
                    meanings_of.setdefault(c, {}).setdefault(m, at)
    out = []

    def row(detail, examples):
        first = next((e for e in examples if e), None)
        return {"detail": detail, **({"clip": first["clip"], "t": first["t"]} if first else {"clip": "video"})}

    def told(label, at):
        return label + (" (legend)" if at is None else f" ({at['what']})")
    for c, ms in meanings_of.items():
        if len(ms) > 1:
            out.append(row(f"{name(c)} stands for " + " and ".join(told(m, at) for m, at in ms.items()), ms.values()))
    for m, cs in colours_of.items():
        if len(cs) > 1:
            out.append(row(f"{m} is drawn in " + " and ".join(told(name(c), at) for c, at in cs.items()), cs.values()))
    for c, uses in misused.items():
        more = f" and {len(uses) - EXAMPLES} more" if len(uses) > EXAMPLES else ""
        out.append(row(f"{name(c)}, which the legend keeps for {' and '.join(reserved[c])}, is on "
                       + ", ".join(u["what"] for u in uses[:EXAMPLES]) + more
                       + f": tag it means: '{reserved[c][0]}' if that is what it is, or recolour it", uses))
    return out


def _cache(video, fmt, samples):
    from .check import _cache_file
    return _cache_file(video, fmt, samples).with_suffix(".legend.json")


def check(video, samples=3, engine=None, boxes=None, clips=None, fmt=None, keys=None):
    """The legend check's rows. `boxes` ((layout, frames), as check gathers them) cover `clips`
    (None: every clip); with `keys` ({clip: clip key}) the other chapters' elements come from the
    cache, or are sampled here when it has none for their key."""
    legend, problems = declared(video)
    frames = boxes[1] if boxes else []
    if not legend and not problems:
        tag = next(((f, b) for f in frames for b in f["boxes"] if b.get("means")), None)
        return [{"check": "legend", "clip": tag[0]["clip"], "t": tag[0]["t"], "ok": True, "severity": "warning",
                 "detail": f"{tag[1]['name']!r} means {tag[1]['means']!r}, but video.json declares no legend to check it against"}] if tag else []
    from .check import _boxes
    from .engine import Engine
    obs = seen(frames)
    if keys is not None:
        f = _cache(video, fmt, samples)
        cache = json.loads(f.read_text()) if f.exists() else {}
        cache.update({cid: {"key": keys[cid], "seen": items} for cid, items in obs.items() if cid in keys})
        missing = {cid for cid in keys if cid not in obs and cache.get(cid, {}).get("key") != keys[cid]}
        if missing:
            more = seen(_boxes(video, samples, engine or Engine(video, fmt=fmt), missing)[1])
            cache.update({cid: {"key": keys[cid], "seen": more.get(cid, [])} for cid in missing})
        cache = {cid: cache[cid] for cid in keys if cid in cache}
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(cache, indent=1, sort_keys=True))
        obs = {cid: v["seen"] for cid, v in cache.items()}
    elif boxes is None:
        obs = seen(_boxes(video, samples, engine or Engine(video, fmt=fmt))[1])
    rows = [{"check": "legend", "clip": "video", "ok": False, "detail": p} for p in problems]
    warned = findings(legend, obs, settings.load(video)["engine"])
    rows += [{"check": "legend", "ok": True, "severity": "warning", **w} for w in warned]
    if not rows:
        tagged = sum(bool(meaning(o, legend)) for items in obs.values() for o in items)
        rows.append({"check": "legend", "clip": "video", "ok": True,
                     "detail": f"{len(legend)} meanings; {tagged} tagged elements in {len(obs)} chapter{'s' * (len(obs) != 1)} keep to them"})
    return rows
