"""The Remotion engine through the kit's engine interface, in a real headless browser. Skipped where the
engine's packages or a browser are missing."""
import json
import shutil

import pytest

from studio_kit.engine import Engine
from studio_kit.env import engine_dir, resolve_browser
from test_render import make_video

needs_engine = pytest.mark.skipif(
    not (engine_dir("remotion") / "node_modules" / "remotion").is_dir() or not resolve_browser()[0] or not shutil.which("node"),
    reason="the Remotion engine's packages or a browser are not installed")

TERMINAL = """
import React from 'react';
import {Chapter, Terminal, useClip} from '@studio';

const RUNS = [{argv: ['ls'], stdout: 'a\\nb\\n', stderr: '', exit: 0},
	{argv: ['cat', 'notes.txt'], stdout: 'a much longer line of output that the panel has to shrink to fit its width\\n', stderr: '', exit: 0}];

export const S1: React.FC = () => {
	const {t} = useClip();
	return <Chapter><Terminal at={[0, 0]} w={8} runs={RUNS} progress={Math.min(1, t / 1.5)} size={24} /></Chapter>;
};
"""


@needs_engine
def test_a_terminal_keeps_one_text_size_as_it_plays(tmp_path):
    """It was sized for the lines shown so far, so its text shrank when the long line appeared."""
    make_video(tmp_path)
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "remotion"}))
    (tmp_path / "scenes" / "s1.tsx").write_text(TERMINAL)
    (tmp_path / "scenes" / "index.ts").write_text("import {S1} from './s1';\nexport default {s1: S1} as Record<string, import('react').FC>;\n")
    (tmp_path / "scenes" / "kit.tsx").unlink()
    early, late = Engine(tmp_path).boxes_at([{"clip": "s1", "t": 0.4}, {"clip": "s1", "t": 1.9}])
    rows = lambda f: {round(b["h"], 2) for b in f["boxes"] if b["name"].startswith("terminal row")}
    assert len(rows(early)) == 1 and rows(early) == rows(late)
