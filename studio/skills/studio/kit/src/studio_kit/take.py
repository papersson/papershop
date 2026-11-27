"""`studio take FILE`: clean a recorded voice take and say how it measures, before and after.

A take from a phone or a USB mic comes in at any level, with rumble under it, room hiss between the
words and silence at both ends. This runs one fixed chain on it, the same each time, so two takes
recorded on different days sound like one voice (after Kit Langton's effect.institute, whose
recordings go through the same steps):

  mono, 48 kHz          one channel at studio's rate
  high-pass 80 Hz       the rumble under a voice (desk, traffic, the mic stand), not the voice
  level                 one fixed gain to near -16 LUFS, so the steps below see the same level
  light denoise         afftdn at 10 dB: hiss between words; more than this makes the voice watery
  trim the ends         the silence before the first word and after the last
  gentle gate           the room between words 10 dB down, never cut to nothing (a hard gate pumps)
  gentle compressor     2.5:1 above -20 dB, so loud words and quiet words sit closer together
  de-esser              softens the hiss of s and sh, which the compressor brings forward
  -16 LUFS, -1.5 dBTP   the loudness the rest of studio's narration has, in two passes

Then it reports loudness, peak, the noise floor and how far the voice stands above it, in and out, and says what to change
at the mic when the take itself is the problem: too quiet (get closer), clipped (back off), or a
noisy room (no chain fixes that). `--text SCRIPT` also transcribes the cleaned take and scores it
against what should have been read, and writes the word timings beside it (OUT.words.json), the
first step to a film narrated in a recorded voice. The recogniser is faster-whisper (the `align`
extra), whose model downloads from Hugging Face on first use.
"""
import json
import re
from array import array
from math import log10
from pathlib import Path

from . import proc
from .audio import RATE

TARGET = -16.0           # LUFS, studio's narration level
PEAK = -1.5              # dBTP
QUIET_IN = -35.0         # LUFS: a take this quiet was recorded too far from the mic
CLIPPED_IN = -0.1        # dBFS sample peak: the take clipped
ROOM = 40.0              # dB the voice should stand above the room in the take (45-50 is a good booth)
WINDOW = 0.05            # seconds per window for the noise floor

def chain(gain):
    """The filters, after a fixed GAIN (dB) that brings the take near the target first, so the
    silence trim and the compressor see the same level whatever the take came in at."""
    return ",".join([
    "aformat=channel_layouts=mono",
    f"aresample={RATE}",
    "highpass=f=80",
    f"volume={gain:.2f}dB",
    "afftdn=nr=10:nf=-50",
    # silenceremove trims the start; the same filter on the reversed take trims the end.
    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.25",
    "areverse",
    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.4",
    "areverse",
    # A gentle gate (10 dB down, never off) between words, before the compressor lifts the room.
    "agate=threshold=0.01:range=0.3:attack=5:release=250",
    "acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150:makeup=1",
    "deesser=i=0.4",
    ])


def samples(path):
    """The take as mono floats at studio's rate, decoded by ffmpeg."""
    raw = proc.run([proc.tool("ffmpeg"), "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(RATE),
                    "-f", "f32le", "-"], capture_output=True).stdout
    return array("f", raw[:len(raw) // 4 * 4])


def measure(path):
    """{lufs, peak (true peak dBTP), sample_peak (dBFS), floor (dBFS), seconds} of an audio file.
    The floor is the level of the quietest tenth of 50 ms windows: the room between the words."""
    run = proc.run([proc.tool("ffmpeg"), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
                    "-f", "null", "-"], capture_output=True, text=True)
    text = run.stderr.split("Summary:")[-1]
    lufs = re.search(r"I:\s+(-?[\d.]+) LUFS", text)
    peak = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", text)
    x = samples(path)
    n = int(RATE * WINDOW)
    db = lambda v: 20 * log10(v) if v > 1e-9 else -120.0
    rms = sorted((sum(s * s for s in x[i:i + n]) / n) ** 0.5 for i in range(0, len(x) - n + 1, n))
    quiet = rms[:max(1, len(rms) // 10)] if rms else [0.0]
    return {"lufs": float(lufs.group(1)) if lufs else -70.0,
            "peak": float(peak.group(1)) if peak and peak.group(1) != "-inf" else -120.0,
            "sample_peak": db(max((abs(s) for s in x), default=0.0)),
            "floor": db(sum(quiet) / len(quiet)), "seconds": len(x) / RATE}


def loudnorm(gain):
    return f"{chain(gain)},loudnorm=I={TARGET}:TP={PEAK}:LRA=11"


def clean(src, out, lufs):
    """Run the chain into OUT (24-bit WAV), with loudnorm's measured two-pass so the level is exact.
    LUFS is the take's own loudness, measured before."""
    gain = TARGET - lufs
    first = proc.run([proc.tool("ffmpeg"), "-hide_banner", "-nostats", "-i", str(src), "-af",
                      loudnorm(gain) + ":print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(first.stderr[first.stderr.rindex("{"):first.stderr.rindex("}") + 1])
    if m["input_i"] in ("-inf", "inf"):
        raise ValueError("nothing is left after trimming the silence")
    second = loudnorm(gain) + (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
                                f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    proc.ffmpeg("-i", src, "-af", second + f",aresample={RATE}", "-ar", RATE, "-ac", 1, "-c:a", "pcm_s24le",
                "-map_metadata", "-1", "-fflags", "+bitexact", out)


def advice(before, after):
    """What to change at the mic, one line each; empty when the take is fine."""
    notes = []
    if before["lufs"] < QUIET_IN:
        notes.append(f"recorded quiet ({before['lufs']:.0f} LUFS): get closer to the mic, a hand's width away, "
                     "rather than turning the gain up afterwards")
    if before["sample_peak"] >= CLIPPED_IN:
        notes.append("the take clipped: back off a little, or turn the input gain down")
    if before["lufs"] - before["floor"] < ROOM:
        notes.append(f"the room is loud between words (the voice is {before['lufs'] - before['floor']:.0f} dB above it, "
                     f"aim for {ROOM:.0f} or more): a closet, a duvet over the head, or closer to the mic")
    return notes


def spoken_text(text):
    """What was to be read: a script's `> ` quoted lines when it has any (a reading script with notes
    around it), otherwise all of it."""
    quoted = [line[1:].strip() for line in text.splitlines() if line.startswith(">")]
    return "\n".join(quoted) if any(quoted) else text


def row(name, m):
    return (f"{name:<6}{m['lufs']:6.1f} LUFS  peak {m['peak']:5.1f} dBTP  floor {m['floor']:6.1f} dBFS  "
            f"voice {m['lufs'] - m['floor']:4.1f} dB above the room  {m['seconds']:5.1f} s")


def main(args):
    src = Path(args.file)
    if not src.is_file():
        raise SystemExit(f"no take at {src}")
    out = Path(args.out) if args.out else src.with_name(src.stem + ".clean.wav")
    if out.resolve() == src.resolve():
        raise SystemExit("--out is the take itself: name another file")
    before = measure(src)
    if before["lufs"] <= -70:
        raise SystemExit(f"{src} is silent: check the mic was the input it recorded from")
    try:
        clean(src, out, before["lufs"])
    except (proc.CalledProcessError, ValueError) as e:
        raise SystemExit(f"could not clean {src}: {getattr(e, 'stderr', '') or e}")
    after = measure(out)
    print(row("in", before))
    print(row("out", after))
    for note in advice(before, after):
        print(f"  {note}")
    print(f"wrote {out}")
    if args.text:
        from .align import recognise
        from .voice_check import score
        expected = spoken_text(Path(args.text).read_text())
        words = recognise(out, args.model)
        heard = " ".join(w["w"] for w in words)
        words_file = out.with_name(out.name.removesuffix(".wav") + ".words.json")
        words_file.write_text(json.dumps({"take": out.name, "words": words}, indent=1) + "\n")
        print(f"read {score(expected, heard):.2f} of the script as written ({len(words)} words); timings in {words_file}")
    return 0
