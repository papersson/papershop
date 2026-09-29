"""Narration cached per paragraph, so an edited sentence re-synthesises only its paragraph.

A paragraph is the narration sentences that share a clip and a paragraph number: the unit a
voice engine synthesises in one call, so intonation carries across its sentences. Its cache key
hashes the spoken text and the voice settings; audio and sentence spans live under
.cache/narration/<key>.wav and <key>.json.

A synthesiser is any callable (sentences, voice) -> (wav bytes, [(start, end)] per sentence).
The Kokoro and ElevenLabs engines move here from the tutor kit in phase 1; until then
`studio narrate --plan` reports what a re-narration would cost.
"""
import hashlib
import json
from pathlib import Path

from . import timeline as tl

DEFAULT_VOICE = {"engine": "kokoro", "voice": "af_heart", "speed": 1.0}


def voice(video):
    vj = Path(video) / "video.json"
    return (json.loads(vj.read_text()).get("voice") if vj.exists() else None) or DEFAULT_VOICE


def paragraphs(timeline):
    """[{clip, paragraph, ids, sentences}] in narration order."""
    out = []
    for s in timeline["tracks"]["narration"]:
        if not out or (out[-1]["clip"], out[-1]["paragraph"]) != (s["clip"], s["paragraph"]):
            out.append({"clip": s["clip"], "paragraph": s["paragraph"], "ids": [], "sentences": []})
        out[-1]["ids"].append(s["id"])
        out[-1]["sentences"].append(s["text"])
    return out


def paragraph_key(sentences, voice_settings):
    blob = json.dumps({"sentences": sentences, "voice": voice_settings}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


class Cache:
    def __init__(self, video):
        self.dir = Path(video) / ".cache" / "narration"

    def get(self, key):
        wav, meta = self.dir / f"{key}.wav", self.dir / f"{key}.json"
        if wav.exists() and meta.exists():
            return wav.read_bytes(), [tuple(x) for x in json.loads(meta.read_text())["spans"]]
        return None

    def put(self, key, wav, spans):
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / f"{key}.wav").write_bytes(wav)
        (self.dir / f"{key}.json").write_text(json.dumps({"spans": [list(s) for s in spans]}))


def plan(video, timeline=None):
    """[(paragraph, key, cached?)] for the video's current narration and voice."""
    timeline = timeline or tl.load(video)
    v, cache = voice(video), Cache(video)
    rows = []
    for p in paragraphs(timeline):
        key = paragraph_key(p["sentences"], v)
        rows.append((p, key, cache.get(key) is not None))
    return rows


def synthesize(video, synth, timeline=None):
    """Audio and sentence spans for every paragraph, calling `synth` only for cache misses.
    Returns ([(paragraph, wav, spans)], number synthesised)."""
    v, cache = voice(video), Cache(video)
    out, made = [], 0
    for p, key, cached in plan(video, timeline):
        hit = cache.get(key) if cached else None
        if hit is None:
            wav, spans = synth(p["sentences"], v)
            if len(spans) != len(p["sentences"]):
                raise ValueError(f"synthesiser returned {len(spans)} spans for {len(p['sentences'])} sentences")
            cache.put(key, wav, spans)
            hit, made = (wav, spans), made + 1
        out.append((p, *hit))
    return out, made


def main(args):
    rows = plan(args.video)
    misses = [(p, key) for p, key, cached in rows if not cached]
    chars = sum(len(" ".join(p["sentences"])) for p, _ in misses)
    print(f"{len(rows)} paragraphs, {len(rows) - len(misses)} cached, {len(misses)} to synthesise "
          f"({chars} characters) with {voice(args.video)}")
    for p, key in misses:
        print(f"  {p['ids'][0]}..{p['ids'][-1]}  {key}")
    if not args.plan:
        raise SystemExit("synthesis engines join the kit in phase 1; run with --plan")
    return 0
