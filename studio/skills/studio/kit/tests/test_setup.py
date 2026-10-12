"""First-run checks must be usable without installing anything or trusting an old video pin."""
import os
import shutil
import sys
from types import SimpleNamespace

import pytest

from studio_kit import cli, doctor, proc


def executable(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(0o755)


def launcher(tmp_path):
    root = tmp_path / "plugin with spaces"
    (root / "bin").mkdir(parents=True)
    shutil.copyfile(doctor.ROOT / "bin/studio", root / "bin/studio")
    (root / "bin/studio").chmod(0o755)
    env = {**os.environ, "STUDIO_NO_NIX": "1", "PATH": "/usr/bin:/bin", "STUDIO_HOME": str(tmp_path / "home")}
    for k in ("STUDIO_ENV", "STUDIO_PINNED", "PYTHONPATH"):
        env.pop(k, None)
    return root, env


def test_clean_machine_preflight_reports_missing_tools_without_bootstrap(tmp_path):
    root, env = launcher(tmp_path)
    video = tmp_path / "old video"
    (video / "video.json").parent.mkdir()
    (video / "video.json").write_text("{}")
    marker = tmp_path / "unexpected-install"
    executable(video / ".studio/bin/studio", f"touch '{marker}'")
    before = set(tmp_path.rglob("*"))
    result = proc.run([str(root / "bin/studio"), "preflight", str(video)], env=env, capture_output=True, text=True)
    assert result.returncode == 1 and "kit Python environment" in result.stdout
    assert "references/setup.md" in result.stdout and not marker.exists()
    assert set(tmp_path.rglob("*")) == before


def test_preflight_with_nix_does_not_enter_uncached_environment(tmp_path):
    root, env = launcher(tmp_path)
    env.pop("STUDIO_NO_NIX")
    marker = tmp_path / "nix-ran"
    executable(tmp_path / "tools/nix", f"touch '{marker}'")
    env["PATH"] = str(tmp_path / "tools") + ":" + env["PATH"]
    (root / "flake.nix").write_text("{}")
    (root / "flake.lock").write_text("{}")
    result = proc.run([str(root / "bin/studio"), "preflight"], env=env, capture_output=True, text=True)
    assert result.returncode == 1 and "not been prepared" in result.stdout
    assert not marker.exists() and not (root / ".cache").exists()


def test_ready_launcher_runs_read_only_diagnostics_without_uv_sync(tmp_path):
    root, env = launcher(tmp_path)
    tools = tmp_path / "tools"
    marker = tmp_path / "uv-ran"
    executable(tools / "uv", f"touch '{marker}'")
    for name, version in {"node": "22.0", "npm": "10.0", "ffmpeg": "6.0", "ffprobe": "6.0", "sox": "14.0"}.items():
        executable(tools / name, f"echo '{version}'")
    env["PATH"] = str(tools) + ":" + env["PATH"]
    (root / "kit/.venv/bin").mkdir(parents=True)
    (root / "kit/.venv/bin/python").symlink_to(sys.executable)
    # Run the real parser/diagnostics, so an empty or broken dispatcher cannot pass this test.
    (root / "kit/src").symlink_to(doctor.ROOT / "kit/src", target_is_directory=True)
    result = proc.run([str(root / "bin/studio"), "preflight", "--silent"], env=env, capture_output=True, text=True)
    assert result.returncode in (0, 1) and "preflight:" in result.stdout and "No installs" in result.stdout
    assert not marker.exists() and not (root / ".cache").exists()


def test_preflight_requires_selected_engine_but_not_unused_extras(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(doctor, "system_checks", lambda: [])
    monkeypatch.setattr(doctor, "engine_dir", lambda name: tmp_path / name)
    browser = tmp_path / "chrome"
    executable(browser, "exit 99")
    monkeypatch.setattr(doctor, "resolve_browser", lambda: (str(browser), "test"))
    monkeypatch.setattr(doctor, "extra_checks", lambda extras: [] if not extras else pytest.fail("silent requested"))
    for name in ("remotion", "live"):
        (tmp_path / name / "node_modules" / doctor.ENGINE_MARKER[name]).mkdir(parents=True)
        (tmp_path / name / "node_modules/@fontsource/ibm-plex-mono").mkdir(parents=True)
    assert cli.main(["preflight", "--silent"]) == 0
    shutil.rmtree(tmp_path / "live")
    assert cli.main(["preflight", "--silent"]) == 1
    assert "--engine live" in capsys.readouterr().out
    assert cli.main(["preflight", "--engine", "remotion", "--silent"]) == 0


def test_preflight_requires_default_narration_packages(monkeypatch, tmp_path):
    monkeypatch.setattr(doctor, "system_checks", lambda: [])
    monkeypatch.setattr(doctor, "check_engine", lambda e: (doctor.OK, "engine " + e, "installed", ""))
    monkeypatch.setattr(doctor.importlib.util, "find_spec", lambda name: None)
    browser = tmp_path / "chrome"
    executable(browser, "exit 99")
    monkeypatch.setattr(doctor, "resolve_browser", lambda: (str(browser), "test"))
    assert cli.main(["preflight"]) == 1
    assert cli.main(["preflight", "--silent"]) == 0


def test_doctor_only_requires_explicit_extras_and_selected_engines(monkeypatch):
    seen = []
    monkeypatch.setattr(doctor, "checks", lambda net=False: [
        (doctor.OK, "engine remotion", "installed", ""),
        (doctor.WARN, "engine live", "missing", "install live")])
    monkeypatch.setattr(doctor, "extra_checks", lambda extras: seen.extend(extras) or [])
    monkeypatch.setattr(doctor, "check_sounds", lambda offline=None: (doctor.WARN, "sound kit", "optional", ""))
    assert cli.main(["doctor", "--engine", "remotion", "--extra", "audio"]) == 0
    assert seen == ["audio"]
    assert cli.main(["doctor", "--engine", "live", "--extra", "audio"]) == 1


def test_explicit_model_source_is_used_and_load_failure_is_reported(monkeypatch):
    wheel = "/approved models/en_core_web_sm-3.8.0-py3-none-any.whl"
    monkeypatch.setenv("STUDIO_SPACY_MODEL", wheel)
    calls = []
    def run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(stdout="3.8\n", returncode=1 if len(calls) == 3 else 0)
    monkeypatch.setattr(doctor.proc, "run", run)
    with pytest.raises(SystemExit, match="could not load"):
        doctor.install_spacy_model()
    assert calls[1][-1] == wheel


@pytest.mark.parametrize("status,expected", [(0, doctor.OK), (1, doctor.FAIL)])
def test_speech_smoke_reports_real_process_failure(monkeypatch, status, expected):
    monkeypatch.setattr(doctor, "extra_checks", lambda extras: [])
    monkeypatch.setattr(doctor.proc, "run", lambda *a, **kw:
                        SimpleNamespace(returncode=status, stdout="The studio is ready.\n", stderr="model unavailable"))
    level, _, detail, fix = doctor.check_speech()
    assert level == expected
    if status:
        assert "model unavailable" in detail and "--speech" in fix


def test_speech_smoke_reports_timeout(monkeypatch):
    monkeypatch.setattr(doctor, "extra_checks", lambda extras: [])
    def timeout(cmd, **kwargs):
        raise proc.TimeoutExpired(cmd, kwargs["timeout"])
    monkeypatch.setattr(doctor.proc, "run", timeout)
    assert doctor.check_speech(timeout=1)[0] == doctor.FAIL
