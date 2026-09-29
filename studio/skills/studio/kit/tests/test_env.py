from studio_kit.env import resolve_browser

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
