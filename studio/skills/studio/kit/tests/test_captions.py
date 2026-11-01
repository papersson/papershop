"""Captions ship as a WebVTT file beside the video, never in its picture, and players keep them off."""
import json
import re
from types import SimpleNamespace

from studio_kit import captions, publish
from studio_kit import timeline as tl
from test_render import make_video


def test_the_caption_file_is_webvtt_with_one_cue_per_chunk():
    t = {"tracks": {"captions": [
        {"start": 0.25, "end": 2.0, "lines": ["Send one key", "with every attempt."]},
        {"start": 3661.5, "end": 3662.004, "lines": ["A <tag> & an arrow --> here."]},
        {"start": 4000.0, "end": 4001.0, "lines": []},                # a blanked span shows nothing
    ]}}
    assert captions.vtt(t) == (
        "WEBVTT\n\n"
        "1\n00:00:00.250 --> 00:00:02.000\nSend one key\nwith every attempt.\n\n"
        "2\n01:01:01.500 --> 01:01:02.004\nA &lt;tag> &amp; an arrow -> here.\n")


def test_a_video_without_narration_gets_no_caption_file(tmp_path):
    out = tmp_path / "out" / "captions.vtt"
    out.parent.mkdir()
    out.write_text("WEBVTT\n\nstale\n")
    assert captions.write({"tracks": {"captions": []}}, out) is None and not out.exists()


def test_studio_captions_writes_the_file_from_the_timeline_without_rendering(tmp_path, monkeypatch):
    make_video(tmp_path)
    monkeypatch.setattr(tl, "build", tl.load)          # make_video writes a built timeline, not its sources
    assert captions.main(SimpleNamespace(video=tmp_path)) == 0
    text = (tmp_path / "out" / "captions.vtt").read_text()
    cues = re.findall(r"^\d\d:\d\d:\d\d\.\d{3} --> \d\d:\d\d:\d\d\.\d{3}$", text, re.M)
    assert text.startswith("WEBVTT\n") and len(cues) == len(tl.load(tmp_path)["tracks"]["captions"]) > 0


def test_the_page_offers_captions_as_a_track_that_starts_off(tmp_path):
    t = make_video(tmp_path)
    page = publish.page_html(t, {"title": "T"}, 3, captions=True)
    track = re.search(r"<track [^>]*>", page).group(0)
    assert 'kind="captions"' in track and 'src="captions.vtt"' in track and "default" not in track
    assert 'id="cc"' in page and 'aria-pressed="false"' in page and "track.mode='hidden'" in page
    page.split("<script>", 1)[1].encode("ascii")
    bare = publish.page_html(t, {"title": "T"}, 3)
    assert "<track" not in bare and 'id="cc"' not in bare


def test_the_desk_shows_captions_only_when_asked():
    from pathlib import Path
    import studio_kit
    desk = (Path(studio_kit.__file__).parent / "page.html").read_text()
    assert 'id="captions" aria-pressed="false"' in desk and "cc = false" in desk
    assert "no-captions" not in desk and "captionMask" not in desk


def test_the_engine_has_no_caption_layer():
    from studio_kit import engine
    assert engine.LAYERS == ("all", "background")
    assert "band" not in tl.DEFAULT_LAYOUT and all("band" not in f for f in tl.FORMATS.values())
    assert json.loads(json.dumps(tl.FORMATS))["9:16"] == {"width": 1080, "height": 1920}
