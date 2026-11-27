"""`studio take`: a recorded take comes out at studio's level, trimmed, with advice when the take is the problem."""
import subprocess
from types import SimpleNamespace

import pytest

from studio_kit import take


def recorded(path, gain_db, seconds=6, hum=True):
    """A take stand-in: speech-like bursts with a second of silence at each end, 50 Hz rumble under it."""
    from test_audio import speech
    speech(path.with_name("voice.wav"), seconds=seconds - 2)
    filters = [f"[0]adelay=1000,apad=pad_dur=1,volume={gain_db}dB" + ("[v]" if hum else "")]
    inputs = ["-i", str(path.with_name("voice.wav"))]
    if hum:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency=50:duration={seconds}:sample_rate=48000"]
        filters.append(f"[1]volume={gain_db - 20}dB[h];[v][h]amix=inputs=2:normalize=0:duration=longest")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-ac", "2", str(path)],
                   check=True)
    return path


def run(src, capsys, **kw):
    assert take.main(SimpleNamespace(file=src, out=None, text=None, model="small.en", **kw)) == 0
    return capsys.readouterr().out


def test_a_quiet_take_comes_out_at_studio_level_and_trimmed(tmp_path, capsys):
    pytest.importorskip("numpy")
    src = recorded(tmp_path / "take.wav", gain_db=-30)
    before = take.measure(src)
    out = run(src, capsys)
    after = take.measure(tmp_path / "take.clean.wav")
    assert abs(after["lufs"] - take.TARGET) < 1.0, after
    assert after["peak"] <= take.PEAK + 0.3, after
    assert after["seconds"] < before["seconds"] - 1.0, "the silence at the ends is trimmed"
    assert "get closer to the mic" in out
    assert "clipped" not in out


def test_the_same_take_cleans_to_the_same_bytes(tmp_path, capsys):
    pytest.importorskip("numpy")
    src = recorded(tmp_path / "take.wav", gain_db=-12)
    run(src, capsys)
    first = (tmp_path / "take.clean.wav").read_bytes()
    run(src, capsys)
    assert (tmp_path / "take.clean.wav").read_bytes() == first


def test_a_clipped_take_says_so(tmp_path, capsys):
    pytest.importorskip("numpy")
    src = recorded(tmp_path / "take.wav", gain_db=12, hum=False)
    assert "clipped" in run(src, capsys)


def test_refuses_to_overwrite_the_take(tmp_path):
    src = tmp_path / "take.wav"
    src.write_bytes(b"")
    with pytest.raises(SystemExit, match="the take itself"):
        take.main(SimpleNamespace(file=src, out=src, text=None, model="small.en"))


def test_a_reading_script_is_scored_on_its_quoted_lines():
    script = "# Voice test\n\nRead it calmly.\n\n> A customer clicks Pay.\n>\n> Where does the time go?\n\nAbout 50 seconds.\n"
    assert take.spoken_text(script) == "A customer clicks Pay.\n\nWhere does the time go?"
    assert take.spoken_text("Just the words.") == "Just the words."
