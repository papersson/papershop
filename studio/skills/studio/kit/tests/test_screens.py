"""The screens layer: one log of what happens on a film's desktops, replayed to every window's state, its
sounds and its check (engines/live/src/screens.js, screens-draw.js, pages.js; studio_kit/screens.py)."""
import hashlib
import json
import subprocess

from studio_kit import screens
from studio_kit import timeline as tl
from studio_kit.engine import Engine
from studio_kit.env import engine_dir
from test_live_engine import needs_engine

SRC = engine_dir("live") / "src"

# Two sentences with a hold between them (1.6 to 2.4 s), then one more from 2.4 s.
NARRATION = [
    {"id": "s1_01", "clip": "s1", "text": "Keys and values.", "caption": "Keys and values.", "paragraph": 0, "start": 0.3, "end": 1.6,
     "words": [{"w": "Keys", "start": 0.3, "end": 0.6}, {"w": "and", "start": 0.6, "end": 0.8}, {"w": "values.", "start": 0.8, "end": 1.6}]},
    {"id": "s1_02", "clip": "s1", "text": "Then the servers.", "caption": "Then the servers.", "paragraph": 0, "start": 2.4, "end": 3.6,
     "words": [{"w": "Then", "start": 2.4, "end": 2.6}, {"w": "the", "start": 2.6, "end": 2.8}, {"w": "servers.", "start": 2.8, "end": 3.6}]},
]
CUES = {"type-ls": 0.2, "edit": 0.4, "save": 1.55, "click": 1.0, "switch": 1.5, "tab": 2.8, "late": 3.0}
SPEC = {
    "seed": "test",
    "desktops": [
        {"id": "laptop", "kind": "editor", "plate": "laptop", "frame": [0, 0, .6, 1], "grow": True, "title": "shop — editor",
         "files": {"shop.py": "def reserve(cart):\n    for sku in cart:\n        stock.take(sku)\n"}, "panel": {"rows": 4}},
        {"id": "shop", "kind": "browser", "plate": "laptop", "frame": [.6, 0, .4, 1], "light": True,
         "tabs": [{"id": "shop", "title": "Shop", "url": "localhost:8000", "page": "basket"}]},
        {"id": "servers", "kind": "terminal", "arrive": "switch", "size": 36,
         "tabs": [{"id": "one", "title": "tea@one", "prompt": "tea@one:~$ "}]},
    ],
    "runs": {"ls": {"argv": ["ls"], "stdout": "shop.log  shop.py\n", "stderr": "", "exit": 0}},
    "actions": [
        {"at": "type-ls", "on": "laptop", "type": "ls", "run": "ls"},
        {"at": "edit", "on": "laptop", "edit": {"file": "shop.py", "line": 2, "indent": 8, "text": "print(\"here\")"}},
        {"at": "save", "on": "laptop", "save": True},
        {"at": "click", "on": "shop", "click": "checkout", "page": "placed"},
        {"at": "switch", "switch": "servers"},
        {"at": "tab", "on": "servers", "tab": "two", "new": {"title": "tea@two", "prompt": "tea@two:~$ "}},
        {"at": "late", "on": "servers", "type": "grep 1004 shop.log", "output": ["start checkout 1004"], "returns": False},
    ],
}


def timeline(duration=4.0):
    return {"version": 1, "fps": 30, "duration": duration, "cues": dict(CUES),
            "tracks": {"scene": [{"id": "s1", "engine": "live", "title": "One", "start": 0.0, "end": duration}],
                       "narration": NARRATION, "captions": tl.chunk_captions(NARRATION), "audio": []}}


def node(body, **values):
    head = "".join(f"const {k}={json.dumps(v)};" for k, v in values.items())
    script = (f"import * as m from {json.dumps((SRC / 'screens.js').as_uri())};"
              f"import * as d from {json.dumps((SRC / 'screens-draw.js').as_uri())};{head}"
              f"console.log(JSON.stringify(await (async()=>{{{body}}})()));")
    return json.loads(subprocess.check_output(["node", "--input-type=module", "-e", script], text=True))


def test_typing_rhythm_is_seeded_and_never_reads_as_autotype():
    r = node("const a=m.keyTimes('grep 1004 shop.log','s'),b=m.keyTimes('grep 1004 shop.log','s'),"
             "c=m.keyTimes('grep 1004 shop.log','other'),fast=m.keyTimes('x'.repeat(40),'s',{speed:6});"
             "return {same:JSON.stringify(a)===JSON.stringify(b),differ:JSON.stringify(a)!==JSON.stringify(c),"
             "rate:(fast.length-1)/(fast.at(-1)-fast[0]),max:m.MAX_KEYS}")
    assert r["same"] and r["differ"]
    assert r["rate"] <= r["max"] + 1e-6


def test_a_switch_moves_into_the_gap_between_sentences_or_says_it_cannot():
    T = timeline()
    r = node("const spans=m.spoken(T);return {inside:m.snapSwitch(1.0,.3,spans),gap:m.snapSwitch(1.65,.3,spans),"
             "none:m.snapSwitch(3.0,.3,spans,.2)}", T=T)
    assert r["gap"] == {"t": 1.65, "ok": True}                      # already clear: the slide and its settle fit the hold
    assert r["inside"]["ok"] and 1.6 <= r["inside"]["t"] and r["inside"]["t"] + .3 + .3 <= 2.4
    assert r["none"]["ok"] is False                                 # mid-sentence, nothing within reach


def test_state_replays_terminal_editor_browser_tabs_and_switches():
    T = timeline(5.0)
    r = node("const k=m.compile(S,T,S.runs);const at=t=>m.state(k,t);"
             "const pick=s=>({cur:s.current,slide:s.slide,present:s.present,panel:s.desks.laptop.panel.lines.map(l=>l.text),"
             "input:s.desks.laptop.panel.input,file:s.desks.laptop.files['shop.py'],dirty:s.desks.laptop.dirty['shop.py']??false,"
             "page:s.desks.shop.tabs[0].page,tabs:s.desks.servers.tabs.map(x=>x.id),active:s.desks.servers.active,"
             "srv:s.desks.servers.tabs[s.desks.servers.active].lines.map(l=>l.text),running:!!s.desks.servers.tabs[s.desks.servers.active].running});"
             "const sw=m.switches(k)[0];"
             "return {t0:pick(at(.25)),t1:pick(at(1.1)),t2:pick(at(1.7)),mid:pick(at(sw.t+sw.ms/2)),end:pick(at(4.9)),sw}", S=SPEC, T=T)
    assert r["t0"]["panel"] == [] and r["t0"]["input"] == ""                 # the first key is still to come
    assert r["t1"]["panel"] == ["ls", "shop.log  shop.py"]                  # Enter, then the captured output
    assert r["t1"]["file"][2].startswith("        print(") and r["t1"]["dirty"]
    assert r["t1"]["page"] == "placed"                                      # the click changed the page
    assert r["t2"]["file"][2] == '        print("here")' and not r["t2"]["dirty"]   # saved
    assert r["t0"]["present"] == ["laptop"] and r["end"]["present"] == ["laptop", "servers"]
    assert r["mid"]["slide"]["from"] == "laptop" and r["mid"]["slide"]["to"] == "servers"
    assert r["end"]["cur"] == "servers" and r["end"]["tabs"] == ["one", "two"] and r["end"]["active"] == 1
    assert r["end"]["srv"] == ["grep 1004 shop.log", "start checkout 1004"] and r["end"]["running"]
    assert r["sw"]["gap"] and 1.6 <= r["sw"]["t"] - .08


def test_an_edit_deletes_lines_at_once_with_one_key():
    spec = json.loads(json.dumps(SPEC))
    spec["actions"][1] = {"at": "edit", "on": "laptop", "edit": {"file": "shop.py", "line": 2, "mode": "delete", "count": 2}}
    r = node("const k=m.compile(S,T,S.runs);const f=t=>m.state(k,t).desks.laptop.files['shop.py'];"
             "return {before:f(.35),after:f(.45),sounds:k.actions[1].sounds}", S=spec, T=timeline(5.0))
    assert r["before"] == ["def reserve(cart):", "    for sku in cart:", "        stock.take(sku)"]
    assert r["after"] == ["def reserve(cart):"]
    assert len(r["sounds"]) == 1 and r["sounds"][0][1] == "key"


def test_the_prompt_comes_back_only_when_a_foreground_command_is_done():
    """A shell gives the prompt back when the command finishes: between Enter and the last line of its
    captured output the line is running (no prompt, no caret). A command sent to the background with `&`
    returns at once, as before."""
    T = timeline(5.0)
    bg = json.loads(json.dumps(SPEC))
    bg["actions"][0] = {"at": "type-ls", "on": "laptop", "type": "python shop.py &", "output": ["[1] 4242"]}
    probe = ("const k=m.compile(S,T,S.runs);const a=k.actions.find(x=>x.kind==='type');"
             "const p=t=>{const st=m.state(k,t).desks.laptop.panel;return {running:!!st.running,input:st.input,lines:st.lines.map(l=>l.text)}};"
             "return {typing:p(a.enter-.01),waiting:p((a.enter+a.output[0].at)/2),done:p(a.output.at(-1).at+.01)}")
    fg, back = node(probe, S=SPEC, T=T), node(probe, S=bg, T=T)
    assert not fg["typing"]["running"] and fg["typing"]["input"] == "ls"
    assert fg["waiting"]["running"] and fg["waiting"]["lines"] == ["ls"]          # Enter, nothing back yet: no prompt
    assert not fg["done"]["running"] and fg["done"]["lines"] == ["ls", "shop.log  shop.py"]
    assert not back["waiting"]["running"] and back["waiting"]["input"] == ""     # `&`: the prompt at once


def test_sounds_sit_on_their_frames_relative_to_the_cue():
    T = timeline()
    r = node("const k=m.compile(S,T,S.runs);return {streams:m.streams(k),ls:k.actions.find(a=>a.kind==='type')}", S=SPEC, T=T)
    ls = r["ls"]
    stream = next(s for s in r["streams"] if s["stream"].endswith("-type"))
    assert stream["t"] == "type-ls" and stream["exact"] and stream["source"] == "screens"
    assert [e[1] for e in stream["events"]] == ["key", "key", "enter"]
    assert abs(stream["events"][0][0] - (ls["keys"][0] - CUES["type-ls"])) < 1e-3
    click = next(s for s in r["streams"] if s["stream"].endswith("-click"))
    assert click["events"] == [[0, "click"]]


def test_a_point_draws_in_before_its_word_holds_then_hands_over_and_marks_replace_by_target():
    T = timeline(5.0)
    spec = {**SPEC, "actions": SPEC["actions"] + [
        {"at": "click", "on": "laptop", "point": {"line": 3, "text": "stock.take"}, "until": "late"},
        {"at": "tab", "on": "laptop", "point": {"text": "reserve"}, "for": 1.5},
        {"at": "edit", "on": "servers", "mark": {"text": "grep"}, "state": "running"},
        {"at": "late", "on": "servers", "mark": {"text": "grep"}, "state": "failed"},
        {"at": "late", "on": "shop", "mark": "checkout", "state": "finished"},
    ]}
    r = node("const k=m.compile(S,T,S.runs);const at=t=>m.state(k,t);"
             "const pick=s=>({point:s.desks.laptop.point&&s.desks.laptop.point.target,marks:Object.values(s.desks.servers.marks).map(x=>x.state)});"
             "return {before:pick(at(.75)),lead:pick(at(.85)),handed:pick(at(2.7)),gone:pick(at(4.9)),"
             "sounds:m.streams(k).filter(x=>x.stream.includes('mark')).length,"
             "on:m.streams(m.compile({...S,outcomeSounds:true},T,S.runs)).filter(x=>x.stream.includes('mark')).map(x=>x.events)}", S=spec, T=T)
    assert r["before"]["point"] is None                                     # nothing until LEAD before the word
    assert r["lead"]["point"] == {"line": 3, "text": "stock.take"}          # drawing in, 0.15 s before the click cue
    assert r["handed"]["point"] == {"text": "reserve"}                      # a newer point on the window takes over
    assert r["gone"]["point"] is None                                       # held its 1.5 s, then faded
    assert r["before"]["marks"] == ["running"] and r["gone"]["marks"] == ["failed"]   # one mark a target, the latest
    assert r["sounds"] == 0                                                 # the outcome sounds are off by default
    assert sorted(e[0][1] for e in r["on"]) == ["failed", "finished"]       # running makes no sound


def test_a_point_or_mark_without_a_target_or_with_an_unknown_state_stops_the_build():
    T = timeline()
    for bad, says in (({"at": "edit", "on": "laptop", "point": {}}, "name a target"),
                      ({"at": "edit", "on": "laptop", "mark": {"text": "x"}, "state": "done"}, "state must be one of"),
                      ({"at": "late", "on": "laptop", "point": {"text": "x"}, "until": "edit"}, "is not after")):
        r = node("try{m.compile(S,T,S.runs);return null}catch(e){return e.message}", S={**SPEC, "actions": [bad]}, T=T)
        assert r and says in r, r


def test_a_name_the_log_does_not_declare_stops_with_its_action():
    T = timeline()
    bad = {**SPEC, "actions": [{"at": "late", "on": "nowhere", "type": "ls"}]}
    r = node("try{m.compile(S,T,{});return 'compiled'}catch(e){return e.message}", S=bad, T=T)
    assert "no window \"nowhere\"" in r


def test_terminal_lines_wrap_at_a_token_boundary_when_they_can():
    r = node("return [d.wrapLine('grep -h order shop.log | jq .duration_ms',24),d.wrapLine('x'.repeat(30),24)]")
    assert not r[0]["midToken"] and all(len(x) <= 24 for x in r[0]["lines"])
    assert r[1]["midToken"]


def write_video(tmp_path, spec=SPEC, scene=None):
    T = timeline()
    (tmp_path / "timeline.json").write_text(json.dumps(T))
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live"}))
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "screens.json").write_text(json.dumps(spec))
    (tmp_path / "scenes").mkdir(exist_ok=True)
    (tmp_path / "scenes" / "s1.js").write_text(scene or SCENE)
    return T


def test_the_check_fails_a_switch_on_a_word_and_stale_sounds_and_warns_a_mid_token_wrap(tmp_path, monkeypatch):
    spec = json.loads(json.dumps(SPEC))
    spec["actions"].append({"at": "late", "switch": "laptop", "snap": False})
    spec["actions"].append({"at": "late", "on": "servers", "type": "x", "output": ["y" * 200]})
    T = write_video(tmp_path, spec)
    monkeypatch.setattr(tl, "load", lambda video: T)
    rows = screens.check(tmp_path)
    fails = [r["detail"] for r in rows if not r["ok"]]
    assert any("switch to laptop" in d for d in fails)
    assert any("run `studio screens VIDEO`" in d for d in fails)
    assert any("inside a token" in r["detail"] for r in rows if r.get("severity") == "warning")


def test_a_command_typed_over_several_lines_keeps_its_continuation_prompt_and_wraps_line_by_line(tmp_path, monkeypatch):
    spec = json.loads(json.dumps(SPEC))
    spec["actions"].append({"at": "tab", "on": "servers", "tab": "sql", "new": {"title": "sql", "prompt": ":) ", "cont": ":-] "}})
    spec["actions"].append({"at": "late", "on": "servers", "type": "x" * 40 + "\n" + "y" * 40, "output": ["Ok."]})
    T = write_video(tmp_path, spec)
    k = node("const k=m.compile(S,T,S.runs);return k.actions.at(-1).keys.length", S=spec, T=T)
    assert k == 81                                                   # the Enter inside is typed too
    monkeypatch.setattr(tl, "load", lambda video: T)
    rows = screens.check(tmp_path)
    assert not any("inside a token" in r["detail"] for r in rows)   # each line fits; joined, it would not


def test_a_paste_lands_its_text_at_once_with_one_chord_and_is_not_a_typing_rate():
    spec = json.loads(json.dumps(SPEC))
    spec["actions"].append({"at": "late", "on": "servers", "type": "SELECT 1;\nSELECT 2;", "paste": True, "output": ["1"]})
    T = timeline()
    r = node("const k=m.compile(S,T,S.runs),a=k.actions.at(-1);"
             "return {keys:[...new Set(a.keys)].length,sounds:a.sounds.filter(x=>x[1]==='key').length,"
             "rated:m.rates(k).some(x=>x.i===a.i),enter:a.enter>a.keys[0]}", S=spec, T=T)
    assert r == {"keys": 1, "sounds": 2, "rated": False, "enter": True}


def test_a_chapter_on_the_screens_rerenders_when_the_log_its_files_or_its_cues_change(tmp_path):
    from studio_kit import keys
    spec = json.loads(json.dumps(SPEC))
    spec["runs"] = {"ls": "data/runs/ls.json"}
    write_video(tmp_path, spec)
    (tmp_path / "data" / "runs").mkdir()
    (tmp_path / "data" / "runs" / "ls.json").write_text(json.dumps(SPEC["runs"]["ls"]))
    assert {"data/screens.json", "data/runs/ls.json"} <= keys.scene_data(tmp_path, "s1", {"s1"})
    assert set(CUES) <= keys.scene_cues(tmp_path, "s1", {"s1"})


def test_moments_feed_the_boxed_checks(tmp_path, monkeypatch):
    T = write_video(tmp_path)
    reqs = screens.sample_requests(tmp_path, T)
    assert {"clip": "s1"} == {k: reqs[0][k] for k in ("clip",)} and all(0 <= r["t"] < 4 for r in reqs)
    assert any(abs(r["t"] - 1.5) < 1 for r in reqs)                 # the landing of the switch


SCENE = """
import { loadScreens, screensAt, screensCamera, drawScreens } from '@studio/screens-draw.js'
import { defCard, timeSeries, productFrame } from '@studio/pages.js'
const scr = await loadScreens(import.meta.url)
function basket(c, p, tab, ctx) {
  c.S.text('page title', p.x + 30, p.y + 40, tab.page === 'placed' ? 'Order placed' : 'Basket', { size: 30, fill: ctx.look.paperInk })
  c.S.rect('checkout', p.x + 30, p.y + 120, p.w - 60, 60, { fill: '#2f7a69', box: 'checkout button' })
  return { targets: { checkout: [p.x + 30, p.y + 120, p.w - 60, 60] } }
}
export default function draw(c) {
  const s = screensAt(c, scr)
  screensCamera(c, scr, s)
  drawScreens(c, scr, s, { pages: { basket, placed: basket } })
  defCard(c, 'card', { variant: 'side', term: 'Log', def: 'A record a program writes as it runs.', t0: 3.2, t1: 3.8 })
}
"""


@needs_engine
def test_the_screens_render_the_same_frame_twice_and_name_their_windows(tmp_path):
    write_video(tmp_path)
    eng = Engine(tmp_path)
    names = {b["name"] for b in eng.boxes("s1", 1.1)["boxes"]["boxes"]}
    assert {"scr:laptop", "scr:shop", "checkout button"} <= names
    assert "scr:servers" not in names                               # not arrived yet
    later = {b["name"] for b in eng.boxes("s1", 3.5)["boxes"]["boxes"]}
    assert "scr:servers" in later and "card card" in later
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    eng.still("s1", 1.7, a)
    Engine(tmp_path).still("s1", 1.7, b)
    assert hashlib.sha256(a.read_bytes()).hexdigest() == hashlib.sha256(b.read_bytes()).hexdigest()


@needs_engine
def test_a_point_underlines_its_target_on_the_word_and_a_mark_sits_after_it(tmp_path):
    spec = json.loads(json.dumps(SPEC))
    spec["actions"] += [{"at": "edit", "on": "laptop", "point": {"text": "stock.take"}, "for": 1.0},
                        {"at": "click", "on": "shop", "mark": "checkout", "state": "finished"}]
    write_video(tmp_path, spec)
    boxes = {b["name"]: b for b in Engine(tmp_path).boxes("s1", 1.3)["boxes"]["boxes"]}
    line = boxes["scr:laptop:point:underline"]
    assert line["w"] > 100 and line["h"] < 12                      # whole under "stock.take", a thin rule
    tick, button = boxes["scr:shop:mark0"], boxes["checkout button"]
    assert tick["x"] > button["x"] + button["w"] and abs(tick["y"] + tick["h"] / 2 - (button["y"] + button["h"] / 2)) < 12
    before = {b["name"] for b in Engine(tmp_path).boxes("s1", .1)["boxes"]["boxes"]}
    assert "scr:laptop:point:underline" not in before


MONO = """
import { monoLine, syntax } from '@studio/screens-draw.js'
export default function draw(c) {
  const line = 'record["server"] = batch["server"]'
  c.camAt([[0, { x: 600, y: 300, z: 1.436 }]])
  monoLine(c, 'pieces', 200, 200, syntax(line), { size: 26 })
  c.S.text('whole', 200, 300, line, { size: 26, mono: true })
}
"""


@needs_engine
def test_coloured_pieces_of_a_line_sit_where_one_string_puts_its_letters_at_any_zoom(tmp_path):
    """monoLine places each piece at its column × 0.6 em, the font's own advance; the browser must lay the
    letters out at that advance under the camera's zoom too (unhinted), or pieces gap or overlap."""
    write_video(tmp_path, scene=MONO)
    boxes = {b["name"]: b for b in Engine(tmp_path).boxes("s1", 0.5)["boxes"]["boxes"]}
    pieces = sorted((b for n, b in boxes.items() if n.startswith("pieces:")), key=lambda b: b["x"])
    whole = boxes["whole"]
    assert len(pieces) == 5
    assert abs(pieces[-1]["x"] + pieces[-1]["w"] - (whole["x"] + whole["w"])) < .5
    assert abs(whole["w"] - len('record["server"] = batch["server"]') * 26 * .6 * 1.436) < .5

