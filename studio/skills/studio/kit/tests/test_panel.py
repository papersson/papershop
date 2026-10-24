import threading
from pathlib import Path
from types import SimpleNamespace

from studio_kit import panel


def test_panel_reads_three_roles_once_in_parallel_and_keeps_every_finding(tmp_path):
    (tmp_path / 'research').mkdir()
    (tmp_path / 'research/brief.md').write_text('Our question is why a pixel changes colour.')
    (tmp_path / 'SCRIPT.md').write_text('We follow one pixel.')
    barrier = threading.Barrier(3, timeout=5)
    folders = []
    def runner(text, cwd):
        folders.append(cwd)
        assert not list(Path(cwd).iterdir())
        assert 'why a pixel' in text and 'We follow one pixel' in text
        role = next(r for r in panel.ROLES if f'You are the {r}' in text)
        barrier.wait()
        return SimpleNamespace(returncode=0, stdout=f'{role}: explain the input.', stderr='')
    path = panel.make(tmp_path, runner)
    assert path.name == 'panel-1.md'
    assert len(set(folders)) == 3
    assert all(f'{r}: explain the input.' in path.read_text() for r in panel.ROLES)
    assert not list(tmp_path.glob('**/*receipt*'))


def test_unavailable_panel_reading_is_visible_and_does_not_gate(tmp_path):
    (tmp_path / 'research').mkdir()
    (tmp_path / 'research/brief.md').write_text('A brief.')
    def runner(*args):
        raise RuntimeError('test outage')
    path = panel.make(tmp_path, runner)
    assert path.read_text().count('test outage') == 3
    assert panel.make(tmp_path, runner).name == 'panel-2.md'


