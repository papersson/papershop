import json
import subprocess

from studio_kit import assets, check, motion, render
from test_render import make_video


class Frames:
    def __init__(self, frames):
        self.frames = frames

    def boxes_at(self, requests):
        return [{**r, **f} for r, f in zip(requests, self.frames)]


def test_legible_flags_text_under_18_px_only(tmp_path):
    make_video(tmp_path)
    frames = [{"band": {}, "boxes": [{"name": "tiny label", "kind": "text", "x": 0, "y": 0, "w": 90, "h": 14},
                                     {"name": "big", "kind": "text", "x": 0, "y": 0, "w": 90, "h": 26},
                                     {"name": "a box", "kind": "", "x": 0, "y": 0, "w": 90, "h": 4}]}]
    lay = {"width": 1920, "height": 1080, "band": {"height": 160}}
    rows = motion.legible(tmp_path, boxes=(lay, [{"clip": "s1", "t": 1.0, **frames[0]}]))
    assert not rows[0]["ok"] and "tiny label" in rows[0]["detail"] and "big" not in rows[0]["detail"]


def test_at_global_maps_timeline_seconds_to_clip_time(tmp_path):
    t = make_video(tmp_path)
    assert motion.at_global(t, 0.5) == ("s1", 0.5) and motion.at_global(t, 2.5) == ("s2", 0.5)
    assert motion.at_global(t, 99)[0] == "s2"


def test_provenance_finds_assets_scenes_use_without_a_row(tmp_path):
    make_video(tmp_path)
    (tmp_path / "scenes" / "s1.tsx").write_text('<Shot file="ui.png" at={[0,0]} /> staticFile(\'logo.svg\')')
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "ui.png").write_bytes(b"x")
    assets.record(tmp_path, "ui.png", "capture", "https://example.com")
    rows = motion.provenance(tmp_path)
    assert not rows[0]["ok"] and "logo.svg" in rows[0]["detail"] and "ui.png" not in rows[0]["detail"].split(";")[0]
    (tmp_path / "assets" / "logo.svg").write_bytes(b"x")
    assets.record(tmp_path, "logo.svg", "supplied", "brand kit")
    assert motion.provenance(tmp_path)[0]["ok"]


def test_pixel_and_motion_videos_get_their_extra_checks_by_default(tmp_path):
    make_video(tmp_path)
    (tmp_path / "video.json").write_text(json.dumps({"genre": "motion", "loop": True}))
    assert check.genre(tmp_path) == "motion" and check.config(tmp_path)["loop"]


def stage(a, b, d=2):
    """Two boxes landing at a and b seconds; a dot blinking on the stage (ambient) and a bar blinking in
    the caption band (not the stage) all along."""
    box = "drawbox=y=100:w=400:h=300:color=white:t=fill"
    return (f"color=c=black:s=1920x1080:r=30:d={d},{box}:x=100:enable='gte(t,{a})',{box}:x=900:enable='gte(t,{b})',"
            "drawbox=x=50:y=700:w=12:h=12:color=white:t=fill:enable='lt(mod(t,0.2),0.1)',"
            "drawbox=x=0:y=950:w=1920:h=100:color=white:t=fill:enable='lt(mod(t,0.2),0.1)'")


class StageEngine:
    """Renders each still from a clip's lavfi graph, at its own time."""
    def __init__(self, graphs):
        self.graphs, self.asked = graphs, 0

    def stills(self, requests):
        self.asked += len(requests)
        for r in requests:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", self.graphs[r["clip"]], "-ss", str(r["t"]),
                            "-frames:v", "1", r["out"]], check=True)


def test_moves_are_runs_of_change_big_enough_to_read():
    sig = [(0.05, 0.0), (0.15, 0.5), (0.25, 0.4), (0.35, 0.05), (0.45, 0.13), (0.55, 0.0), (0.65, 3.0), (0.75, 0.11)]
    assert motion.moves(sig) == [(0.1, 0.3, 0.9), (0.6, 0.7, 3.0)]      # 0.13 alone is ambient, 0.11 under the level
    quiet = [(round(0.05 + i / 10, 2), 0.0) for i in range(10)]
    assert motion.moves([(0.05, 0.3), (0.15, 0.3), (0.25, 0.3)] + quiet[3:]) == [(0.0, 0.3, 0.9)]


def at(values, links=None):
    return [(round(0.05 + i / 10, 2), v, 1.0 if links is None else links[i]) for i, v in enumerate(values)]


def test_back_to_back_moves_split_with_no_hold_between_them():
    """A move ending as the next begins leaves no quiet sample: the run splits where the change moves to
    other pixels, or where it dips between two peaks, and the hold between them is 0 s."""
    pad = [0.0] * 8
    elsewhere = at(pad + [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0] + pad, [1.0] * 12 + [0.0] + [1.0] * 11)
    assert motion.moves(elsewhere) == [(0.8, 1.2, 4.0), (1.2, 1.6, 4.0)]
    in_place = at(pad + [0.3, 0.9, 0.6, 0.15, 0.5, 0.9, 0.4] + pad)           # two eased moves of one box
    assert motion.moves(in_place) == [(0.8, 1.2, 1.95), (1.2, 1.5, 1.8)]
    one = at(pad + [0.2, 0.6, 1.0, 0.7, 0.5, 0.6, 0.3] + pad)                  # a bump is not a dip
    assert len(motion.moves(one)) == 1


def test_ambient_motion_does_not_join_the_moves():
    """A wobble that never stops changes about 0.15 grey levels a sample; the moves stand out over it."""
    wobble = [0.15 + 0.05 * ((i * 7) % 3 - 1) for i in range(60)]
    for i, v in zip(range(10, 14), (0.6, 1.2, 0.9, 0.3)):
        wobble[i] += v
    for i, v in zip(range(30, 34), (0.6, 1.2, 0.9, 0.3)):
        wobble[i] += v
    found = motion.moves(at(wobble))
    assert [(a, b) for a, b, _ in found] == [(1.0, 1.4), (3.0, 3.4)]


def test_pacing_reads_the_cuts_clips_and_warns_at_a_short_hold(tmp_path):
    t = make_video(tmp_path)
    (tmp_path / "video.json").write_text(json.dumps({"engine": "remotion"}))
    cache = tmp_path / ".cache" / "clips"
    cache.mkdir(parents=True)
    for cid, (a, b) in {"s1": (0.5, 0.8), "s2": (0.5, 1.2)}.items():
        f = cache / f"{cid}-draft-{render.clip_key(tmp_path, t, cid, 'draft')}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", stage(a, b), "-pix_fmt", "yuv420p", str(f)], check=True)
    eng = StageEngine({})
    rows = motion.pacing(tmp_path, eng)
    assert eng.asked == 0                                       # no stills: the rendered clips are the frames
    (warn,), (ok,) = [r for r in rows if r["clip"] == "s1"], [r for r in rows if r["clip"] == "s2"]
    assert warn["severity"] == "warning" and warn["ok"] and warn["t"] == 0.5
    assert warn["detail"].startswith("0.2 s hold between the move at 0.4-0.5 s and the one at 0.7 s")
    assert ok["detail"] == "2 significant moves, each held at least 0.5 s"
    (tmp_path / "scenes" / "s2.tsx").write_text("// s2, edited: its rendered clip is stale\n")
    assert [r.get("skipped") for r in motion.pacing(tmp_path, eng, stills=False)] == [None, True]


def test_pacing_samples_stills_where_no_clip_is_rendered(tmp_path):
    make_video(tmp_path)
    eng = StageEngine({"s1": stage(0.5, 0.8), "s2": stage(0.5, 1.2)})
    rows = motion.pacing(tmp_path, eng, clips={"s1"})
    assert eng.asked == 20 and [r.get("severity") for r in rows] == ["warning"]    # 2 s at 10 a second
    assert rows[0]["detail"].startswith("0.2 s hold")


def test_two_boxes_landing_on_consecutive_samples_are_two_moves(tmp_path):
    """Measured on rendered frames: box B lands the sample after box A, elsewhere on the stage."""
    t = make_video(tmp_path)
    f = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", stage(0.5, 0.6), "-pix_fmt", "yuv420p", str(f)], check=True)
    signal = motion.file_signal(f, t, {"width": 1920, "height": 1080, "band": {"height": 160}}, 0, 60)
    assert [(a, b) for a, b, _ in motion.moves(signal)] == [(0.4, 0.5), (0.5, 0.6)]


LAY = {"width": 1920, "height": 1080, "band": {"height": 160}}


def old_signal(path, fps, first, count, seek=True):
    """The pacing signal as the kit measured it before frame_signal shared its decoder, written out
    whole: the reference the pacing check and the motion review must still match."""
    step, crop = max(1, round(fps / 10)), 92
    seek = ["-ss", f"{max(0.0, (first - 0.5) / fps):.4f}", "-t", f"{count / fps:.4f}"] if seek else []
    raw = subprocess.run(["ffmpeg", "-v", "error", *seek, "-i", str(path), "-vf",
                          f"fps={fps / step:g},scale=192:108,crop=192:{crop}:0:0,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    times = [k / fps for k in range(0, count, step)]
    frames = [raw[i:i + 192 * crop] for i in range(0, len(raw), 192 * crop)][:len(times)]
    out, before = [], frozenset()
    for a, b, x, y in zip(times, times[1:], frames, frames[1:]):
        diff = list(map(abs, map(int.__sub__, x, y)))
        mask = frozenset(i for i, v in enumerate(diff) if v > 8)
        link = len(mask & before) / min(len(mask), len(before)) if mask and before else 1.0
        out.append((round((a + b) / 2, 3), sum(diff) / (192 * crop), round(link, 3)))
        before = mask
    return out


def test_the_pacing_check_and_the_motion_review_measure_what_they_did(tmp_path):
    """Both read the sampled signal (pacing_signal from a clip render, file_signal from a cut's video
    or clip, at any frame), which now shares its decoder and change measure with frame_signal."""
    t = make_video(tmp_path)
    cache = tmp_path / ".cache" / "clips"
    cache.mkdir(parents=True)
    f = cache / f"s1-draft-{render.clip_key(tmp_path, t, 's1', 'draft')}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", stage(0.5, 0.8, 4), "-pix_fmt", "yuv420p", str(f)], check=True)
    for first, count in ((0, 60), (7, 60), (31, 80)):
        assert [s[:3] for s in motion.file_signal(f, t, LAY, first, count)] == old_signal(f, 30, first, count)
    (tmp_path / "video.json").write_text(json.dumps({"engine": "remotion"}))
    got = motion.pacing_signal(tmp_path, StageEngine({}), clips={"s1"}, stills=False)["s1"]
    assert [s[:3] for s in got] == old_signal(f, 30, 0, 60, seek=False) and len(got) == 19


def gray_clip(path, frames, w=384, h=216, fps=30):
    """A clip of raw grey frames (bytes of w*h each), losslessly encoded."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-r", str(fps),
                    "-i", "-", "-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p", str(path)],
                   input=b"".join(frames), check=True)


def picture(w=384, h=216):
    """90 frames above the caption band: a box easing right over frames 10-20 (fastest into 15), a cut
    to a grey stage at 45, and a panel over half the stage fading in over frames 60-65."""
    def frame(bg, boxes):
        rows = [bytearray([bg]) * w for _ in range(h)]
        for x, y, bw, bh, v in boxes:
            for r in rows[y:y + bh]:
                r[x:x + bw] = bytes([v]) * bw
        return bytes(b"".join(rows))
    speeds = [4, 8, 12, 16, 20, 24, 20, 16, 12, 8, 4]
    x = [20] * 10 + [20 + sum(speeds[:k + 1]) for k in range(11)]
    out = [frame(0, [(p, 40, 40, 40, 255)]) for p in x] + [frame(0, [(x[-1], 40, 40, 40, 255)])] * 24
    out += [frame(128, [(300, 100, 40, 40, 255)])] * 15
    out += [frame(128, [(300, 100, 40, 40, 255), (0, 0, 200, 184, 128 + 20 * k)]) for k in range(1, 7)]
    return out + [out[-1]] * 24


def test_the_frame_signal_starts_on_the_frame_asked_for(tmp_path):
    """Half a frame early, a seek lands on frame `first` itself: a window reads what the whole file does
    (but the link of its first change, which has no change before it in the window)."""
    f = tmp_path / "p.mp4"
    gray_clip(f, picture())
    whole = motion.frame_signal(f, LAY, 30, 0, 90)
    assert [r[0] for r in whole] == list(range(1, 90))
    unlinked = lambda s: [(frame, change, share) for frame, change, _, share in s]
    for first in (9, 14, 44, 59):
        assert unlinked(motion.frame_signal(f, LAY, 30, first, 12)) == unlinked(whole[first:first + 11])


def test_the_frame_signal_reads_a_cut_with_sound_from_any_frame(tmp_path):
    """A cut's video.mp4 carries its sound: the raw muxer's default frame-rate mode then duplicated the
    first frame after a seek in two seek positions of three, so a box appearing on frame 46 read as 47."""
    f = tmp_path / "with-sound.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=640x360:r=30:d=3,"
                    "drawbox=x=100:y=60:w=160:h=120:color=white:t=fill:enable=gte(n\\,46)", "-f", "lavfi", "-i", "sine=d=3",
                    "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", str(f)], check=True)
    for first in range(36, 46):
        assert max(motion.frame_signal(f, LAY, 30, first, 12), key=lambda r: r[1])[0] == 46, first


def test_the_frame_signal_names_where_motion_starts_peaks_ends_and_cuts(tmp_path):
    f = tmp_path / "p.mp4"
    gray_clip(f, picture())
    s = motion.frame_signal(f, LAY, 30, 0, 90)
    assert motion.starts(s, 30) == [10, 60] and motion.ends(s, 30) == [20, 65]
    assert motion.cuts(s) == [45] and motion.is_cut(s, 45) and not motion.is_cut(s, 60)
    assert 45 not in motion.moving(s, 30)                   # a cut is not motion
    assert max(r[3] for r in s if r[0] != 45) < 0.6 < s[44][3]    # the fade over half the stage is no cut
    assert motion.peak(motion.frame_signal(f, LAY, 30, 5, 25), 30) == 15
    assert motion.peak(motion.frame_signal(f, LAY, 30, 25, 15), 30) is None
    window = motion.frame_signal(f, LAY, 30, 12, 6)          # motion under way across the whole window
    assert motion.starts(window, 30) == motion.ends(window, 30) == [] and len(motion.moving(window, 30)) == 5
