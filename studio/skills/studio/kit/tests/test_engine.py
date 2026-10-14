import json
import shutil

import pytest

from studio_kit import engine
from studio_kit.env import engine_dir

node = pytest.mark.skipif(not shutil.which("node"), reason="node not installed")


@node
def test_a_reply_larger_than_a_pipe_buffer_arrives_whole(tmp_path, monkeypatch):
    # An engine that answers through the shared reply module, as the three engine CLIs do. A 64 KiB
    # pipe used to cut a reply this size short when the engine exited before stdout drained.
    reply = (engine_dir("live").parent / "shared" / "reply.js").as_uri()
    script = (f"import {{ reply }} from {json.dumps(reply)}; const i = process.argv.indexOf('--reply'); "
              "reply(i > 0 ? process.argv[i + 1] : null, "
              "{frames: Array.from({length: 4000}, (_, n) => ({n, pad: 'x'.repeat(40)}))})")
    monkeypatch.setattr(engine.Engine, "_command",
                        lambda self, op, *a: ["node", "--input-type=module", "-e", script, op, *a])
    frames = engine.Engine(tmp_path, "live")._call("boxesAt")["frames"]
    assert len(frames) == 4000 and frames[-1]["n"] == 3999
