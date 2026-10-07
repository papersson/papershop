import json

import pytest

from studio_kit import settings


def write(tmp_path, cfg):
    (tmp_path / "video.json").write_text(json.dumps(cfg))


def test_defaults_without_a_file(tmp_path):
    cfg = settings.load(tmp_path)
    assert cfg["engine"] == "remotion" and cfg["checkpoints"] == "few" and cfg["keep_cuts"] == 10
    assert settings.raw(tmp_path) == {}


def test_file_values_override_defaults(tmp_path):
    write(tmp_path, {"engine": "motion-canvas", "checkpoints": "many", "drive": "learner"})
    cfg = settings.load(tmp_path)
    assert (cfg["engine"], cfg["checkpoints"], cfg["drive"], cfg["genre"]) == ("motion-canvas", "many", "learner", "explainer")
    assert settings.raw(tmp_path) == {"engine": "motion-canvas", "checkpoints": "many", "drive": "learner"}


@pytest.mark.parametrize("key,value", [("checkpoints", "some"), ("level", "advanced")])
def test_enumerated_values_are_checked(tmp_path, key, value):
    write(tmp_path, {key: value})
    with pytest.raises(SystemExit, match=key):
        settings.load(tmp_path)
