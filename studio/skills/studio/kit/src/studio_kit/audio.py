"""The audio finish and the mixdown.

`studio audio VIDEO` writes audio/final.wav from audio/narration.wav (else the mp3):
  - resampled to 48 kHz with soxr;
  - one fixed gain, measured over the whole file, to the target integrated loudness (default
    -16 LUFS), so the level moves and the dynamics don't;
  - a limiter that touches only samples above the true-peak ceiling (default -1.5 dBTP), run until
    the measured true peak is under it;
  - no room tone and no one-pass loudnorm: that filter is dynamic, so it raised the room tone and
    the breaths in every pause, and the learner heard "a constant background noise".
Fixed gain alone pushed the raw voice to about +6.5 dBTP on a few samples; the limiter is for those.
The measured loudness and true peak are printed and stored in timeline.json's "audio_finish".

`mix` builds the video's soundtrack from timeline.tracks.audio: each entry {file, start, in, out,
gain} is trimmed, delayed to its start and summed.
"""
import json
import re
import subprocess
from pathlib import Path

from . import timeline as tl

RATE = 48_000
MAX_PASSES = 4


def measure(path):
    """(integrated LUFS, true peak dBTP) of an audio file, from ffmpeg's ebur128."""
    run = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True)
    text = run.stderr.split("Summary:")[-1]
    lufs = re.search(r"I:\s+(-?[\d.]+) LUFS", text)
    peak = re.search(r"Peak:\s+(-?[\d.]+) dBFS", text)
    if not lufs or not peak:
        raise RuntimeError(f"could not measure {path}: {run.stderr[-300:]}")
    return float(lufs.group(1)), float(peak.group(1))


def source(video):
    a = Path(video) / "audio"
    return a / "narration.wav" if (a / "narration.wav").exists() else a / "narration.mp3"


def finish(video, lufs=-16.0, peak=-1.5):
    video = Path(video)
    src = source(video)
    if not src.exists():
        raise SystemExit(f"no narration in {video / 'audio'}: run `studio narrate` first")
    out = video / "audio" / "final.wav"
    before, before_tp = measure(src)
    gain = lufs - before
    ceiling = peak
    for _ in range(MAX_PASSES):
        limit = 10 ** (ceiling / 20)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af",
                        f"aresample={RATE}:resampler=soxr:precision=28,volume={gain:.3f}dB,"
                        f"alimiter=limit={limit:.4f}:attack=5:release=50:level=disabled",
                        "-c:a", "pcm_s24le", str(out)], check=True)
        got, tp = measure(out)
        settled = abs(got - lufs) <= 0.3 and tp <= peak + 0.05
        if settled:
            break
        # The limiter removes energy from the peaks, so the loudness lands under the target; aim the
        # gain again, and lower the limit when the true peak overshoots the sample-peak limit.
        gain += lufs - got
        if tp > peak + 0.05:
            ceiling -= (tp - peak) + 0.05
    result = {"target_lufs": lufs, "lufs": got, "true_peak_dbtp": tp, "ceiling_dbtp": peak,
              "gain_db": round(gain, 2), "source": src.name, "input_lufs": before, "input_true_peak_dbtp": before_tp}
    if (video / "timeline.json").exists():
        t = tl.load(video)
        t["audio_finish"] = result
        tl.save(video, t)
    return result


def pick(video, entry_file):
    """The narration file to mix: the finished one when it is at least as new as its source."""
    video = Path(video)
    final = video / "audio" / "final.wav"
    if final.exists() and (video / entry_file).name.startswith("narration"):
        src = source(video)
        if src.exists() and final.stat().st_mtime >= src.stat().st_mtime:
            return final
    return video / entry_file


def mix(video, timeline, out):
    """Mix timeline.tracks.audio into one AAC file `out`, `duration` seconds long."""
    video = Path(video)
    dur = timeline["duration"]
    entries = [e for e in timeline["tracks"]["audio"] if pick(video, e["file"]).exists()]
    if not entries:      # a silent video (a motion piece before its music, estimated timings): silence, not a failure
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"anullsrc=r={RATE}:cl=stereo", "-t", f"{dur:.3f}",
                        "-c:a", "aac", "-b:a", "96k", str(out)], check=True)
        return
    cmd = ["ffmpeg", "-v", "error", "-y"]
    filters = []
    for i, e in enumerate(entries):
        cmd += ["-i", str(pick(video, e["file"]))]
        chain = []
        if e.get("in") is not None or e.get("out") is not None:
            chain.append(f"atrim=start={e.get('in', 0)}" + (f":end={e['out']}" if e.get("out") is not None else ""))
            chain.append("asetpts=PTS-STARTPTS")
        if e.get("fade") and e.get("out") is not None:       # a short fade at every cut, so a cut never clicks
            d = e["out"] - e.get("in", 0)
            chain.append(f"afade=t=in:d={e['fade']}")
            chain.append(f"afade=t=out:st={max(0, d - e['fade']):.3f}:d={e['fade']}")
        if e.get("gain"):
            chain.append(f"volume={e['gain']}dB")
        if e.get("start"):
            ms = round(e["start"] * 1000)
            chain.append(f"adelay={ms}|{ms}")
        filters.append(f"[{i}:a]{','.join(chain) if chain else 'anull'}[a{i}]")
    join = "".join(f"[a{i}]" for i in range(len(entries)))
    filters.append(f"{join}amix=inputs={len(entries)}:normalize=0:duration=longest,apad=whole_dur={dur:.3f},atrim=end={dur:.3f}[m]")
    cmd += ["-filter_complex", ";".join(filters), "-map", "[m]", "-c:a", "aac", "-b:a", "160k", str(out)]
    subprocess.run(cmd, check=True)


def main(args):
    r = finish(args.video, args.lufs, args.peak)
    print(f"audio/final.wav: {r['lufs']:.1f} LUFS (target {r['target_lufs']}), true peak {r['true_peak_dbtp']:.1f} dBTP "
          f"(ceiling {r['ceiling_dbtp']}); fixed gain {r['gain_db']:+.1f} dB from {r['input_lufs']:.1f} LUFS, "
          f"input peak {r['input_true_peak_dbtp']:.1f} dBTP")
    return 0 if r["true_peak_dbtp"] <= r["ceiling_dbtp"] + 0.1 else 1
