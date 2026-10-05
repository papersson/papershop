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


@pytest.mark.parametrize("uv_index,pip_index,expected", [
    (None, "https://packages.example/simple", "https://packages.example/simple"),
    ("https://uv.example/simple", "https://pip.example/simple", "https://uv.example/simple"),
])
def test_spacy_wheel_uses_configured_index_without_github_fallback(monkeypatch, uv_index, pip_index, expected):
    monkeypatch.delenv("UV_INDEX_URL", raising=False)
    if uv_index:
        monkeypatch.setenv("UV_INDEX_URL", uv_index)
    monkeypatch.setenv("PIP_INDEX_URL", pip_index)
    calls = []
    def run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return SimpleNamespace(stdout="3.8\n" if len(calls) == 1 else "", returncode=0)
    monkeypatch.setattr(doctor.subprocess, "run", run)
    doctor.install_spacy_model()
    assert calls[1][0][-1] == "en-core-web-sm~=3.8.0"
    assert calls[1][1]["env"]["UV_INDEX_URL"] == expected
    assert len(calls) == 2 and "github" not in str([cmd for cmd, _ in calls])


def test_missing_model_fails_before_synthesis_with_one_repair(monkeypatch):
    monkeypatch.setattr(doctor.importlib.util, "find_spec", lambda name: None if name == "en_core_web_sm" else object())
    with pytest.raises(SystemExit, match="doctor --fetch --extra kokoro"):
        doctor.require_extra("kokoro")


def test_blocked_model_host_is_diagnostic_not_success(monkeypatch):
    def blocked(*args, **kwargs):
        raise urllib.error.HTTPError("https://raw.githubusercontent.com/", 403, "blocked", {}, None)
    monkeypatch.setattr(doctor.urllib.request, "urlopen", blocked)
    level, host, detail, fix = doctor.check_host(doctor.HOSTS[-1])
    assert level == doctor.WARN and "raw.githubusercontent.com" in host
    assert "403" in detail and "wheel" in fix
