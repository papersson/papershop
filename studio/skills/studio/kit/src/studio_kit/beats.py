"""`studio beats VIDEO FILE`: a beat grid from a track, so cuts and hits land on the music.

Onset strength from a short-time spectrum (positive change in log-magnitude), the tempo from the
autocorrelation of that curve between 70 and 190 BPM, and the phase from the grid offset that
collects the most onset strength. Writes audio/beats.json, which the timeline carries as "beats":
  bpm, beats (seconds), downbeats (every fourth beat, from the strongest phase of four), hits
(the onset peaks, for effects).
Scenes read them with `useClip().beat(i)` and `useClip().hits`. Numpy only; the `audio` extra.
"""
from pathlib import Path

from . import proc

RATE = 22_050
N_FFT = 1024
HOP = 256
BPM_RANGE = (70, 190)


def load_mono(path):
    import numpy as np
    raw = proc.ffmpeg("-i", path, "-f", "f32le", "-ac", "1", "-ar", RATE, "-", capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def onset_strength(y):
    import numpy as np
    win = np.hanning(N_FFT)
    frames = np.lib.stride_tricks.sliding_window_view(np.pad(y, (N_FFT // 2, N_FFT // 2)), N_FFT)[::HOP]
    mag = np.abs(np.fft.rfft(frames * win, axis=1))
    logm = np.log1p(30 * mag)
    flux = np.maximum(0, np.diff(logm, axis=0)).sum(axis=1)
    return np.concatenate([[0.0], flux])


def analyse(y):
    import numpy as np
    env = onset_strength(y)
    env = env - env.mean()
    fps = RATE / HOP
    lo, hi = int(fps * 60 / BPM_RANGE[1]), int(fps * 60 / BPM_RANGE[0])
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    lag = lo + int(np.argmax(ac[lo:hi]))
    # Refine the period to a fraction of a frame, by parabolic interpolation around the peak.
    a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
    denom = a - 2 * b + c
    period = lag + (0.5 * (a - c) / denom if denom else 0.0)
    bpm = 60 * fps / period
    if bpm < 90 and 2 * bpm <= BPM_RANGE[1]:          # a half-time peak: prefer the pulse people tap
        bpm, period = 2 * bpm, period / 2
    n = len(env)
    best, phase = -1e18, 0.0
    for off in np.arange(0, period, 0.25):
        idx = np.round(np.arange(off, n, period)).astype(int)
        idx = idx[idx < n]
        score = env[idx].sum()
        if score > best:
            best, phase = score, off
    idx = np.round(np.arange(phase, n, period)).astype(int)
    beats = [round(float(i / fps), 3) for i in idx if i < n]
    strengths = [float(env[i]) for i in idx if i < n]
    down = max(range(4), key=lambda k: sum(strengths[k::4])) if len(beats) >= 4 else 0
    thr = env.mean() + 1.5 * env.std()
    peaks = [i for i in range(2, n - 2) if env[i] > thr and env[i] >= env[i - 1] and env[i] > env[i + 1]]
    hits, last = [], -1.0
    for i in peaks:
        t = i / fps
        if t - last >= 0.08:
            hits.append(round(t, 3))
            last = t
    return {"bpm": round(float(bpm), 2), "beats": beats, "downbeats": beats[down::4], "hits": hits}


def main(args):
    from . import timeline as tl
    from .workspace import atomic_json
    video = Path(args.video)
    try:
        result = analyse(load_mono(args.file))
    except ImportError:
        raise SystemExit("beats needs numpy: run `studio doctor --fetch --extra audio`")
    atomic_json(video / "audio" / "beats.json", result)
    if (video / "timeline.json").exists():     # else the first narration or edit builds it with the beats
        tl.build(video)
    print(f"{result['bpm']} BPM, {len(result['beats'])} beats, {len(result['downbeats'])} downbeats, {len(result['hits'])} hits")
    return 0
