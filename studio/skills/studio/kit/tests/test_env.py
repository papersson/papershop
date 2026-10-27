from pathlib import Path
import tomllib
from studio_kit.env import resolve_browser
from studio_kit import doctor
from types import SimpleNamespace
import urllib.error
import pytest

MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def test_studio_browser_wins_over_installed_chrome():
    path, source = resolve_browser({"STUDIO_BROWSER": "/opt/chrome"}, "Darwin", exists=lambda p: True, shell="/x/shell")
    assert (path, source) == ("/opt/chrome", "STUDIO_BROWSER")


def test_installed_chrome_on_mac():
    path, source = resolve_browser({}, "Darwin", exists=lambda p: p == MAC_CHROME, shell="")
    assert (path, source) == (MAC_CHROME, "installed Chrome")


def test_linux_uses_chromium_on_path_when_no_chrome():
    which = {"chromium": "/nix/store/x/bin/chromium"}.get
    path, source = resolve_browser({}, "Linux", which=which, shell="")
    assert path == "/nix/store/x/bin/chromium" and source == "chromium on PATH"


def test_falls_back_to_engine_download():
    assert resolve_browser({}, "Darwin", exists=lambda p: False, shell="") == (None, "engine download")


def test_engine_headless_shell_beats_installed_chrome():
    path, source = resolve_browser({}, "Darwin", exists=lambda p: True, shell="/e/chrome-headless-shell")
    assert (path, source) == ("/e/chrome-headless-shell", "engine headless shell")


def test_spacy_model_is_a_locked_kokoro_dependency():
    # Kokoro's phonemizer loads en_core_web_sm, so it installs with the extra from the lock.
    root = Path(__file__).resolve().parents[1]
    kokoro = tomllib.loads((root / "pyproject.toml").read_text())["project"]["optional-dependencies"]["kokoro"]
    assert any(d.startswith("en-core-web-sm @ https://") for d in kokoro)
    assert 'name = "en-core-web-sm"' in (root / "uv.lock").read_text()


def test_missing_model_fails_before_synthesis_with_one_repair(monkeypatch):
    monkeypatch.setattr(doctor.importlib.util, "find_spec", lambda name: None if name == "en_core_web_sm" else object())
    with pytest.raises(SystemExit, match="doctor --fetch --extra kokoro"):
        doctor.require_extra("kokoro")


def test_blocked_model_host_is_diagnostic_not_success(monkeypatch):
    def blocked(*args, **kwargs):
        raise urllib.error.HTTPError("https://github.com/", 403, "blocked", {}, None)
    monkeypatch.setattr(doctor.urllib.request, "urlopen", blocked)
    level, host, detail, fix = doctor.check_host(doctor.HOSTS[-1])
    assert level == doctor.WARN and "github.com" in host
    assert "403" in detail and "mirror" in fix


def test_the_launch_check_skips_without_the_live_engine(monkeypatch, tmp_path):
    monkeypatch.setattr(doctor, "engine_dir", lambda name: tmp_path / name)
    level, name, detail, _ = doctor.check_launch()
    assert (level, name) == (doctor.SKIP, "browser launch") and detail.startswith("skipped")


live_installed = pytest.mark.skipif(
    not (doctor.engine_dir("live") / "node_modules" / "playwright-core").is_dir() or not doctor.shutil.which("node"),
    reason="the live engine or node is not installed")


@live_installed
@pytest.mark.parametrize("stderr,hint", [
    ("browserType.launch: Target page, context or browser has been closed\nsandbox: Operation not permitted", "sandbox restrictions"),
    ("SyntaxError: bad scene", "prints the engine's full error"),
])
def test_a_failed_launch_names_the_cause_and_a_fix(monkeypatch, stderr, hint):
    calls = []
    class Failed:
        def __init__(self, cmd, **kw):
            calls.append(cmd)
            self.returncode, self.pid = 1, 0
        def communicate(self, timeout=None):
            return "", stderr
    monkeypatch.setattr(doctor.proc, "popen", Failed)
    level, _, detail, fix = doctor.check_launch()
    assert level == doctor.FAIL and stderr.splitlines()[-1] in detail and hint in fix
    assert calls[0][1].endswith("engines/live/cli.mjs") and calls[0][2] == "still"    # the engine's own command


@live_installed
def test_a_hung_launch_is_killed_with_what_it_started(monkeypatch, tmp_path):
    import os
    import sys
    import time
    from studio_kit import engine
    pidfile = tmp_path / "child.pid"
    hang = (f"import subprocess, sys, time; c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
            f"open({str(pidfile)!r}, 'w').write(str(c.pid)); time.sleep(60)")
    monkeypatch.setattr(engine.Engine, "_command", lambda self, *a: [sys.executable, "-c", hang])
    level, _, detail, fix = doctor.check_launch(timeout=2)
    assert level == doctor.FAIL and "did not finish in 2 s" in detail and "sandbox" in fix
    with pytest.raises(ProcessLookupError):      # the browser's stand-in went with the engine
        for _ in range(50):
            os.kill(int(pidfile.read_text()), 0)
            time.sleep(0.1)


def test_downloaded_browser_is_independent_of_engine_node_modules(tmp_path, monkeypatch):
    from studio_kit import env
    monkeypatch.setattr(env, 'ROOT', tmp_path)
    shell = tmp_path / '.cache/browser/chromium_headless_shell-1243/chrome-mac/headless_shell'
    shell.parent.mkdir(parents=True)
    shell.write_bytes(b'browser')
    assert env.headless_shell() == str(shell)


def test_explicit_fetch_uses_playwright_and_the_independent_browser_cache(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(doctor, 'engine_dir', lambda name: tmp_path / name)
    monkeypatch.setattr(doctor, 'browser_cache', lambda: tmp_path / 'browser')
    monkeypatch.setattr(doctor.proc, 'run', lambda cmd, **kw: calls.append((cmd, kw)) or SimpleNamespace(returncode=0))
    doctor.fetch()
    assert calls[0][0] == ['npm', 'ci', '--no-audit', '--no-fund']
    assert calls[1][0][-2:] == ['install', 'chromium-headless-shell']
    assert calls[1][1]['env']['PLAYWRIGHT_BROWSERS_PATH'] == str(tmp_path / 'browser')
