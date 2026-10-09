import json
import shutil
from types import SimpleNamespace

import pytest

from studio_kit import cli, workspace
from studio_kit.env import ROOT

PROBE = """import json, os, sys
import studio_kit
print(json.dumps({"cwd": os.getcwd(), "video": os.environ["STUDIO_VIDEO"], "work": os.environ["STUDIO_WORK"],
                  "stdin": sys.stdin.read(), "args": sys.argv[1:], "pinned": os.environ.get("STUDIO_PINNED"),
                  "path": os.environ["PATH"].split(os.pathsep)[0]}))
sys.exit(int(os.environ.get("EXIT", "0")))
"""


@pytest.fixture
def video(tmp_path, monkeypatch):
    monkeypatch.delenv("STUDIO_OWNER", raising=False)
    v = tmp_path / "v"
    (v / "sims").mkdir(parents=True)
    (v / "video.json").write_text("{}\n")
    (v / "sims" / "probe.py").write_text(PROBE)
    return v


def test_a_script_runs_in_the_video_with_the_kit(video, capfd, monkeypatch):
    monkeypatch.setenv("STUDIO_PINNED", "1")           # set by bin/studio when it routed to a pinned copy
    assert cli.main(["run", str(video), str(video / "sims" / "probe.py"), "--", "--flag", "x"]) == 0
    seen = json.loads(capfd.readouterr().out)          # streamed to our stdout, not captured
    v = str(video.resolve())
    assert seen == {"cwd": v, "video": v, "work": f"{v}/.studio/work", "stdin": "", "args": ["--", "--flag", "x"],
                    "pinned": None, "path": str(ROOT / "bin")}
    assert cli.main(["run", "--allow-outside", str(video), "sims/probe.py", "a", "--", "b"]) == 0
    assert json.loads(capfd.readouterr().out)["args"] == ["a", "--", "b"]


def test_a_terminated_run_stops_its_script(video, tmp_path):
    import os
    import signal
    import subprocess
    import sys
    import time
    pidfile = tmp_path / "pid"
    (video / "sims" / "wait.py").write_text(f"import os, time\nopen({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
                                            "time.sleep(60)\n")
    run = subprocess.Popen([sys.executable, "-m", "studio_kit.cli", "run", str(video), "sims/wait.py"])
    for _ in range(100):
        if pidfile.exists() and pidfile.read_text():
            break
        time.sleep(0.1)
    run.send_signal(signal.SIGTERM)
    assert run.wait(timeout=10) == 128 + signal.SIGTERM
    with pytest.raises(ProcessLookupError):
        for _ in range(50):
            os.kill(int(pidfile.read_text()), 0)
            time.sleep(0.1)


def test_a_path_relative_to_the_video_and_the_exit_status_pass_through(video, monkeypatch):
    monkeypatch.setenv("EXIT", "7")
    assert cli.main(["run", str(video), "sims/probe.py"]) == 7


def test_a_script_outside_the_video_needs_allow_outside(video, tmp_path, capfd):
    outside = tmp_path / "probe.py"
    shutil.copy(video / "sims" / "probe.py", outside)
    with pytest.raises(SystemExit, match="outside .*--allow-outside"):
        cli.main(["run", str(video), str(outside)])
    (video / "sims" / "link.py").symlink_to(outside)
    with pytest.raises(SystemExit, match="outside"):
        cli.main(["run", str(video), "sims/link.py"])
    assert cli.main(["run", "--allow-outside", str(video), str(outside)]) == 0
    capfd.readouterr()


def test_only_python_and_node_scripts_and_only_for_the_owner(video):
    (video / "sims" / "x.sh").write_text("echo hi\n")
    with pytest.raises(SystemExit, match="takes a Python"):
        cli.main(["run", str(video), "sims/x.sh"])
    workspace.main_lock(SimpleNamespace(video=video, action="acquire", owner="b", recover=False))
    with pytest.raises(SystemExit, match="video owned by b"):
        cli.main(["run", str(video), "sims/probe.py"])


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_a_node_script_runs_with_node(video, capfd):
    (video / "sims" / "probe.mjs").write_text("console.log(process.cwd() === process.env.STUDIO_VIDEO)\n")
    assert cli.main(["run", str(video), "sims/probe.mjs"]) == 0
    assert capfd.readouterr().out.strip() == "true"
