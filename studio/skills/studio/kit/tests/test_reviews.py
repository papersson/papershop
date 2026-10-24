from concurrent.futures import ThreadPoolExecutor

from studio_kit import reviews


def test_records_preserve_parallel_findings_without_overwriting(tmp_path):
    with ThreadPoolExecutor(max_workers=3) as pool:
        paths = list(pool.map(lambda n: reviews.write(tmp_path, "panel", f"Finding {n}"), range(3)))
    assert len(set(paths)) == 3
    assert {p.read_text() for p in paths} == {f"Finding {n}\n" for n in range(3)}
    assert all(p.parent == tmp_path / "research/reviews" for p in paths)
