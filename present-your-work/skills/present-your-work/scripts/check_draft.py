#!/usr/bin/env python3
"""Check a presentation draft against the present-your-work rules.

Reads a Markdown or HTML draft and checks its main text, which is everything before the appendix
without notes, references or a table of contents:

  words    the word count of the prose, tables left out, against the size's range (ten percent
           either side passes);
  terms    new terms against the size's budget;
  numbers  distinct numerals, tables included, against the size's budget;
  labels   no internal labels: the glossary's labels, tokens that mix letters and digits (dev40,
           B8), snake_case and camelCase identifiers, file names and paths, and acronyms that are
           neither common, nor listed as known, nor defined in the draft;
  order    no term used before the draft defines it, including a term defined only in the appendix.

It prints a short report and exits 0 when every rule holds, 1 when one is broken, 2 on a usage
error. Standard library only.

What the draft does so the script can see it:
  - A new term is marked where it is defined: <dfn>, or a short italic or bold span (*term*,
    **term**, <em>, <i>, <strong>, <b>); a glossary's <dt> also defines its terms. An acronym is
    defined as "long form (ABC)".
  - The appendix starts at a heading that begins with "Appendix", a heading whose id begins with
    "app-" or "appendix", or the comment <!-- appendix -->.
  - Quantities the reader must weigh are written as numerals; counts that structure the text
    (three results, two readings) are spelled out. Years, dates, citation brackets and references
    such as "Section 4" or "Figure 2" are not counted.
"""
from __future__ import annotations

import argparse
import html.parser
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SIZES = {
    "small": {"words": (150, 300), "terms": 2, "numbers": 3},
    "medium": {"words": (600, 900), "terms": 5, "numbers": 8},
    "large": {"words": (2500, 4000), "terms": 10, "numbers": 25},
}
WORD_TOLERANCE = 0.10

RULES = {
    "words": "words in the main text",
    "terms": "new terms in the main text",
    "numbers": "numbers in the main text",
    "labels": "internal labels in the main text",
    "order": "terms used before their definition",
}

BACK_MATTER = {
    "notes", "footnotes", "endnotes", "references", "bibliography", "works cited", "sources",
    "acknowledgements", "acknowledgments", "contents", "table of contents",
}

COMMON_ACRONYMS = {
    "AI", "AM", "API", "BBC", "CEO", "CPU", "CSV", "DNA", "DVD", "EU", "FAQ", "FIFA", "GDP", "GPS",
    "GPU", "HD", "HTML", "ID", "IT", "MIT", "NASA", "NBA", "NFL", "NHS", "OK", "PC", "PDF", "PM",
    "RAM", "SMS", "SQL", "TV", "UEFA", "UK", "UN", "URL", "US", "USA", "USB", "UTC", "VAR", "VR",
    "WHO",
}
COMMON_MIXED = {
    "2D", "3D", "4K", "8K", "A4", "B2B", "B2C", "CO2", "COVID-19", "H.264", "MP3", "MP4", "P2P",
    "eBay", "iCloud", "iOS", "iPad", "iPhone", "macOS",
}

MARK_OPEN, MARK_CLOSE = "\x01", "\x02"


# ---------------------------------------------------------------------------------------------
# Reading the draft into blocks


@dataclass
class Block:
    kind: str  # heading, text, cell, code, figure, marker
    text: str = ""
    level: int = 0
    hid: str = ""
    marks: list = field(default_factory=list)  # (start, end) of each marked span in text
    start: int = 0  # offset of the block in the whole document
    section: int = 0


def finish(raw: str) -> tuple[str, list]:
    """Collapse whitespace and turn the mark sentinels into (start, end) spans."""
    raw = re.sub(r"[\s   ]+", " ", raw).strip()
    out, marks, stack = [], [], []
    for ch in raw:
        if ch == MARK_OPEN:
            stack.append(len(out))
        elif ch == MARK_CLOSE:
            if stack:
                marks.append((stack.pop(), len(out)))
        else:
            out.append(ch)
    text = "".join(out)
    spans = []
    for s, e in marks:
        while s < e and text[s] == " ":
            s += 1
        while e > s and text[e - 1] == " ":
            e -= 1
        if e > s:
            spans.append((s, e))
    return text, sorted(set(spans))


class HTMLDraft(html.parser.HTMLParser):
    SKIP = {"script", "style", "nav", "math", "template", "noscript", "head", "title", "button"}
    BLOCK = {
        "p", "li", "dt", "dd", "td", "th", "figcaption", "caption", "blockquote", "div", "section",
        "article", "header", "footer", "main", "aside", "table", "tr", "ul", "ol", "dl", "figure",
        "body", "hr", "details", "summary",
    }
    HEADINGS = {f"h{i}": i for i in range(1, 7)}
    MARKS = {"dfn", "em", "i", "strong", "b"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block] = []
        self.buf: list[str] = []
        self.fig: list[str] = []
        self.capture: list[list] = []  # [tag, parts] for <sup> and in-page links
        self.skip = 0
        self.svg = 0
        self.pre = 0
        self.cell = 0
        self.heading: tuple[int, str] | None = None
        self.hidden: list | None = None  # [tag, depth] of an element the reader does not see
        self.boundary = False  # an inline element just opened or closed

    def emit(self, s: str) -> None:
        (self.capture[-1][1] if self.capture else self.buf).append(s)

    def last_char(self) -> str:
        for part in reversed((self.capture[-1][1] if self.capture else []) + self.buf):
            text = part.replace(MARK_OPEN, "").replace(MARK_CLOSE, "")
            if text:
                return text[-1]
        return " "

    def flush(self) -> None:
        self.capture = []
        text, marks = finish("".join(self.buf))
        self.buf = []
        if not text:
            return
        if self.heading:
            self.blocks.append(Block("heading", text, self.heading[0], self.heading[1], marks))
        else:
            kind = "code" if self.pre else "cell" if self.cell else "text"
            self.blocks.append(Block(kind, text, marks=marks))

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.hidden:
            self.hidden[1] += tag == self.hidden[0]
            return
        invisible = "hidden" in a or re.search(r"display\s*:\s*none", a.get("style") or "")
        if invisible and tag not in self.VOID:
            self.hidden = [tag, 1]
            return
        self.boundary = True
        if tag in self.SKIP:
            self.flush()
            self.skip += 1
            return
        if self.skip:
            return
        if tag == "svg":
            self.svg += 1
            return
        if self.svg:
            return
        if tag in self.HEADINGS:
            self.flush()
            self.heading = (self.HEADINGS[tag], a.get("id") or "")
        elif tag == "pre":
            self.flush()
            self.pre += 1
        elif tag in self.BLOCK:
            self.flush()
            self.cell += tag in ("td", "th")
            if tag == "dt":
                self.buf.append(MARK_OPEN)
        elif tag == "br":
            self.emit(" ")
        elif tag in self.MARKS:
            self.emit(MARK_OPEN)
        elif tag == "sup" or (tag == "a" and (a.get("href") or "").startswith("#")):
            self.capture.append([tag, []])

    def handle_endtag(self, tag):
        if self.hidden:
            if tag == self.hidden[0]:
                self.hidden[1] -= 1
                if not self.hidden[1]:
                    self.hidden = None
            return
        self.boundary = True
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag == "svg":
            self.svg = max(0, self.svg - 1)
            if not self.svg:
                text, _ = finish(" ".join(self.fig))
                self.fig = []
                if text:
                    self.blocks.append(Block("figure", text))
            return
        if self.svg:
            return
        if tag in self.HEADINGS:
            self.flush()
            self.heading = None
        elif tag == "pre":
            self.flush()
            self.pre = max(0, self.pre - 1)
        elif tag in self.BLOCK:
            if tag == "dt":
                self.buf.append(MARK_CLOSE)
            self.flush()
            if tag in ("td", "th"):
                self.cell = max(0, self.cell - 1)
        elif tag in self.MARKS:
            self.emit(MARK_CLOSE)
        elif self.capture and self.capture[-1][0] == tag:
            _, parts = self.capture.pop()
            text = "".join(parts)
            if not re.fullmatch(r"[\s\d,\[\]()–-]*", text):  # drop footnote markers
                self.emit(text)

    def handle_data(self, data):
        if self.skip or self.hidden:
            return
        if self.svg:
            self.fig.append(data)
            return
        # A run-in head styled as a block ("<span>Touch and event</span>This paper") reads as two words.
        if self.boundary and data[:1].isupper() and (self.last_char().isalnum() or self.last_char() in ".:;)"):
            self.emit(" ")
        self.boundary = False
        self.emit(data)

    def handle_comment(self, data):
        if re.fullmatch(r"\s*appendix\s*", data, re.I):
            self.flush()
            self.blocks.append(Block("marker"))

    def close(self):
        super().close()
        self.flush()


def md_inline(s: str) -> str:
    """Markdown inline syntax to plain text, with sentinels around marked spans."""
    s = re.sub(r"<!--.*?-->", "", s)
    codes: list[str] = []

    def keep_code(m):
        codes.append(m.group(1))
        return f"\x03{len(codes) - 1}\x03"

    s = re.sub(r"`+([^`]+)`+", keep_code, s)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"\[\^[^\]]+\]", "", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", s)
    s = re.sub(r"<(dfn|em|i|strong|b)>(.*?)</\1>", MARK_OPEN + r"\2" + MARK_CLOSE, s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\*\*(?!\s)(.+?)(?<!\s)\*\*", MARK_OPEN + r"\1" + MARK_CLOSE, s)
    s = re.sub(r"(?<![\w_])__(?!\s)(.+?)(?<!\s)__(?![\w_])", MARK_OPEN + r"\1" + MARK_CLOSE, s)
    s = re.sub(r"(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])", MARK_OPEN + r"\1" + MARK_CLOSE, s)
    s = re.sub(r"(?<![\w_])_(?![\s_])(.+?)(?<![\s_])_(?![\w_])", MARK_OPEN + r"\1" + MARK_CLOSE, s)
    s = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|])", r"\1", s)
    return re.sub(r"\x03(\d+)\x03", lambda m: codes[int(m.group(1))], s)


def parse_markdown(src: str) -> list[Block]:
    blocks: list[Block] = []
    lines = src.splitlines()
    if lines and lines[0].strip() == "---":  # front matter
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), 0)
        lines = lines[end + 1:]
    para: list[str] = []
    fence = None
    code: list[str] = []

    def flush():
        if para:
            text, marks = finish(md_inline(" ".join(para)))
            if text:
                blocks.append(Block("text", text, marks=marks))
            para.clear()

    for line in lines:
        stripped = line.strip()
        if fence:
            if stripped.startswith(fence):
                text, _ = finish(" ".join(code))
                if text:
                    blocks.append(Block("code", text))
                fence, code = None, []
            else:
                code.append(line)
            continue
        if re.match(r"(```|~~~)", stripped):
            flush()
            fence = stripped[:3]
            continue
        if re.fullmatch(r"<!--\s*appendix\s*-->", stripped, re.I):
            flush()
            blocks.append(Block("marker"))
            continue
        m = re.match(r"(#{1,6})\s+(.*?)\s*#*\s*$", stripped)
        if m:
            flush()
            title, hid = m.group(2), ""
            idm = re.search(r"\s*\{#([^}]+)\}\s*$", title)
            if idm:
                title, hid = title[: idm.start()], idm.group(1)
            text, marks = finish(md_inline(title))
            blocks.append(Block("heading", text, len(m.group(1)), hid, marks))
            continue
        if not stripped or re.fullmatch(r"([-*_])( ?\1){2,}", stripped):
            flush()
            continue
        if re.match(r"\[\^[^\]]+\]:", stripped):  # a footnote's text is back matter
            flush()
            continue
        if stripped.startswith("|"):
            flush()
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            text, _ = finish(md_inline("; ".join(cells)))
            if text:
                blocks.append(Block("cell", text))
            continue
        item = re.match(r"([-*+]|\d+[.)])\s+(.*)", stripped)
        if item:
            flush()
            para.append(item.group(2))
            continue
        para.append(re.sub(r"^(>\s?)+", "", stripped))
    flush()
    return blocks


def load(path: Path) -> list[Block]:
    src = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".html", ".htm"} or re.match(r"\s*<(!doctype|html)", src, re.I):
        parser = HTMLDraft()
        parser.feed(src)
        parser.close()
        return parser.blocks
    return parse_markdown(src)


# ---------------------------------------------------------------------------------------------
# Sections and zones


@dataclass
class Section:
    title: str
    zone: str  # main, appendix, back


def heading_name(text: str) -> str:
    return re.sub(r"^\s*(?:\d+(?:\.\d+)*|[A-Z])[.):]?\s+", "", text).strip().lower()


def is_appendix_heading(b: Block) -> bool:
    return bool(
        re.match(r"(?:[A-Z][.:)]?\s*)?appendi(x|ces)\b", b.text.strip(), re.I)
        or re.match(r"(appendix|app[-_:\d])", b.hid, re.I)
    )


def sectionize(blocks: list[Block]) -> list[Section]:
    levels = [b.level for b in blocks if b.kind == "heading"]
    top, title_index = (min(levels) if levels else 1), -1
    if levels and levels.count(top) == 1 and len(set(levels)) > 1:
        title_index = next(i for i, b in enumerate(blocks) if b.kind == "heading" and b.level == top)
        top = min(level for level in levels if level > top)
    sections = [Section("(opening)", "main")]
    zone = "main"
    pos = 0
    for i, b in enumerate(blocks):
        if b.kind == "marker":
            zone = "appendix"
            sections.append(Section("(appendix)", "appendix"))
        elif b.kind == "heading" and b.level <= top and i != title_index:
            if is_appendix_heading(b):
                zone = "appendix"
            back = heading_name(b.text) in BACK_MATTER
            sections.append(Section(b.text, "back" if back else zone))
        b.section = len(sections) - 1
        b.start = pos
        pos += len(b.text) + 1
    return sections


# ---------------------------------------------------------------------------------------------
# What the checks look for

WORD_RE = re.compile(r"[^\W_]+(?:['’.\-][^\W_]+)*")
UNITS = r"(?:ms|min|hrs?|km|cm|mm|kg|GB|MB|KB|TB|fps|kHz|MHz|GHz|Hz|px|bn|pp|s|h|d|m|g|p|x|k|K|M|B)"
NUM_RE = re.compile(
    r"(?<![\w.,/\-−])"
    r"(?:\d{1,2}:\d{2}(?::\d{2})?|[-−+]?\d+(?:,\d{3})*(?:\.\d+)?)"
    r"(?:\s?%|\s?percent\b|" + UNITS + r"(?![\w]))?"
    r"(?![\w]|[.,]\d|-\d)"
)
NUM_REFERENCE = re.compile(
    r"(?:sections?|sec\.|§|figures?|fig\.|tables?|appendix|appendices|chapters?|equations?"
    r"|eq\.|steps?|parts?|pages?|pp?\.|notes?|footnotes?|items?|no\.|#)\s*$",
    re.I,
)
LABEL_FINDERS = [
    ("file name or path", re.compile(
        r"(?<![\w/:])(?:[\w.-]+/)*[\w-]+\.(?:py|ipynb|json|jsonl|md|csv|tsv|sqlite|db|duckdb|parquet"
        r"|html|yaml|yml|toml|txt|sh|js|ts|tsx|log|pt|onnx|pkl)(?![\w])"
        r"|(?<![\w/:.])(?:[\w.-]+/){2,}[\w.-]*")),
    ("letters and digits", re.compile(
        r"(?<![\w-])(?=[\w.-]*[A-Za-z])(?=[\w.-]*\d)[A-Za-z0-9]+(?:[-_.][A-Za-z0-9]+)*(?![\w-])")),
    ("snake_case", re.compile(r"(?<![\w-])[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+(?![\w-])")),
    ("camelCase", re.compile(r"(?<![\w-])[a-z]+[A-Z][A-Za-z0-9]*(?![\w-])")),
    ("acronym", re.compile(r"(?<![\w-])[A-Z]{2,}(?=s?(?![\w]))")),
]
NOT_A_LABEL = re.compile(
    r"\d+(?:[.,]\d+)?" + UNITS + r"|\d+(?:st|nd|rd|th)|\d{4}[a-z]|\d+(?:[.,]\d+)?(?:-[a-z]+)+",
)
ACRONYM_DEFS = [
    re.compile(r"\(([A-Z]{2,})s?\)"),  # long form (ABC)
    re.compile(r"\b([A-Z]{2,})s?\s+\((?!\d)[^)]{4,}\)"),  # ABC (long form)
]
ROMAN = re.compile(r"[IVXLC]+")


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def find_numbers(text: str) -> list[str]:
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", text)
    text = re.sub(r"\[\d+(?:\s*[,–-]\s*\d+)*\]", " ", text)
    text = re.sub(r"\((?:\d{1,2}|[ivx]{1,4}|[a-h])\)", " ", text)
    found = []
    for m in NUM_RE.finditer(text):
        raw = m.group(0)
        if NUM_REFERENCE.search(text[max(0, m.start() - 14): m.start()]):
            continue
        if re.fullmatch(r"(?:1[5-9]|20)\d{2}", raw):
            continue
        key = raw.replace("−", "-").replace(",", "").replace(" ", "").replace("percent", "%")
        found.append(key)
    return found


def singular(word: str) -> str:
    if len(word) <= 3 or word.endswith("ss") or not word.endswith("s"):
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if re.search(r"(ch|sh|x|ss)es$", word):
        return word[:-2]
    return word[:-1]


def term_key(t: str) -> str:
    """A term's key: lower case, without a leading article, its last word singular."""
    t = re.sub(r"\s+", " ", t.strip(" \"'“”‘’()[]:;,.")).lower()
    words = re.sub(r"^(the|a|an) ", "", t).split(" ")
    return " ".join(words[:-1] + [singular(words[-1])])


def valid_term(raw: str) -> bool:
    raw = raw.strip()
    if not raw or raw[-1] in ".!?:" or not re.search(r"[A-Za-z]", raw):
        return False
    if re.match(r"(table|figure|fig\.|note|step|source|see)\b", raw, re.I):
        return False
    return 1 <= len(raw.split()) <= 5 and 2 <= len(raw) <= 60


def term_pattern(key: str, acronym: bool) -> re.Pattern:
    """Matches the term and its plural; the key's last word is already singular."""
    words = key.split()
    last = words[-1]
    if acronym:
        last = re.escape(last) + "s?"
    elif last.endswith("y") and len(last) > 2:
        last = re.escape(last[:-1]) + "(?:y|ies)"
    else:
        last = re.escape(last) + "(?:s|es)?"
    body = r"\s+".join([re.escape(w) for w in words[:-1]] + [last])
    return re.compile(r"(?<![\w-])" + body + r"(?![\w-])", 0 if acronym else re.I)


def read_list(path: Path) -> list[str]:
    """Labels from a GLOSSARY.md (first column of a table, or the head of a list item), or one
    term per line from a plain file. Several labels in one cell are separated by commas."""
    labels: list[str] = []
    rows = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(rows):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            nxt = rows[i + 1].strip() if i + 1 < len(rows) else ""
            if re.fullmatch(r"\|?\s*:?-{2,}.*", nxt):
                continue  # the header row
            head = cells[0]
        elif re.match(r"[-*+]\s+", s):
            head = re.split(r"\s*(?::|—|–| - )\s+", re.sub(r"^[-*+]\s+", "", s), maxsplit=1)[0]
        elif path.suffix.lower() == ".md":
            continue
        else:
            head = s
        head = re.sub(r"[`*_]", "", head)
        labels += [p.strip() for p in re.split(r"\s*[,;]\s*", head) if p.strip()]
    return labels


# ---------------------------------------------------------------------------------------------
# The analysis


@dataclass
class Result:
    size: str
    sections: list
    stats: dict  # section index -> {"words", "terms", "numbers", "labels"}
    words: int
    terms: dict  # key -> (display, section index)
    numbers: set
    labels: dict  # label -> {"kind", "uses", "section", "figure"}
    order: list  # (display, first-use section, definition section or None, definition zone)
    other_words: int
    other_sections: int
    failures: list


def analyse(blocks: list[Block], size: str, glossary=(), known=()) -> Result:
    sections = sectionize(blocks)
    budget = SIZES[size]
    known_cf = {k.casefold() for k in known}
    main = [b for b in blocks if sections[b.section].zone == "main"]
    body = [b for b in main if b.kind in ("text", "cell")]

    # Definitions anywhere outside the back matter, the first one per term.
    defs: dict[str, tuple] = {}  # key -> (pos, section, zone, display, acronym)
    for b in blocks:
        zone = sections[b.section].zone
        if zone == "back" or b.kind != "text":
            continue
        found = []
        for s, e in b.marks:
            full = b.text[s:e]
            if full[-1] in ".!?" or (s == 0 and b.text[e:e + 1] == "."):
                continue  # a run-in heading, not a term
            full = re.sub(r"\([^)]*\)", lambda m: " " * len(m.group(0)), full)
            for piece in re.finditer(r"[^,;]+", full):
                if valid_term(piece.group(0)):
                    found.append((b.start + s + piece.start(), term_key(piece.group(0)),
                                  piece.group(0).strip(), False))
        for rx in ACRONYM_DEFS:
            for m in rx.finditer(b.text):
                found.append((b.start + m.start(), m.group(1), m.group(1), True))
        for pos, key, display, acronym in found:
            if key and (key not in defs or pos < defs[key][0]):
                defs[key] = (pos, b.section, zone, display, acronym)

    # New terms: first defined in the main text and not known to the reader.
    terms = {k: (d[3], d[1]) for k, d in defs.items() if d[2] == "main" and k.casefold() not in known_cf}

    # Terms used before their definition, or in the main text and defined only in the appendix.
    order = []
    for key, (pos, sec, zone, display, acronym) in sorted(defs.items(), key=lambda kv: kv[1][0]):
        if key.casefold() in known_cf:
            continue
        rx = term_pattern(key, acronym)
        for b in body:
            if zone == "main" and b.start >= pos:
                continue
            m = rx.search(b.text)
            if m and (zone != "main" or b.start + m.start() < pos):
                order.append((display, b.section, sec, zone))
                break

    # Internal labels in the main text, headings and figures included.
    labels: dict[str, dict] = {}
    acronyms_defined = {k for k, d in defs.items() if d[4]}
    gloss = [(g, re.compile(r"(?<![\w-])" + re.escape(g) + r"(?![\w-])", re.I)) for g in glossary if g]

    def note(label, kind, b):
        info = labels.setdefault(label, {"kind": kind, "uses": 0, "section": b.section, "figure": False})
        info["uses"] += 1
        info["figure"] |= b.kind == "figure"

    for b in main:
        if b.kind == "marker":
            continue
        text = b.text
        for g, rx in gloss:
            for m in rx.finditer(text):
                note(g, "glossary", b)
            text = rx.sub(lambda m: " " * len(m.group(0)), text)
        letters = re.sub(r"[^A-Za-z]", "", text)
        shouting = len(text.split()) >= 3 and letters and sum(c.isupper() for c in letters) / len(letters) > 0.6
        for kind, rx in LABEL_FINDERS:
            for m in rx.finditer(text):
                tok = m.group(0).rstrip(".")
                if tok.casefold() in known_cf or tok in COMMON_MIXED or NOT_A_LABEL.fullmatch(tok):
                    continue
                if kind == "acronym" and (shouting or tok in COMMON_ACRONYMS or tok in acronyms_defined
                                          or ROMAN.fullmatch(tok)):
                    continue
                note(tok, kind, b)
            text = rx.sub(lambda m: " " * len(m.group(0)), text)

    # Per-section counts.
    stats: dict[int, dict] = {}
    for b in main:
        st = stats.setdefault(b.section, {"words": 0, "terms": 0, "numbers": set(), "labels": set()})
        if b.kind in ("text", "code"):
            st["words"] += count_words(b.text)
        if b.kind in ("text", "cell"):
            st["numbers"].update(find_numbers(b.text))
    for key, (_, sec) in terms.items():
        stats.setdefault(sec, {"words": 0, "terms": 0, "numbers": set(), "labels": set()})["terms"] += 1
    for label, info in labels.items():
        stats[info["section"]]["labels"].add(label)
    numbers = set().union(*(st["numbers"] for st in stats.values())) if stats else set()
    words = sum(st["words"] for st in stats.values())

    rest = [b for b in blocks if sections[b.section].zone != "main" and b.kind in ("text", "cell", "code")]
    other_sections = len({b.section for b in rest})

    lo, hi = budget["words"]
    failures = []
    if not lo * (1 - WORD_TOLERANCE) <= words <= hi * (1 + WORD_TOLERANCE):
        failures.append("words")
    if len(terms) > budget["terms"]:
        failures.append("terms")
    if len(numbers) > budget["numbers"]:
        failures.append("numbers")
    if labels:
        failures.append("labels")
    if order:
        failures.append("order")
    return Result(size, sections, stats, words, terms, numbers, labels, order,
                  sum(count_words(b.text) for b in rest), other_sections, failures)


# ---------------------------------------------------------------------------------------------
# The report


def short(title: str, n: int = 34) -> str:
    return title if len(title) <= n else title[: n - 1] + "…"


def render(r: Result, path: Path, list_all: bool = False, limit: int = 12) -> str:
    budget = SIZES[r.size]
    lo, hi = budget["words"]
    out = [f"present-your-work check: {path.name}, size {r.size}", ""]

    def status(rule):
        return "FAIL" if rule in r.failures else "ok  "

    out.append(f"  {status('words')}  {RULES['words']}: {r.words:,} (range {lo:,} to {hi:,}; "
               f"{int(lo * (1 - WORD_TOLERANCE)):,} to {int(hi * (1 + WORD_TOLERANCE)):,} passes)")
    out.append(f"  {status('terms')}  {RULES['terms']}: {len(r.terms)} (budget {budget['terms']})")
    out.append(f"  {status('numbers')}  {RULES['numbers']}: {len(r.numbers)} distinct (budget {budget['numbers']})")
    out.append(f"  {status('labels')}  {RULES['labels']}: {len(r.labels)} distinct")
    out.append(f"  {status('order')}  {RULES['order']}: {len(r.order)}")
    out.append("")
    out.append(f"  {'Main-text section':<34} {'words':>6} {'terms':>6} {'numbers':>8} {'labels':>7}")
    for sec in sorted(r.stats):
        st = r.stats[sec]
        out.append(f"  {short(r.sections[sec].title):<34} {st['words']:>6,} {st['terms']:>6} "
                   f"{len(st['numbers']):>8} {len(st['labels']):>7}")
    if r.other_sections:
        out.append(f"  Appendix and back matter: {r.other_words:,} words in {r.other_sections} "
                   f"sections, not budgeted.")

    def capped(lines):
        if list_all or len(lines) <= limit:
            return lines
        return lines[:limit] + [f"    and {len(lines) - limit} more (--all lists them)"]

    if r.labels:
        out += ["", "  Internal labels (uses in the main text, first section, why flagged):"]
        rows = sorted(r.labels.items(), key=lambda kv: (-kv[1]["uses"], kv[0].lower()))
        out += capped([
            f"    {short(label, 24):<24} {info['uses']:>4}  {short(r.sections[info['section']].title, 26):<26} "
            f"{info['kind']}{', in a figure' if info['figure'] else ''}"
            for label, info in rows
        ])
    if r.order:
        out += ["", "  Terms used before their definition:"]
        lines = []
        for display, used, defined, zone in r.order:
            where = (f"defined later in {r.sections[defined].title}" if zone == "main"
                     else f"defined only in the {zone if zone != 'back' else 'back matter'} "
                          f"({r.sections[defined].title})")
            lines.append(f"    \"{display}\": used in {short(r.sections[used].title, 30)}, {where}")
        out += capped(lines)
    if "terms" in r.failures:
        out += ["", "  New terms by section:"]
        by_sec: dict[int, list] = {}
        for display, sec in r.terms.values():
            by_sec.setdefault(sec, []).append(display)
        out += capped([f"    {short(r.sections[s].title, 30)}: {', '.join(v)}" for s, v in sorted(by_sec.items())])
    out += ["", f"  {len(r.failures)} of {len(RULES)} rules broken." if r.failures else "  Every rule holds."]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check a presentation draft against the present-your-work rules.")
    ap.add_argument("draft", type=Path, help="the draft, Markdown or HTML")
    ap.add_argument("--size", required=True, choices=sorted(SIZES), help="the presentation's size")
    ap.add_argument("--glossary", type=Path, action="append", default=[],
                    help="a GLOSSARY.md whose labels must not appear in the main text (repeatable)")
    ap.add_argument("--known", action="append", default=[],
                    help="a term or acronym the reader already knows (repeatable)")
    ap.add_argument("--known-file", type=Path, action="append", default=[],
                    help="a file of known terms, one per line, or a Markdown table or list")
    ap.add_argument("--all", action="store_true", help="list every finding, not the first twelve")
    args = ap.parse_args(argv)

    for p in [args.draft, *args.glossary, *args.known_file]:
        if not p.is_file():
            print(f"check_draft: no such file: {p}", file=sys.stderr)
            return 2
    glossary = [g for p in args.glossary for g in read_list(p)]
    known = list(args.known) + [k for p in args.known_file for k in read_list(p)]
    result = analyse(load(args.draft), args.size, glossary, known)
    print(render(result, args.draft, args.all))
    return 1 if result.failures else 0


if __name__ == "__main__":
    sys.exit(main())
