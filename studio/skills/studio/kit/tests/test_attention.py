"""The attention audit reads staging mistakes off frames: two places changing at once, motion in a
rest, a far jump between onsets. Synthetic frames, so each case is one mistake and nothing else."""
import pytest

np = pytest.importorskip("numpy")

from studio_kit import attention as a  # noqa: E402

GROUND = 20


def frame(*squares):
    """A dark frame with bright squares, each (x, y, size) in pixels of the 480 by 270 sample."""
    im = np.full((a.H, a.W, 3), GROUND, np.uint8)
    for x, y, s in squares:
        im[y:y + s, x:x + s] = 235
    return im


def hold(f, seconds):
    return [f] * int(seconds * a.FPS)


def slide(x0, x1, y, s, seconds, still=()):
    n = int(seconds * a.FPS)
    return [frame((round(x0 + (x1 - x0) * i / (n - 1)), y, s), *still) for i in range(n)]


def test_one_thing_at_a_time_passes():
    rows = a.analyse(hold(frame(), 1) + slide(120, 160, 120, 40, 1) + hold(frame((160, 120, 40)), 2)
                     + slide(210, 260, 120, 40, 1, still=[(160, 120, 40)]) + hold(frame((160, 120, 40), (260, 120, 40)), 2))
    s = a.summarise(rows, "s1", rests=[(4.5, 6.0)])
    fails, warns = a.verdict(s)
    assert s["onsets"] == 2 and s["split"] == 0 and s["far_jumps"] == 0 and s["rest_motion"] == 0
    assert fails == [] and not any(w.startswith(("split", "far_jumps", "fast_onsets")) for w in warns)


def test_two_far_places_changing_at_once_is_a_split():
    n = 5
    both = [frame((20 + 10 * i, 30, 30), (400 - 10 * i, 220, 30)) for i in range(n)]
    s = a.summarise(a.analyse(hold(frame(), 1) + both + hold(both[-1], 2)), "s1")
    assert s["split"] > 0.5
    assert any(w.startswith("split") for w in a.verdict(s)[1])


def test_motion_inside_a_rest_fails():
    rows = a.analyse(hold(frame((100, 100, 40)), 2) + slide(100, 300, 100, 40, 1) + hold(frame((300, 100, 40)), 1))
    s = a.summarise(rows, "s1", rests=[(1.0, 4.0)], where=True)
    fails, _ = a.verdict(s)
    assert s["rest_motion"] > 0.5
    assert fails and "marked rest" in fails[0]
    assert any(n.startswith("motion inside the rest 1.0-4.0 s") for n in s["notes"])


def test_a_jump_across_the_frame_between_onsets():
    rows = a.analyse(hold(frame(), 1) + slide(10, 40, 10, 30, 1) + hold(frame((40, 10, 30)), 2)
                     + slide(400, 430, 220, 30, 1, still=[(40, 10, 30)]) + hold(frame((40, 10, 30), (430, 220, 30)), 2))
    s = a.summarise(rows, "s1", where=True)
    assert s["far_jumps"] == 1.0
    assert any(n.startswith("far jumps at") for n in s["notes"])


def test_the_command_is_wired():
    from studio_kit import cli
    help_, _, handler = cli.COMMANDS["attention"]
    assert handler == "attention:main"
