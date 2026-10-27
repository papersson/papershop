

def test_fetched_extras_are_remembered_once_outside_the_environment(tmp_path, monkeypatch):
    from studio_kit import doctor
    (tmp_path / "kit").mkdir()
    monkeypatch.setattr(doctor, "ROOT", tmp_path)
    doctor.remember_extras(("kokoro",))
    doctor.remember_extras(("align", "kokoro"))
    assert (tmp_path / "kit" / ".extras").read_text().split() == ["kokoro", "align"]
