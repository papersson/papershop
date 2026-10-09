import json
import shutil
from types import SimpleNamespace

import pytest

from studio_kit import cli, workspace

PROBE = """import json, os, sys
import studio_kit
print(json.dumps({"cwd": os.getcwd(), "video": os.environ["STUDIO_VIDEO"], "work": os.environ["STUDIO_WORK"],
                  "stdin": sys.stdin.read(), "args": sys.argv[1:]}))
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


def test_a_script_runs_in_the_video_with_the_kit(video, capfd):
    assert cli.main(["run", str(video), str(video / "sims" / "probe.py"), "--flag", "x"]) == 0
    seen = json.loads(capfd.readouterr().out)          # streamed to our stdout, not captured
    v = str(video.resolve())
    assert seen == {"cwd": v, "video": v, "work": f"{v}/.studio/work", "stdin": "", "args": ["--flag", "x"]}


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
