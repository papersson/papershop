"""`studio sfx VIDEO CUES.json`: synthesised effects placed on the timeline, and `studio sound-lab`.

CUES.json is a list of {"t": seconds, "type": "click", "gain": 0}; `t` may also be a cue or beat
name ("reveal:s1_03", "beat_3", "downbeat_1", "hit_2") from the timeline. The voices are small numpy
synths (a click, a pop, a thump and a whoosh), so effects are code like everything else and land on
the measured beat. `studio sfx` checks the cues and keeps them as audio/sfx.json; every mix renders
them against the timeline it mixes (`rendered`, into audio/sfx.wav, again only when a resolved time
or a voice changed), so a re-narration moves an effect with its cue. The timeline mixes it at -8 dB
under the narration.

Sound effects are off by default and belong in pauses. The sound lab renders candidates for each
type, each played alone and in context (after a sentence of the narration, in its pause), on one
page with a radio group per type and a "Copy choices" export, so the choice is made by listening.
"""
import hashlib
import json
import math
from pathlib import Path

from . import timeline as tl
from .workspace import atomic_json

RATE = 48_000
SEED = 42
KINDS = ("click", "pop", "thump", "whoosh")
NEEDS = "sfx needs numpy and soundfile: run `studio doctor --fetch --extra audio`"


def _noise(n):
    """Deterministic noise (the LCG the article's synth uses), so a render is identical every run."""
    import numpy as np
    out = np.empty(n)
    s = SEED
    for i in range(n):
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        out[i] = s / 2147483648 - 1
    return out


def voice(kind, **p):
    """One effect as a float array at RATE."""
    import numpy as np
    if kind == "click":
        f, d = p.get("freq", 1800), p.get("decay", 90)
        t = np.arange(int(0.05 * RATE)) / RATE
        return np.sin(2 * math.pi * f * t) * np.exp(-t * d) * 0.5
    if kind == "pop":
        f, d = p.get("freq", 600), p.get("decay", 30)
        t = np.arange(int(0.15 * RATE)) / RATE
        return np.sin(2 * math.pi * (f + 900 * t) * t) * np.exp(-t * d) * 0.4
    if kind == "thump":
        f, d = p.get("freq", 90), p.get("decay", 9)
        t = np.arange(int(0.5 * RATE)) / RATE
        return np.sin(2 * math.pi * (f - 60 * t) * t) * np.exp(-t * d) * 0.9
    if kind == "whoosh":
        n = int(p.get("length", 0.35) * RATE)
        t = np.arange(n) / RATE
        return _noise(n) * np.sin(math.pi * np.minimum(1, t / (n / RATE))) * 0.25
    raise SystemExit(f"unknown effect {kind!r}: click, pop, thump or whoosh")


def _time(t, timeline):
    if isinstance(t, (int, float)):
        return float(t)
    if t in timeline.get("cues", {}):
        return timeline["cues"][t]
    b = timeline.get("beats", {})
    for prefix, key in (("downbeat_", "downbeats"), ("beat_", "beats"), ("hit_", "hits")):
        if t.startswith(prefix) and t[len(prefix):].isdigit():
            i = int(t[len(prefix):]) - 1
            if 0 <= i < len(b.get(key, [])):
                return b[key][i]
    return None


def resolve_time(t, timeline):
    at = _time(t, timeline)
    if at is None:
        raise SystemExit(f"no time for cue {t!r}")
    return at


def unresolved(cues, timeline):
    """The effect times in `cues` this timeline has no time for (a cue a re-narration dropped)."""
    return [c["t"] for c in cues if _time(c["t"], timeline) is None]


def render(cues, timeline):
    """The effects on one float track, unclipped: the timeline's -8 dB comes later, in the mix, so an
    effect over full scale here is not over it there, and the master's limiter takes what still is."""
    import numpy as np
    placed = [(resolve_time(c["t"], timeline), voice(c["type"], **c.get("params", {})), 10 ** (c.get("gain", 0) / 20)) for c in cues]
    end = max(t * RATE + len(v) for t, v, _ in placed) if placed else RATE
    buf = np.zeros(int(max(end, timeline["duration"] * RATE)) + RATE, dtype=np.float32)
    for t, v, g in placed:
        i = int(t * RATE)
        buf[i:i + len(v)] += (v * g).astype(np.float32)
    return buf


def write_wav(path, buf, subtype="PCM_24"):
    import soundfile as sf
    sf.write(path, buf, RATE, subtype=subtype)


def check(cues, timeline):
    """Stop on an effect with no time in this timeline, an unknown type or a gain that isn't a number."""
    for c in cues:
        resolve_time(c["t"], timeline)
        if c.get("type") not in KINDS:
            raise SystemExit(f"unknown effect {c.get('type')!r}: {', '.join(KINDS)}")
        if not isinstance(c.get("gain", 0), (int, float)):
            raise SystemExit(f"effect at {c['t']!r}: gain must be dB")


def rendered(video, timeline):
    """audio/sfx.wav for this timeline: audio/sfx.json's cues resolved against it and rendered,
    again only when a resolved time, a voice or this synth changed (the key is kept beside the
    mix cache)."""
    video = Path(video)
    cues = json.loads((video / "audio" / "sfx.json").read_text())
    if unresolved(cues, timeline):
        raise SystemExit(f"audio/sfx.json: no time for {', '.join(map(repr, unresolved(cues, timeline)))} in the "
                         "timeline (a re-narration drops a reveal: cue whose hold is gone); `studio sfx VIDEO CUES` "
                         "with times that exist")
    placed = [{**c, "t": resolve_time(c["t"], timeline)} for c in cues]
    key = hashlib.sha1(json.dumps(placed, sort_keys=True).encode() + Path(__file__).read_bytes()).hexdigest()[:16]
    out, kept = video / "audio" / "sfx.wav", video / ".cache" / "sound" / "sfx.key"
    if out.exists() and kept.exists() and kept.read_text() == key:
        return out
    try:
        write_wav(out, render(placed, timeline), "FLOAT")
    except ImportError:
        if not out.exists():
            raise SystemExit(NEEDS)
        # a video from before effects were placed at mix time: its render, at the times it was made
        print(f"warn: audio/sfx.wav kept as rendered, effects not re-placed ({NEEDS})")
        return out
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_text(key)
    return out


def main(args):
    video = Path(args.video)
    cues = json.loads(Path(args.cues).read_text())
    try:
        import numpy, soundfile  # noqa: F401  (every mix renders the effects)
    except ImportError:
        raise SystemExit(NEEDS)
    check(cues, tl.build(video, quiet=True))      # cue and beat names resolve against the current sources
    atomic_json(video / "audio" / "sfx.json", cues)
    rendered(video, tl.build(video))
    print(f"{len(cues)} effects → audio/sfx.json (each mix places them on the current timeline)")
    return 0


# --- the sound lab ---------------------------------------------------------------------------------

CANDIDATES = {
    "click": [{"freq": 1200}, {"freq": 1800}, {"freq": 2600, "decay": 140}],
    "pop": [{"freq": 400}, {"freq": 600}, {"freq": 900, "decay": 45}],
    "thump": [{"freq": 60}, {"freq": 90}, {"freq": 120, "decay": 14}],
    "whoosh": [{"length": 0.25}, {"length": 0.35}, {"length": 0.6}],
}


def lab(video):
    """out/sound-lab/index.html: candidates for every effect type, alone and in a pause of the narration."""
    import numpy as np
    video = Path(video)
    out = video / "out" / "sound-lab"
    out.mkdir(parents=True, exist_ok=True)
    t = tl.load(video)
    narr = video / "audio" / "narration.mp3"
    rows = []
    for kind, variants in CANDIDATES.items():
        for i, p in enumerate(variants, 1):
            alone = np.zeros(int(1.0 * RATE) + RATE // 2, dtype=np.float32)
            v = voice(kind, **p).astype(np.float32)
            alone[RATE // 4:RATE // 4 + len(v)] = v
            write_wav(out / f"{kind}{i}_alone.wav", alone)
            rows.append({"kind": kind, "n": i, "params": p, "alone": f"{kind}{i}_alone.wav"})
    if narr.exists() and t["tracks"]["narration"]:
        # In context: the first sentence's ending and its pause, with the effect placed 0.3 s after it.
        s = t["tracks"]["narration"][0]
        for r in rows:
            v = voice(r["kind"], **r["params"]).astype(np.float32)
            n = int((s["end"] + 1.2) * RATE)
            buf = np.zeros(n + RATE, dtype=np.float32)
            from . import proc
            pcm = proc.ffmpeg("-i", narr, "-t", f"{s['end'] + 0.3:.2f}", "-f", "f32le", "-ac", "1", "-ar", RATE, "-",
                              capture_output=True).stdout
            voice_pcm = np.frombuffer(pcm, dtype=np.float32)
            buf[:len(voice_pcm)] = voice_pcm[:len(buf)]
            i = int((s["end"] + 0.3) * RATE)
            buf[i:i + len(v)] += v * 0.7
            name = f"{r['kind']}{r['n']}_context.wav"
            write_wav(out / name, buf)
            r["context"] = name
    (out / "index.html").write_text(lab_html(rows, t), encoding="utf-8")
    return out / "index.html"


def lab_html(rows, t):
    kinds = list(dict.fromkeys(r["kind"] for r in rows))
    blocks = []
    for k in kinds:
        items = "".join(
            f'<label class="c"><input type="radio" name="{k}" value="{r["n"]}"{" checked" if r["n"] == 1 else ""}> '
            f'{k} {r["n"]} <code>{json.dumps(r["params"])}</code>'
            f'<audio controls preload="none" src="{r["alone"]}"></audio>'
            + (f'<audio controls preload="none" src="{r["context"]}"></audio>' if r.get("context") else "")
            + "</label>" for r in rows if r["kind"] == k)
        blocks.append(f"<fieldset><legend>{k}</legend>{items}</fieldset>")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sound lab</title><style>
:root{{--bg:#0b0e12;--ink:#e6ebf0;--muted:#8c97a4;--line:#232b34;--accent:#8fd3ff}}
@media (prefers-color-scheme:light){{:root{{--bg:#f5f6f7;--ink:#151a20;--muted:#5b6672;--line:#dde2e7;--accent:#0a6fa8}}}}
body{{margin:0;padding:24px 16px;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif;max-width:900px;margin-inline:auto}}
fieldset{{border:1px solid var(--line);border-radius:8px;margin:16px 0;padding:8px 16px}}legend{{padding:0 8px;color:var(--muted)}}
.c{{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:6px 0}}code{{color:var(--muted);font-size:12px}}audio{{height:32px}}
button{{font:inherit;padding:6px 14px;border-radius:6px;border:1px solid var(--accent);background:none;color:var(--accent);cursor:pointer}}
pre{{background:none;border:1px solid var(--line);padding:12px;border-radius:8px;white-space:pre-wrap}}
</style></head><body><h1>Sound lab</h1>
<p>Each candidate plays alone, then (when the narration exists) in the pause after the first sentence. Pick one per type.</p>
{''.join(blocks)}<button id="copy" type="button">Copy choices</button><pre id="out" hidden></pre>
<script>
document.getElementById('copy').addEventListener('click',()=>{{
  const pick={{}};document.querySelectorAll('input[type=radio]:checked').forEach(r=>pick[r.name]=+r.value);
  const text=JSON.stringify(pick);const out=document.getElementById('out');out.textContent=text;out.hidden=false;
  if(navigator.clipboard)navigator.clipboard.writeText(text).catch(()=>{{}});
}});
</script></body></html>
"""


def main_lab(args):
    print(lab(args.video))
    return 0
