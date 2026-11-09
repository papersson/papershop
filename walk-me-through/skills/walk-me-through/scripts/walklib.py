"""What the walk-me-through scripts share: the caption and writing rules, the click list's lint, and
a headless Chrome. Standard library only; run the scripts with `python3 -I`."""
import html
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ENGINE = SKILL / "engine"
SIZES = [(2000, 1150), (1440, 900), (1280, 720)]
CAPTION_WORDS = 12

# ---------------------------------------------------------------- writing rules

def strip_code(text):
    """Text with `code` spans removed: code may hold semicolons and dots that are not prose."""
    return re.sub(r"`[^`]*`", "x", text or "")


def words(text):
    return [w for w in strip_code(text).split() if re.search(r"\w", w)]


def sentences(text):
    """Sentence ends: . ! ? followed by a space and more text. Decimals and code spans don't count."""
    body = strip_code(text).strip()
    return len(re.findall(r"[.!?](?=\s+\S)", body)) + (1 if body else 0)


def punctuation_problems(text):
    problems = []
    bare = strip_code(text)
    if "\u2014" in bare or re.search(r"\s[\u2013-]\s", bare):
        problems.append("has a dash used as punctuation; use a full stop or a comma")
    if ";" in bare:
        problems.append("has a semicolon; split it or cut half")
    return problems


def caption_problems(text):
    if not text:
        return []
    problems = []
    n = len(words(text))
    if n > CAPTION_WORDS:
        problems.append(f"caption has {n} words, the limit is {CAPTION_WORDS}")
    if sentences(text) > 1:
        problems.append("caption has more than one sentence: the click is doing two things")
    if "?" in strip_code(text):
        problems.append("caption asks a question; say the thing instead")
    return problems + [f"caption {p}" for p in punctuation_problems(text)]


def title_problems(title):
    problems = []
    if re.match(r"^\s*(chapter\s+)?\d+[.):]?\s", title, re.I):
        problems.append("starts with a number; chapter titles are plain sentences")
    if len(words(title)) > 9:
        problems.append(f"has {len(words(title))} words; keep a chapter title short")
    return problems + punctuation_problems(title)

# ---------------------------------------------------------------- the click list

def load_list(path):
    try:
        return json.loads(Path(path).read_text())
    except json.JSONDecodeError as e:
        raise SystemExit(f"{path}: not valid JSON: {e}")


def lint(spec):
    """(problems, notes) for a click list. Problems block a build; notes are advice."""
    problems, notes = [], []
    if not isinstance(spec.get("title"), str) or not spec["title"].strip():
        problems.append("the list needs a title")
    chapters = spec.get("chapters")
    if not isinstance(chapters, list) or not chapters or not all(isinstance(c, str) and c.strip() for c in chapters):
        problems.append("the list needs chapters: a list of plain sentences")
        chapters = []
    for i, title in enumerate(chapters, 1):
        problems += [f"chapter {i} title '{title}' {p}" for p in title_problems(title)]
    clicks = spec.get("clicks")
    if not isinstance(clicks, list) or not clicks:
        problems.append("the list needs clicks")
        clicks = []
    last = 0
    for n, c in enumerate(clicks, 1):
        if not isinstance(c, dict):
            problems.append(f"click {n} is not an object")
            continue
        ch = c.get("chapter")
        if not isinstance(ch, int) or not 1 <= ch <= len(chapters):
            problems.append(f"click {n} has chapter {ch!r}; chapters run from 1 to {len(chapters)}")
        elif ch < last:
            problems.append(f"click {n} goes back from chapter {last} to {ch}")
        else:
            last = ch
        change = c.get("change")
        if c.get("clear"):
            pass
        elif not isinstance(change, str) or len(words(change)) < 2:
            problems.append(f"click {n} does not say what changes (give it a 'change')")
        elif re.search(r"\b(and then|then|while|as well as)\b", change):
            notes.append(f"click {n}'s change may be two changes: '{change}'")
        problems += [f"click {n} {p}" for p in caption_problems(c.get("caption", ""))]
    for i in range(1, len(chapters) + 1):
        if clicks and not any(isinstance(c, dict) and c.get("chapter") == i for c in clicks):
            problems.append(f"chapter {i} has no clicks")
    notes_list = spec.get("notes")
    if notes_list is not None and (not isinstance(notes_list, list) or len(notes_list) > len(chapters)):
        problems.append("notes must be a list with at most one entry per chapter")
    if "cover" in spec and not isinstance(spec["cover"], (bool, str)):
        problems.append("cover must be true, false or the cover's question")
    if clicks and not 15 <= len(clicks) <= 25:
        notes.append(f"{len(clicks)} clicks; a page usually holds 15 to 25, and more usually means two pages")
    return problems, notes


def markdown(spec):
    """The click list as the reader will follow it."""
    chapters, clicks = spec.get("chapters", []), spec.get("clicks", [])
    out = [f"# {spec.get('title', '(untitled)')}", ""]
    cover = spec.get("cover")
    shape = f"{len(clicks)} clicks in {len(chapters)} chapters"
    if cover:
        shape += f", opening on a cover: \"{cover if isinstance(cover, str) else spec.get('title')}\""
    out += [shape + ".", ""]
    notes = spec.get("notes") or []
    for i, title in enumerate(chapters, 1):
        out += [f"## {title}", ""]
        if i <= len(notes) and notes[i - 1]:
            out += [f"_Speaker notes: {notes[i - 1]}_", ""]
        for n, c in enumerate(clicks, 1):
            if not isinstance(c, dict) or c.get("chapter") != i:
                continue
            change = "The stage clears." if c.get("clear") else c.get("change", "(no change given)")
            out.append(f"{n}. {change}")
            out.append(f"   > {c['caption']}" if c.get("caption") else "   _(no caption: the picture says it)_")
        out.append("")
    return "\n".join(out)

# ---------------------------------------------------------------- headless Chrome

CHROME_PATHS = {
    "Darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
               "/Applications/Chromium.app/Contents/MacOS/Chromium",
               "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
    "Linux": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"],
    "Windows": [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"],
}
NO_BROWSER = "no headless Chrome found: install Google Chrome or Chromium, or set WALK_CHROME to one"


def find_chrome():
    """Path of a Chrome or Chromium: WALK_CHROME, then the usual places for this system."""
    if os.environ.get("WALK_CHROME"):
        return os.environ["WALK_CHROME"]
    for candidate in CHROME_PATHS.get(platform.system(), []):
        if "/" in candidate or "\\" in candidate:
            path = os.path.expanduser(candidate)
            if os.path.isfile(path):
                return path
        elif shutil.which(candidate):
            return shutil.which(candidate)
    return None


def chrome_args(chrome, size, extra, scale=1, budget=4000):
    # chrome-headless-shell only knows the old --headless; a full Chrome needs --headless=new.
    headless = "--headless" if "headless" in Path(chrome).name else "--headless=new"
    args = [chrome, headless, "--disable-gpu", "--hide-scrollbars", "--mute-audio", "--no-first-run",
            "--no-default-browser-check", "--disable-extensions", "--allow-file-access-from-files",
            f"--window-size={size[0]},{size[1]}", f"--force-device-scale-factor={scale}",
            f"--virtual-time-budget={budget}", "--run-all-compositor-stages-before-draw"]
    if platform.system() == "Linux":
        args.append("--no-sandbox")
    return args + extra


def run_chrome(chrome, size, url, extra, scale=1, budget=4000, timeout=60):
    """One headless run. New headless gives every process its own temporary profile, so runs can go in
    parallel. No --user-data-dir: with one, Chrome 153 in a container loaded the page and never exited
    (measured on 2026-11-09), which --headless=new without it does not do."""
    args = chrome_args(chrome, size, [*extra, url], scale, budget)
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", f"chrome did not finish in {timeout}s")


def page_url(out_dir, query="", fragment=""):
    page = Path(out_dir).resolve() / "page.html"
    if not page.exists():
        raise SystemExit(f"{page} does not exist")
    return page.as_uri() + (f"?{query}" if query else "") + (f"#{fragment}" if fragment else "")


_offset = {}


def dom_offset(chrome):
    """How much smaller than --window-size the page's viewport is under --dump-dom. Chrome 153 takes
    87 pixels of height for a window frame there (a screenshot resizes to the full size before it
    captures), so the checker asks for that much more to measure the size it means."""
    if chrome not in _offset:
        probe = "data:text/html,<script>document.write('<p id=v>'+innerWidth+'x'+innerHeight+'</p>')</script>"
        out = run_chrome(chrome, (1000, 1000), probe, ["--dump-dom"]).stdout
        found = re.search(r"id=\"?v\"?>(\d+)x(\d+)<", out)
        _offset[chrome] = (1000 - int(found.group(1)), 1000 - int(found.group(2))) if found else (0, 0)
    return _offset[chrome]


def check_report(chrome, out_dir, size):
    """The page's ?check report at one window size, or {'errors': [...]} when there is none."""
    dx, dy = dom_offset(chrome)
    result = run_chrome(chrome, (size[0] + dx, size[1] + dy), page_url(out_dir, "check"), ["--dump-dom"])
    found = re.search(r'<pre id="walk-report"[^>]*>(.*?)</pre>', result.stdout, re.S)
    if not found:
        tail = (result.stderr or "").strip().splitlines()[-1:] or ["no output"]
        return {"errors": [f"no report: the page did not run (chrome said: {tail[0][:160]})"]}
    return json.loads(html.unescape(found.group(1)))
