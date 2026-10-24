from studio_kit import ablation


def test_ablation_keeps_two_separate_starts_and_never_overwrites(tmp_path, monkeypatch):
    monkeypatch.setenv('STUDIO_HOME', str(tmp_path))
    run, prompts, commands = ablation.prepare('a shader "pixel"', today='2026-10-24')
    assert run.parent == tmp_path / 'ablation/2026-10-24'
    assert (run / 'studio/video.json').exists()
    assert not (run / 'bare/video.json').exists()
    assert not (run / 'bare/scenes').exists()
    assert prompts['bare'].splitlines()[0] == prompts['studio'].splitlines()[0]
    assert '--safe-mode --disable-slash-commands' in commands['bare']
    assert '--plugin-dir' in commands['studio']
    (run / 'bare/result.txt').write_text('Keep the first experiment.')
    second, _, _ = ablation.prepare(today='2026-10-24')
    assert second != run and (run / 'bare/result.txt').exists()
