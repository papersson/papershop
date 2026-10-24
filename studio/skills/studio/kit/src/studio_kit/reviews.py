"""Plain review findings, numbered only to preserve each reader's output."""
from pathlib import Path


def write(video, name, text):
    folder = Path(video) / "research" / "reviews"
    folder.mkdir(parents=True, exist_ok=True)
    number = 1
    while True:
        path = folder / f"{name}-{number}.md"
        try:
            with path.open("x") as out:
                out.write(text.rstrip() + "\n")
            return path
        except FileExistsError:
            number += 1
