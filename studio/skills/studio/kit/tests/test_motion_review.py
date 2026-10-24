import json
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from studio_kit import moments, motion_review
from studio_kit import timeline as tl
from test_render import make_video


def test_a_sequence_can_put_its_time_fourth():
    t = {"fps": 30, "tracks": {"scene": [{"id": "s1", "start": 0.0, "end": 4.0}]}}
    m = moments.sequence(t, "s1", 1.0, 12, 15, "motion", before=3)
    assert m["frames"][3] == 1.0 and m["frames"][0] == 0.8 and len(m["frames"]) == 12
    assert m["id"] == "motion_s1_1.0_15fps_3b" and moments.sequence(t, "s1", 1.0)["id"] == "strip_s1_1.0"


