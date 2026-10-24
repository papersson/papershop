import json

import pytest

from studio_kit import settings


def write(tmp_path, cfg):
    (tmp_path / "video.json").write_text(json.dumps(cfg))


def test_defaults_without_a_file(tmp_path):
    cfg = settings.load(tmp_path)
    assert cfg["engine"] == "live" and cfg["keep_cuts"] == 10
    assert settings.raw(tmp_path) == {}


def test_file_values_override_defaults(tmp_path):
    write(tmp_path, {"engine": "live", "gl": "gpu"})
    assert settings.load(tmp_path)["engine"] == "live"
    assert settings.load(tmp_path)["gl"] == "gpu"


@pytest.mark.parametrize("key,value", [("engine", "missing"), ("gl", "metal"), ("motion", "fast")])
def test_enumerated_values_are_checked(tmp_path, key, value):
    write(tmp_path, {key: value})
    with pytest.raises(SystemExit, match=key):
        settings.load(tmp_path)


def test_webgl_renders_on_the_cpu_unless_the_video_asks_for_the_gpu(tmp_path):
    assert settings.load(tmp_path)["gl"] == "cpu"
    write(tmp_path, {"gl": "gpu"})
    assert settings.load(tmp_path)["gl"] == "gpu"


