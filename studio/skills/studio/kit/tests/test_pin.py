import pytest

from studio_kit import pin, new


def test_init_copies_the_kit_without_heavy_directories(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    video, _ = new.create("v", directory=str(tmp_path / "v"))
    p = pin.init(video)
    assert (p / "bin" / "studio").exists() and (p / "kit" / "src" / "studio_kit" / "pin.py").exists()
    assert (p / "engines" / "remotion" / "cli.mjs").exists() and (p / "flake.lock").exists()
    assert not (p / "engines" / "remotion" / "node_modules").exists()
    assert "node_modules" in (p / ".gitignore").read_text()
    assert (p / "PIN").read_text().split()[0] == pin.plugin_version()


def test_init_refuses_to_overwrite_and_update_replaces_sources(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    video, _ = new.create("v", directory=str(tmp_path / "v"))
    p = pin.init(video)
    with pytest.raises(SystemExit, match="--update"):
        pin.init(video)
    (p / "kit" / "src" / "studio_kit" / "stale.py").write_text("x = 1\n")
    (p / "engines" / "remotion" / "node_modules").mkdir()
    pin.init(video, update=True)
    assert not (p / "kit" / "src" / "studio_kit" / "stale.py").exists()
    assert (p / "engines" / "remotion" / "node_modules").exists()      # installed packages are kept


def test_init_needs_a_video_folder(tmp_path):
    with pytest.raises(SystemExit, match="not a video folder"):
        pin.init(tmp_path)


def test_init_copies_the_shared_pixel_module_and_both_engines(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    video, _ = new.create("v", directory=str(tmp_path / "v"))
    p = pin.init(video)
    assert (p / "engines" / "shared" / "pixels.ts").exists()
    assert (p / "engines" / "motion-canvas" / "cli.mjs").exists() and (p / "engines" / "motion-canvas" / "src" / "map.ts").exists()
    assert not (p / "engines" / "motion-canvas" / "node_modules").exists()
