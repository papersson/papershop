"""The soundtrack, in four stages, and its finish.

  sources  each timeline.tracks.audio entry as a file. The effects are rendered here, from
           audio/sfx.json against the current timeline (sfx.rendered), so a re-narration moves
           them with their cues; the narration is its lossless wav when there is one.
  chain    per entry: trimmed, faded at each cut, the role's own processing (ROLE_CHAIN), its gain,
           delayed to its start.
  bus      the chains summed at unity (amix normalize=0), padded or cut to the video's length.
  master   the finish, on the whole mix (`studio audio VIDEO`, run by publish and export):
    - resampled to 48 kHz with soxr;
    - one fixed gain, measured over the whole mix, to the target integrated loudness (default
      -16 LUFS), so the level moves and the dynamics don't;
    - a limiter that touches only samples above the true-peak ceiling (default -1.5 dBTP), run
      until the measured true peak is under it;
    - no room tone and no one-pass loudnorm: that filter is dynamic, so it raised the room tone and
      the breaths in every pause, and the learner heard "a constant background noise".
  Fixed gain alone pushed the raw voice to about +6.5 dBTP on a few samples; the limiter is for
  those, and for an effect or a music hit over the voice. The master is audio/final.wav; what it was
  finished from and to (target, measured loudness and true peak, gain, a stamp of the inputs) is
  audio/final.json. A draft mixes the finished master while its inputs are unchanged, else the
  unfinished bus.
"""
import hashlib
import json
import re
from pathlib import Path

from . import proc
from . import timeline as tl
from .workspace import atomic_json

RATE = 48_000
# A sparse mix (a quiet bed under one loud hit) took six passes: its integrated loudness is set by
# which blocks pass ebur128's relative gate, so it jumps as the limiter flattens the hit.
MAX_PASSES = 8
OFF_TARGET = 0.5         # LU from the target past which a finish is reported as failed
SILENCE = -70.0          # LUFS: ebur128's absolute gate; a mix this quiet has nothing to finish


def measure(path):
    """(integrated LUFS, true peak dBTP) of an audio file, from ffmpeg's ebur128."""
    run = proc.run([proc.tool("ffmpeg"), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
                    "-f", "null", "-"], capture_output=True, text=True)
    text = run.stderr.split("Summary:")[-1]
    lufs = re.search(r"I:\s+(-?[\d.]+) LUFS", text)
    peak = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", text)
    if not lufs or not peak:
        raise RuntimeError(f"could not measure {path}: {run.stderr[-300:]}")
    return float(lufs.group(1)), float(peak.group(1))


# --- stage 1: sources -----------------------------------------------------------------------------

def sources(video, timeline):
    """[(entry, file)] for every tracks.audio entry whose file exists."""
    video = Path(video)
    out = []
    for e in timeline["tracks"]["audio"]:
        f = video / e["file"]
        if e["file"] == tl.SFX["file"] and (video / "audio" / "sfx.json").exists():
            from . import sfx
            f = sfx.rendered(video, timeline)
        elif tl.audio_role(e) == "narration" and f.suffix == ".mp3" and f.with_suffix(".wav").exists():
            f = f.with_suffix(".wav")           # narrate writes both; the mp3 is the wav, lossy
        if f.exists():
            out.append((e, f))
    return out


def inputs(timeline, files):
    """A stamp of everything the bus is made from: the entries, the length, each file's size and time."""
    h = hashlib.sha1(json.dumps([timeline["tracks"]["audio"], timeline["duration"]], sort_keys=True).encode())
    for _, f in files:
        st = f.stat()
        h.update(f"{f.name}:{st.st_size}:{st.st_mtime_ns}".encode())
    return h.hexdigest()[:16]


# --- stage 2: each entry's chain ------------------------------------------------------------------

# Each role's own filters, after the trim and fades and before the gain: where effects and music will
# get their presence-band cut under speech. Ducking needs the narration as its key, so it belongs
# in the bus.
ROLE_CHAIN = {"narration": [], "sfx": [], "music": [], "footage": []}


def chain(e):
    """The filters one entry goes through before the bus."""
    out = []
    if e.get("in") is not None or e.get("out") is not None:
        out.append(f"atrim=start={e.get('in', 0)}" + (f":end={e['out']}" if e.get("out") is not None else ""))
        out.append("asetpts=PTS-STARTPTS")
    if e.get("fade") and e.get("out") is not None:       # a short fade at every cut, so a cut never clicks
        d = e["out"] - e.get("in", 0)
        out.append(f"afade=t=in:d={e['fade']}")
        out.append(f"afade=t=out:st={max(0, d - e['fade']):.3f}:d={e['fade']}")
    out += ROLE_CHAIN.get(tl.audio_role(e), [])
    if e.get("gain"):
        out.append(f"volume={e['gain']}dB")
    if e.get("start"):
        ms = round(e["start"] * 1000)
        out.append(f"adelay={ms}|{ms}")
    return out


# --- stage 3: the bus -----------------------------------------------------------------------------

def mix(video, timeline, out, files=None):
    """Stages 1 to 3: the sources, each through its chain, summed into `out`, `duration` seconds long.
    A .m4a is AAC; anything else is 32-bit float, so a sum over full scale reaches the master intact."""
    video = Path(video)
    dur = timeline["duration"]
    files = sources(video, timeline) if files is None else files
    codec = ["-c:a", "aac", "-b:a", "160k"] if Path(out).suffix == ".m4a" else ["-c:a", "pcm_f32le"]
    if not files:      # a silent video (a motion piece before its music, estimated timings): silence, not a failure
        proc.ffmpeg("-f", "lavfi", "-i", f"anullsrc=r={RATE}:cl=stereo", "-t", f"{dur:.3f}", *codec, out)
        return
    cmd, filters = [], []
    for i, (e, f) in enumerate(files):
        cmd += ["-i", str(f)]
        filters.append(f"[{i}:a]{','.join(chain(e)) or 'anull'}[a{i}]")
    join = "".join(f"[a{i}]" for i in range(len(files)))
    filters.append(f"{join}amix=inputs={len(files)}:normalize=0:duration=longest,apad=whole_dur={dur:.3f},atrim=end={dur:.3f}[m]")
    proc.ffmpeg(*cmd, "-filter_complex", ";".join(filters), "-map", "[m]", *codec, out)


# --- stage 4: the master --------------------------------------------------------------------------

def master(src, out, lufs=-16.0, peak=-1.5, measured=None):
    """Finish `src` into `out` (48 kHz, 24-bit): the fixed gain and the iterated limiter. `measured`
    is src's (LUFS, true peak) when the caller has it."""
    before, before_tp = measured or measure(src)
    gain = lufs - before
    ceiling = peak
    for _ in range(MAX_PASSES):
        limit = 10 ** (ceiling / 20)
        proc.ffmpeg("-i", src, "-af",
                    f"aresample={RATE}:resampler=soxr:precision=28,volume={gain:.3f}dB,"
                    f"alimiter=limit={limit:.4f}:attack=5:release=50:level=disabled",
                    "-c:a", "pcm_s24le", out)
        got, tp = measure(out)
        settled = abs(got - lufs) <= 0.3 and tp <= peak + 0.05
        if settled:
            break
        # The limiter removes energy from the peaks, so the loudness lands under the target; aim the
        # gain again, and lower the limit when the true peak overshoots the sample-peak limit.
        gain += lufs - got
        if tp > peak + 0.05:
            ceiling -= (tp - peak) + 0.05
    return {"target_lufs": lufs, "lufs": got, "true_peak_dbtp": tp, "ceiling_dbtp": peak,
            "gain_db": round(gain, 2), "input_lufs": before, "input_true_peak_dbtp": before_tp}


def _record(video):
    p = Path(video) / "audio" / "final.json"
    return json.loads(p.read_text()) if p.exists() and (Path(video) / "audio" / "final.wav").exists() else None


def finish(video, lufs=-16.0, peak=-1.5, timeline=None):
    """Mix the timeline's sound and finish it into audio/final.wav; returns the record, or None for
    a silent mix. Kept as it is when it was finished from these inputs to these targets (a
    re-publish after a picture-only change)."""
    video = Path(video)
    timeline = timeline or tl.load(video)
    files = sources(video, timeline)
    stamp_in = inputs(timeline, files)
    stamp = f"{stamp_in}:{lufs}:{peak}"
    done = _record(video)
    if done and done.get("stamp") == stamp:
        print("audio finish: unchanged mix, kept")
        return done
    if not files:
        print("audio finish: the soundtrack is silent, nothing to finish")
        return None
    bus = video / ".cache" / "sound" / f"bus-{stamp_in}.wav"
    bus.parent.mkdir(parents=True, exist_ok=True)
    mix(video, timeline, bus, files)
    measured = measure(bus)
    if measured[0] <= SILENCE:
        bus.unlink()
        print("audio finish: the soundtrack is silent, nothing to finish")
        return None
    result = {**master(bus, video / "audio" / "final.wav", lufs, peak, measured),
              "source": "mix", "inputs": stamp_in, "stamp": stamp}
    bus.unlink()
    atomic_json(video / "audio" / "final.json", result)
    if missed(result):
        print(f"warn: the finish landed at {result['lufs']:.1f} LUFS, not {lufs}: the mix is too sparse "
              "or too peaky to reach it under the ceiling")
    return result


def missed(r):
    """Whether a finish missed its loudness target or its true-peak ceiling."""
    return abs(r["lufs"] - r["target_lufs"]) > OFF_TARGET or r["true_peak_dbtp"] > r["ceiling_dbtp"] + 0.1


def encode(src, out, ceiling, *args):
    """src's sound as AAC with `args` (bitrate, rate, channels), under the true-peak `ceiling` (None:
    unchecked). A lossy encode overshoots the peak it was given, by 0.1 dB at 160 kbps and up to
    1.5 dB at the web copy's 28 to 64 kbps mono (measured), so the encode is measured and, when over,
    made again that much quieter."""
    trim = 0.0
    for _ in range(MAX_PASSES):
        proc.ffmpeg("-i", src, "-vn", *(["-af", f"volume={-trim:.2f}dB"] if trim else []), "-c:a", "aac", *args, out)
        over = measure(out)[1] - ceiling if ceiling is not None else 0
        if over <= 0:
            return
        trim += over + 0.05
    raise RuntimeError(f"could not encode {out} under {ceiling} dBTP")


def soundtrack(video, timeline):
    """The video's sound as AAC, cached under .cache/sound/ by its inputs, so a cut that changed only
    pictures doesn't re-mix it: the finished master while audio/final.json was finished from these
    very inputs (at whatever target), else the unfinished bus, as a draft hears it."""
    video = Path(video)
    files = sources(video, timeline)
    stamp_in = inputs(timeline, files)
    done = _record(video)
    finished = bool(done and done.get("inputs") == stamp_in)
    cache = video / ".cache" / "sound"
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / f"{hashlib.sha1((done['stamp'] if finished else stamp_in).encode()).hexdigest()[:16]}.m4a"
    if f.exists():
        print("soundtrack: unchanged, cached", flush=True)
        return f
    for old in cache.glob("*.m4a"):
        old.unlink()
    if finished:
        encode(video / "audio" / "final.wav", f, done["ceiling_dbtp"], "-b:a", "160k")
    else:
        mix(video, timeline, f, files)
    return f


def main(args):
    r = finish(args.video, args.lufs, args.peak, tl.build(args.video))
    if r is None:
        return 0
    print(f"audio/final.wav (the whole mix): {r['lufs']:.1f} LUFS (target {r['target_lufs']}), true peak "
          f"{r['true_peak_dbtp']:.1f} dBTP (ceiling {r['ceiling_dbtp']}); fixed gain {r['gain_db']:+.1f} dB from "
          f"{r['input_lufs']:.1f} LUFS, input peak {r['input_true_peak_dbtp']:.1f} dBTP")
    return 1 if missed(r) else 0
