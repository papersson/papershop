from studio_kit import publish
from test_render import make_video


def test_page_is_ascii_and_matches_the_drive(tmp_path):
    t = make_video(tmp_path)
    t["tracks"]["narration"][0]["caption"] = "Charged twice · or once"
    author = publish.page_html(t, {"title": "T", "drive": "author"}, 3)
    learner = publish.page_html(t, {"title": "T", "drive": "learner"}, 3)
    script = author.split("<script>", 1)[1]
    script.encode("ascii")
    assert '<meta charset="utf-8">' in author
    assert ">Annotate<" in author and 'data-kind="picture"' in author
    assert ">Lost me here<" in learner and 'data-kind="picture"' not in learner
    assert '"v1 (cut 3)"' in author


def test_poster_offsets_count_from_start_or_back_from_end(tmp_path):
    t = make_video(tmp_path)
    assert publish.poster_time(t, ["s2_01", 1.0]) == 3.5
    assert publish.poster_time(t, ["s2_01", -0.2]) == 3.3
