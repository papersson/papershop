"""The motion glossary's matcher: a note names a term when it says the term's words together."""
import pytest

from studio_kit import glossary


@pytest.mark.parametrize("text,terms", [
    ("this frame is empty on the right", []),              # the review's false "frame on"
    ("frame on the three replicas", ["frame on"]),
    ("Stagger these and blur them together", ["stagger", "blur together"]),
    ("ease it out", ["ease out"]),
    ("panning across to the db", ["pan"]),
    ("let the sign settle when it lands", ["settle"]),
    ("the count goes up slowly", []),                        # not "count-up"
    ("match the cut", []),                                   # not "match cut"
    ("push in on the ladder, then pull it back", ["push-in", "pull back"]),
    ("dim the rest while it fails", ["dim the rest"]),
    ("the box is out of focus and the frame shakes on landing", ["shake"]),
])
def test_a_term_is_its_words_together(text, terms):
    assert [g["term"] for g in glossary.find(text)] == terms


@pytest.mark.parametrize("text,terms", [
    ("orbit round the stack once it opens", ["orbit"]),
    ("tilt it so the layers show", ["tilt"]),
    ("open it into depth on the cue, then flatten it back", ["open into depth", "flatten"]),
    ("explode the stack", ["explode"]),
    ("a projected callout on the heads", ["projected callout", "callout"]),
])
def test_the_3d_terms_are_their_words_together(text, terms):
    assert sorted(g["term"] for g in glossary.find(text)) == sorted(terms)
