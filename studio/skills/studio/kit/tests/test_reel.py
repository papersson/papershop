from studio_kit import reel


def test_reel_uses_real_narration_before_boards(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(reel.narration, 'narrate', lambda v: calls.append(('voice', v)))
    def make(v, boards):
        assert calls == [('voice', v)] and boards is True
        return {'cut': 1, 'pacing': {}}
    monkeypatch.setattr(reel.animatic, 'make', make)
    assert reel.make(tmp_path)['cut'] == 1
