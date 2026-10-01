"""The pronunciation lint: words the voice is likely to say wrong, found before any audio exists.

The voice check can't catch these. A recogniser writes "A" whether the voice said the letter or
the article, and it spells an acronym the same way whether the voice read it out or tried to say
it as a word. So `studio narrate` runs Kokoro's own grapheme-to-phoneme step (misaki) over the
script first and reports three kinds of word, as they will actually be spoken:

  letter    a lone capital letter read as something other than its name. Kokoro reads "A" as the
            article ("uh"), which is right in "A unit test" and wrong in "A reads one".
  acronym   an all-caps word, with how it will be read (spelled out, or as one word): JSON is
            spelled out, SQL becomes "sequel". Listed once each, so the reading is a choice.
  unknown   a word missing from the lexicon, pronounced by a rule-based guess (espeak). Names and
            coined words land here: "rr" comes out as "ar-rar".
  word      an abbreviation written in lowercase that the lexicon knows as an ordinary word:
            "id" is read as the Freudian id ("ɪd"), "os" as "oss". Write it in capitals (ID), or
            respell it.

Each finding names the first sentence it occurs in and the fix: a `phonemes_by_id` entry for a
letter that names something, or a `phonemes` or `spoken` entry for a word. Findings never block
narration; the list goes to audio/pronunciation.txt and the console. It runs whichever engine
speaks, since the risky words are the same; it needs Kokoro's extra installed and says so if not.
"""
import re

LETTER = re.compile(r"(?<![\w'’])[A-HJ-Z](?![\w'’])")
ACRONYM = re.compile(r"(?<![\w'’])[A-Z][A-Z0-9]{1,6}s?(?![\w'’])")
WORD = re.compile(r"[A-Za-z][\w'’-]*")
# Abbreviations that misaki reads as an English word when written in lowercase (measured: "the id
# here" -> ˈɪd). Other lowercase abbreviations (url, api, json, cpu, ...) aren't in its lexicon at
# all and are reported as unknown.
AS_WORDS = {"id": "ID", "ids": "IDs", "os": "OS"}
# Each letter's name as misaki says it (measured on "Customer X reads one."); a lone letter whose
# phonemes differ was read as something else.
NAMES = dict(zip("ABCDEFGHJKLMNOPQRSTUVWXYZ",
                 ["ˈA", "bˈi", "sˈi", "dˈi", "ˈi", "ˈɛf", "ʤˈi", "ˈAʧ", "ʤˈA", "kˈA", "ˈɛl", "ˈɛm", "ˈɛn", "ˈO",
                  "pˈi", "kjˈu", "ˈɑɹ", "ˈɛs", "tˈi", "jˈu", "vˈi", "dˈʌbᵊlju", "ˈɛks", "wˈI", "zˈi"]))


def _g2p():
    try:
        from misaki import en, espeak
    except ImportError:
        return None, None
    plain = en.G2P(trf=False, british=False, fallback=None)
    try:
        guess = en.G2P(trf=False, british=False, fallback=espeak.EspeakFallback(british=False))
    except Exception:          # espeak missing: report unknown words without a guess
        guess = plain
    return plain, guess


def _tokens(g2p, text):
    _, toks = g2p(text)
    # misaki can keep a sentence's final period on its last word ("id."); None: not in the lexicon
    return [(t.text.rstrip(".,;:!?") or t.text, t.phonemes.strip() if t.phonemes else None) for t in toks]


def find(S, chapters, g2p=None):
    """[(kind, sentence id, word, how it will be said, fix)] in script order, each word once
    (a letter once per sentence, since whether it names something depends on the sentence)."""
    plain, guess = g2p or _g2p()
    if plain is None:
        return None
    out, seen = [], set()
    for _, _, sents in chapters:
        for lid, cap, _ in sents:
            text = S.spoken(cap, lid)
            fixed = S.phonemes_for(lid)
            toks = _tokens(plain, S.marked(text, lid))
            heard = {}
            for w, ph in toks:
                heard.setdefault(w, ph)
            for m in LETTER.finditer(text):
                w = m.group(0)
                ph = heard.get(w, "")
                if w not in fixed and ph and ph.replace("ˌ", "") != NAMES[w]:
                    out.append(("letter", lid, w, ph,
                                f'if "{w}" names something here: "phonemes_by_id": {{"{lid}": {{"{w}": "{NAMES[w]}"}}}}'))
            for m in ACRONYM.finditer(text):
                w = m.group(0)
                if w in fixed or ("acronym", w) in seen:
                    continue
                seen.add(("acronym", w))
                out.append(("acronym", lid, w, heard.get(w) or "?",
                            f'to change it: "phonemes": {{"{w}": "..."}} or "spoken": [["{w}", "..."]]'))
            for w, ph in toks:
                if w in AS_WORDS and w not in fixed and ("word", w) not in seen:
                    seen.add(("word", w))
                    out.append(("word", lid, w, ph or "?", f'write "{AS_WORDS[w]}", or "spoken": [["{w}", "eye dee"]]'
                                if w.startswith("id") else f'write "{AS_WORDS[w]}"'))
                if ph is None and WORD.fullmatch(w) and ("unknown", w) not in seen and w not in fixed:
                    seen.add(("unknown", w))
                    g = (dict(_tokens(guess, w)).get(w) or "?") if guess is not plain else "?"
                    out.append(("unknown", lid, w, g, f'if that is wrong: "phonemes": {{"{w}": "..."}}'))
    return out


def report(S, chapters):
    found = find(S, chapters)
    if found is None:
        print("pronunciation lint skipped: it needs Kokoro's extra (`studio doctor --fetch --extra kokoro`)")
        return None
    lines = [f"{kind:8} {lid:7} {w!r:14} said as /{ph}/   {fix}" for kind, lid, w, ph, fix in found]
    head = (f"pronunciation: {len(found)} word(s) to check before trusting the audio "
            "(a lone letter that names something, an acronym's reading, a word the lexicon lacks)")
    (S.audio / "pronunciation.txt").write_text("\n".join([head, *lines]) + "\n")
    print(head if found else "pronunciation: nothing to check")
    for ln in lines:
        print("  " + ln)
    return found
