from pathlib import Path
from types import SimpleNamespace

import pytest

from studio_kit import review


def test_reviewer_sees_only_the_supplied_prompt_in_an_empty_folder():
    seen = []
    def runner(text, cwd):
        assert list(Path(cwd).iterdir()) == []
        seen.append(cwd)
        return SimpleNamespace(returncode=0, stdout="Check the claim.", stderr="")
    assert review.run_reviewer("The brief.", runner) == "Check the claim."
    assert len(seen) == 1 and not Path(seen[0]).exists()


def test_failed_reviewer_reports_the_failure():
    with pytest.raises(RuntimeError, match="offline"):
        review.run_reviewer("brief", lambda text, cwd: SimpleNamespace(returncode=1, stdout="", stderr="offline"))
