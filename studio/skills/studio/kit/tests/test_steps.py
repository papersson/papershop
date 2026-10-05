import json
import shutil
import sys

import pytest

from studio_kit import steps


def fixture(tmp_path, command=None):
    (tmp_path / "first.py").write_text('print("first")\n')
    (tmp_path / "real.py").write_text('print("final")\n')
    spec = {"version": 1, "source": {"main.py": "real.py"},
            "commands": [command or [sys.executable, "main.py"]],
            "steps": [{"id": "first", "files": {"main.py": "first.py"}},
                      {"id": "final", "files": {"main.py": "real.py"}}]}
    manifest = tmp_path / "steps.json"
    manifest.write_text(json.dumps(spec))
    (tmp_path / "scenes").mkdir()
    return manifest, spec


def test_steps_record_actual_versions_output_and_final_source_binding(tmp_path):
    manifest, _ = fixture(tmp_path)
    result, output = steps.run(tmp_path, manifest)
    assert result["ok"]
    assert [s["commands"][0]["stdout"] for s in result["steps"]] == ["first\n", "final\n"]
    assert (output.parent / "first-0.stdout").read_bytes() == b"first\n"
    assert not steps.check(tmp_path)[0]["ok"]  # Source equality alone is not a scene binding.
    (tmp_path / "scenes/s1.tsx").write_text(f'import results from "../{output.relative_to(tmp_path)}";')
    assert steps.check(tmp_path)[0]["ok"]
    (tmp_path / "real.py").write_text('print("changed")\n')
    assert not steps.check(tmp_path)[0]["ok"]


def test_repeated_runs_preserve_evidence(tmp_path):
    manifest, _ = fixture(tmp_path)
    _, first = steps.run(tmp_path, manifest)
    _, second = steps.run(tmp_path, manifest)
    assert first != second and first.exists() and second.exists()


def test_expected_failure_and_timeout_record_diagnostics(tmp_path):
    manifest, spec = fixture(tmp_path, {"argv": [sys.executable, "-c", "import sys; print('expected', file=sys.stderr); sys.exit(2)"], "expected_exit": 2})
    result, _ = steps.run(tmp_path, manifest)
    assert result["ok"] and result["steps"][0]["commands"][0]["stderr"] == "expected\n"
    spec["commands"] = [[sys.executable, "-c", "import time; time.sleep(5)"]]
    spec["timeout"] = 0.05
    manifest.write_text(json.dumps(spec))
    result, output = steps.run(tmp_path, manifest)
    assert not result["ok"] and output.exists()
    assert result["steps"][0]["commands"][0]["timeout"]


def test_steps_reject_path_escape_and_shell_string(tmp_path):
    manifest, spec = fixture(tmp_path)
    spec["steps"][0]["files"] = {"../escape.py": "first.py"}
    manifest.write_text(json.dumps(spec))
    with pytest.raises(SystemExit, match="escapes"):
        steps.run(tmp_path, manifest)
    assert not (tmp_path.parent / "escape.py").exists()
    with pytest.raises(SystemExit, match="argv arrays"):
        steps.execute("echo wrong", tmp_path, 1)


@pytest.mark.skipif(shutil.which("rustc") is None, reason="Rust compiler is optional")
def test_rust_build_and_run_is_language_neutral(tmp_path):
    source = tmp_path / "real.rs"
    source.write_text('fn main() { println!("record {}", 7); }\n')
    spec = {"version": 1, "source": {"main.rs": "real.rs"},
            "commands": [["rustc", "main.rs", "-o", "demo"], ["./demo"]],
            "steps": [{"id": "complete", "files": {"main.rs": "real.rs"}}]}
    manifest = tmp_path / "steps.json"
    manifest.write_text(json.dumps(spec))
    result, _ = steps.run(tmp_path, manifest)
    assert result["ok"] and result["steps"][0]["commands"][-1]["stdout"] == "record 7\n"
