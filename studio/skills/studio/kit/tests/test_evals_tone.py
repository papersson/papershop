"""The tone evals' regex graders say what their prompts mean: a comic tone recorded in any wording,
and no comic tone set where the user only asked for "delightful"."""
import re

import pytest

from studio_kit.env import ROOT

EVALS = ROOT.parents[1] / "evals"


def grader(name):
    head = (EVALS / name).read_text().split("---")[1]
    pattern = re.search(r"^pattern: '(.*)'$", head, re.M).group(1)
    return re.compile(pattern, re.I if re.search(r"^flags: i$", head, re.M) else 0)


@pytest.mark.parametrize("text", ["studio new caching --tone comic", "with the tone set to comic", '"tone": "comic"',
                                  "Tone: comic", "the video's tone is comic"])
def test_the_comic_eval_finds_a_comic_tone_however_it_is_worded(text):
    assert grader("tone-comic-on-request/graders/comic-tone.md").search(text)


@pytest.mark.parametrize("text,found", [("studio new v --tone comic", True), ('"tone": "comic"', True),
                                        ("the tone stays plain; no comic tone unless asked", False),
                                        ("tone set to plain, not comic", False)])
def test_the_delightful_eval_flags_only_a_comic_tone_actually_set(text, found):
    assert bool(grader("tone-delightful-is-plain/graders/no-comic-tone.md").search(text)) is found
