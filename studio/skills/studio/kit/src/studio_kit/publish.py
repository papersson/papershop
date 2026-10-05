"""`studio publish VIDEO`: the final cut, its web encode, and the page to publish.

Renders a final-quality cut unless the latest cut already is one (only chapters whose key changed
re-render), links it as out/master.mp4 (1080p), encodes out/web.mp4 to fit the Artifact tool's
per-file limit (15 MiB: 1080p for short videos, 720p or 540p for long ones, see web_settings), grabs
the poster frame named in video.json, and writes out/page/: index.html, video.mp4 and poster.jpg. The page is the video, its chapters and a feedback button
that saves the moment to the artifact's database (collection "feedback"):
  learner drive: "Lost me here", the time and the sentence on screen, with an optional note;
  author drive:  "Annotate", the same plus whether it is about the narration or the picture, and
                 ±1 s to nudge the moment.
Captions are burned into the video, so the page has no captions toggle. The button hides itself
where no database is available (a local file). Publishing the folder is the Artifact tool's job.
"""
import html
import json
import shutil
import subprocess
from pathlib import Path

from . import audio, render
from . import timeline as tl

WEB_CRF = 27
# The page's video must fit the Artifact tool's per-file limit for binary files (15 MiB, base64-encoded
# into one upload). web_encode picks the largest frame height and audio bitrate that fit the video's
# length, caps the bitrate, and re-encodes smaller if a pass still comes out too big.
WEB_LIMIT = 15 * 2**20
WEB_HEADROOM = 0.93
HEIGHTS = ((1080, 90), (720, 40), (540, 0))       # (height, the least video kbps it needs: measured, diagrams at crf 27)


def web_settings(duration, limit=WEB_LIMIT):
    """(height, video kbps cap, audio kbps) for a video of `duration` seconds to fit in `limit` bytes."""
    total = limit * 8 * WEB_HEADROOM / duration / 1000          # kbps for audio and video together
    audio_kbps = 64 if total > 400 else 48 if total > 160 else 28
    video = total - audio_kbps
    height = next(h for h, need in HEIGHTS if video >= need)
    return height, int(video), audio_kbps


def _encode_part(src, dst, height, video_kbps):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-an", "-vf", f"scale=-2:{height}:flags=lanczos",
                    "-c:v", "libx264", "-preset", "slow", "-tune", "animation", "-crf", str(WEB_CRF),
                    "-maxrate", f"{video_kbps}k", "-bufsize", f"{2 * video_kbps}k", "-pix_fmt", "yuv420p",
                    str(dst)], check=True)


def web_encode(src, dst, duration, limit=WEB_LIMIT, parts=None, sound=None, cache=None):
    """The page's video: as sharp as fits in `limit` bytes. Returns the settings used.

    With `parts` (the final clips, in order, each a silent video) and `sound` (the mixed soundtrack),
    each clip is encoded on its own and cached under `cache` by its file name (which carries its
    key) and the settings, then the parts are joined without re-encoding: a re-publish after a
    revision round encodes only the chapters that changed."""
    height, video_kbps, audio_kbps = web_settings(duration, limit)
    dst = Path(dst)
    for attempt in range(4):
        if parts:
            cache.mkdir(parents=True, exist_ok=True)
            tag = f"{height}p-{video_kbps}k-crf{WEB_CRF}"
            files, made = [], 0
            for p in parts:
                f = cache / f"{Path(p).stem}-{tag}.mp4"
                if not f.exists():
                    _encode_part(p, f, height, video_kbps)
                    made += 1
                files.append(f)
            for old in cache.glob("*.mp4"):
                if old not in files:
                    old.unlink()
            lst = dst.with_suffix(".txt")
            lst.write_text("".join(f"file '{f.resolve()}'\n" for f in files))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(sound),
                            "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", f"{audio_kbps}k",
                            "-ar", "24000" if audio_kbps < 48 else "48000", "-ac", "1", "-t", f"{duration:.3f}",
                            "-movflags", "+faststart", str(dst)], check=True)
            lst.unlink()
            print(f"web video: encoded {made} chapter(s), {len(parts) - made} unchanged (cached)")
        else:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", f"scale=-2:{height}:flags=lanczos",
                            "-c:v", "libx264", "-preset", "slow", "-tune", "animation", "-crf", str(WEB_CRF),
                            "-maxrate", f"{video_kbps}k", "-bufsize", f"{2 * video_kbps}k", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", f"{audio_kbps}k", "-ar", "24000" if audio_kbps < 48 else "48000", "-ac", "1",
                            "-movflags", "+faststart", str(dst)], check=True)
        size = dst.stat().st_size
        if size <= limit:
            return {"height": height, "video_kbps": video_kbps, "audio_kbps": audio_kbps, "bytes": size, "passes": attempt + 1}
        video_kbps = int(video_kbps * limit / size * 0.9)
    raise SystemExit(f"could not fit the web video under {limit / 2**20:.0f} MiB; the master is {src}")


def mmss(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def ascii_script(js):
    """The page's script, with every non-ASCII character escaped: a page opened from file:// may
    be decoded as Windows-1252, which turned "·" into "Â·" in exported notes."""
    return "".join(c if ord(c) < 128 else f"\\u{ord(c):04x}" for c in js)


def poster_time(timeline, poster):
    by_id = {s["id"]: s for s in timeline["tracks"]["narration"]}
    sid, off = poster or (timeline["tracks"]["narration"][0]["id"], 1.0)
    s = by_id[sid]
    return s["end"] + off if off < 0 else s["start"] + off


def final_cut(video):
    n = render.latest_cut(video)
    rec = render.read_cut(video, n) if n else None
    if rec and rec["quality"] == "final" and rec["video"] and len(rec["clips"]) == len(tl.load(video)["tracks"]["scene"]) and not any(
            c["key"] != k for c, (_, k, _) in zip(rec["clips"], render.plan(video, tl.load(video), "final"))):
        return rec
    return render.make_cut(video, "final")


def gate(video):
    """The full check, every chapter, before anything is published."""
    from . import check
    cfg = json.loads((Path(video) / "video.json").read_text()) if (Path(video) / "video.json").exists() else {}
    if cfg.get("teaching_contract"):
        from .review_state import require, required_roles
        for role in required_roles(cfg):
            require(video, role)
        if cfg.get("level") == "deep-dive" or cfg.get("destination") in ("share", "social") or cfg.get("frame_review"):
            require(video, "frames", frames=True)
    rows = check.run(video, everything=True)
    bad = [r for r in rows if not r["ok"]]
    print(f"publish gate: full check, {len(rows)} results, {len(bad)} failed")
    if bad:
        for r in bad[:20]:
            print(f"FAIL  {r['check']:11} {r.get('clip', '')} {r.get('t', '')} {r['detail']}")
        raise SystemExit("publish stopped: the full check failed (fix, then `studio publish` again)")


def build(video, skip_gate=False):
    video = Path(video).resolve()
    if not skip_gate:
        gate(video)
    cfg = json.loads((video / "video.json").read_text()) if (video / "video.json").exists() else {}
    t = tl.load(video)
    finish = audio.finish(video)
    print(f"audio: {finish['lufs']:.1f} LUFS, true peak {finish['true_peak_dbtp']:.1f} dBTP")
    rec = final_cut(video)
    from .cuts import media_info
    movie = render.cuts_dir(video) / f"cut{rec['cut']}" / rec["video"]
    media = media_info(movie)
    print(f"master: {media['width']}×{media['height']}, {media['fps']:g} fps, quality=final, final=true; user approval is separate")
    src = render.cuts_dir(video) / f"cut{rec['cut']}" / rec["video"]
    out, page = video / "out", video / "out" / "page"
    page.mkdir(parents=True, exist_ok=True)
    # the master: the final cut at full quality (1080p), for downloads and re-encodes
    master = out / "master.mp4"
    master.unlink(missing_ok=True)
    try:
        master.hardlink_to(src)
    except OSError:
        shutil.copyfile(src, master)
    parts = [f for _, _, f in render.plan(video, t, "final")]
    if all(parts) and render.clip_files_fresh(video, t, "final"):
        web = web_encode(src, out / "web.mp4", t["duration"], parts=parts, sound=render.mixed_sound(video, t),
                         cache=video / ".cache" / "web")
    else:
        web = web_encode(src, out / "web.mp4", t["duration"])
    print(f"web video: {web['height']}p, video ≤{web['video_kbps']} kbps, audio {web['audio_kbps']} kbps, "
          f"{web['bytes'] / 2**20:.1f} MiB (limit {WEB_LIMIT / 2**20:.0f} MiB); master: {master}")
    shutil.copyfile(out / "web.mp4", page / "video.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{poster_time(t, cfg.get('poster')):.2f}", "-i", str(src),
                    "-frames:v", "1", "-vf", "scale=1280:-2", "-q:v", "4", str(page / "poster.jpg")], check=True)
    (page / "index.html").write_text(page_html(t, cfg, rec["cut"]), encoding="utf-8")
    size = (page / "video.mp4").stat().st_size / 1e6
    print(f"cut {rec['cut']} (final) → {page}/index.html, video {size:.1f} MB")
    return page


def chapters_html(t):
    out = []
    for i, c in enumerate(t["tracks"]["scene"]):
        d = c["end"] - c["start"]
        out.append(f'<button class="ch" type="button" style="flex-grow:{d:.2f}" data-t="{c["start"]:.2f}" '
                   f'data-end="{c["end"]:.2f}" aria-label="Chapter {i + 1}: {html.escape(c["title"])}">'
                   f'<span class="ch-bar"></span><span class="ch-name">{html.escape(c["title"])}</span></button>')
    return "\n".join(out)


def page_html(t, cfg, cut):
    title = cfg.get("title", "Video")
    author = cfg.get("drive", "author") == "author"
    sentences = json.dumps([[round(s["start"], 2), s["id"], s["caption"]] for s in t["tracks"]["narration"]])
    chapters = json.dumps([[c["id"], c["title"]] for c in t["tracks"]["scene"]])
    credit = t.get("voice", {}).get("credit")
    version = json.dumps(f"{cfg.get('version', 'v1')} (cut {cut})")
    button = "Annotate" if author else "Lost me here"
    ask = ("What is wrong here, and what would be better?" if author
           else "What didn't make sense? A few words is plenty, and you can leave it empty.")
    kinds = ('<div class="kinds" id="kinds" role="group" aria-label="About">'
             '<button type="button" class="btn" data-kind="narration">narration</button>'
             '<button type="button" class="btn" data-kind="picture" aria-pressed="true">picture</button>'
             '<button type="button" class="btn" data-kind="both">both</button>'
             '<span class="gap"></span><button type="button" class="btn" id="minus">&minus;1 s</button>'
             '<button type="button" class="btn" id="plus">+1 s</button></div>') if author else ""
    js = ascii_script(JS)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{CSS}</style></head>
<body><div class="wrap">
  <header><h1>{html.escape(title)}</h1><span class="len">{mmss(t['duration'])}</span></header>
  <div class="player"><video id="v" preload="metadata" poster="poster.jpg" playsinline>
    <source src="video.mp4" type="video/mp4"></video></div>
  <div class="controls"><button id="play" class="btn" type="button">Play</button>
    <input id="seek" type="range" min="0" max="{t['duration']:.2f}" step="0.05" value="0" aria-label="Position">
    <span id="clock" class="len">0:00 / {mmss(t['duration'])}</span>
    <button id="full" class="btn" type="button">Full screen</button></div>
  <nav class="chapters" aria-label="Chapters">{chapters_html(t)}</nav>
  {f'<p class="credit">{html.escape(credit)}</p>' if credit else ""}
  <div class="bar"><span id="status" class="status" role="status"></span>
    <button id="lost" class="btn lost" type="button" hidden>{button}</button></div>
  <section id="panel" class="panel" hidden aria-label="{button}">
    <div id="where" class="where"></div>
    <blockquote id="quote"></blockquote>
    {kinds}
    <label for="note">{ask}</label>
    <textarea id="note" maxlength="2000"></textarea>
    <div class="actions"><button id="save" class="btn primary" type="button">Save</button>
      <button id="cancel" class="btn" type="button">Cancel</button></div>
  </section>
  <details id="mine" hidden><summary id="count"></summary><ul id="notes" class="notes"></ul></details>
</div>
<script>const SENTENCES={sentences};const CHAPTERS={chapters};const VERSION={version};const AUTHOR={json.dumps(author)};{js}</script>
</body></html>
"""


CSS = """
:root{--bg:#0E1216;--surface:#151B22;--raise:#1B232C;--line:#27303A;--ink:#E6EBF0;--muted:#8C97A4;--faint:#5E6874;
  --amber:#F2A93B;--ice:#8FD3FF;--coral:#E4715F;color-scheme:dark}
*{box-sizing:border-box}
[hidden]{display:none!important}  /* .btn's all:unset and .panel's flex would otherwise show hidden elements */
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  padding-inline:16px;padding-block:28px 56px}
.wrap{max-width:1080px;margin:0 auto;display:flex;flex-direction:column;gap:18px}
header{display:flex;align-items:baseline;justify-content:space-between;gap:8px 20px;flex-wrap:wrap}
h1{font-weight:600;font-size:clamp(22px,3vw,30px);line-height:1.15;margin:0;text-wrap:balance}
.len{font:500 13px "IBM Plex Mono",ui-monospace,monospace;color:var(--muted);font-variant-numeric:tabular-nums}
.player{background:#000;border:1px solid var(--line);border-radius:10px;overflow:hidden;aspect-ratio:16/9;max-width:100%}
video{display:block;width:100%;height:100%;cursor:pointer}
/* Controls sit below the picture: native ones would cover the burned-in captions whenever the
   video is paused, which is exactly when a note is written. */
.controls{display:flex;align-items:center;gap:12px}
.controls input{flex:1;accent-color:var(--ice);min-width:0}
@media (max-width:520px){#full{display:none}}
.chapters{display:flex;gap:6px}
.ch{all:unset;cursor:pointer;min-width:0;flex-basis:0;display:flex;flex-direction:column;gap:7px}
.ch-bar{height:6px;border-radius:3px;background:var(--raise);position:relative;overflow:hidden}
.ch-bar::after{content:"";position:absolute;inset:0;width:var(--p,0%);background:var(--ice)}
.ch-name{font-size:13px;line-height:1.3;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ch.on .ch-name,.ch:hover .ch-name{color:var(--ink)}
.ch:focus-visible .ch-bar{outline:2px solid var(--ice);outline-offset:3px}
.bar{display:flex;align-items:center;justify-content:flex-end;gap:12px;flex-wrap:wrap}
.btn{all:unset;cursor:pointer;font:500 13px "IBM Plex Mono",ui-monospace,monospace;color:var(--muted);
  border:1.5px solid var(--line);border-radius:6px;padding:6px 11px;white-space:nowrap}
.btn:hover{color:var(--ink);border-color:var(--faint)}
.btn:focus-visible{outline:2px solid var(--ice);outline-offset:2px}
.btn[aria-pressed="true"]{color:var(--bg);background:var(--ice);border-color:var(--ice)}
.btn.lost{color:var(--amber);border-color:rgba(242,169,59,.45)}
.btn.lost:hover{border-color:var(--amber)}
.btn.primary{color:var(--bg);background:var(--amber);border-color:var(--amber)}
.status{font-size:13px;color:var(--muted)}
.credit{margin:0;font-size:12px;color:var(--faint)}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px;display:flex;flex-direction:column;gap:12px}
.panel .where{font:500 12px "IBM Plex Mono",ui-monospace,monospace;color:var(--muted);letter-spacing:.04em;text-transform:uppercase}
.panel blockquote{margin:0;padding-left:12px;border-left:2px solid var(--amber);color:var(--ink);max-width:70ch}
.panel blockquote .prev{display:block;color:var(--muted);font-size:14px;margin-bottom:4px}
.panel label{font-size:14px;color:var(--muted)}
.kinds{display:flex;gap:8px;flex-wrap:wrap}.kinds .gap{flex:1}
textarea{font:15px/1.45 "IBM Plex Sans",system-ui,sans-serif;color:var(--ink);background:var(--bg);border:1px solid var(--line);
  border-radius:6px;padding:10px;min-height:72px;resize:vertical;width:100%}
textarea:focus-visible{outline:2px solid var(--ice);outline-offset:1px}
.actions{display:flex;gap:10px;flex-wrap:wrap}
details{color:var(--muted);font-size:14px}
summary{cursor:pointer;width:max-content}
.notes{list-style:none;margin:10px 0 0;padding:0;display:flex;flex-direction:column;gap:8px}
.notes li{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:12px;align-items:baseline}
.notes .t{all:unset;cursor:pointer;font:500 13px "IBM Plex Mono",ui-monospace,monospace;color:var(--ice);font-variant-numeric:tabular-nums}
.notes .txt{color:var(--ink)}.notes .txt i{color:var(--muted)}
.notes .x{all:unset;cursor:pointer;color:var(--faint);font-size:13px}.notes .x:hover{color:var(--coral)}
@media (max-width:640px){.ch-name{display:none}.chapters{gap:4px}}
"""

JS = r"""
const v=document.getElementById('v');
const chs=[...document.querySelectorAll('.ch')];
chs.forEach(b=>b.addEventListener('click',()=>{v.currentTime=+b.dataset.t;v.play().catch(()=>{});}));
function tick(){const t=v.currentTime;chs.forEach(c=>{const a=+c.dataset.t,b=+c.dataset.end;c.classList.toggle('on',t>=a&&t<b);
  c.style.setProperty('--p',(t>=b?100:t<=a?0:(t-a)/(b-a)*100)+'%');});}
v.addEventListener('timeupdate',tick);v.addEventListener('seeked',tick);tick();
const play=document.getElementById('play'),seek=document.getElementById('seek'),clock=document.getElementById('clock');
const toggle=()=>{if(v.paused)v.play().catch(()=>{});else v.pause();};
play.addEventListener('click',toggle);v.addEventListener('click',toggle);
document.getElementById('full').addEventListener('click',()=>v.requestFullscreen&&v.requestFullscreen());
seek.addEventListener('input',()=>{v.currentTime=+seek.value;});
v.addEventListener('play',()=>{play.textContent='Pause';});v.addEventListener('pause',()=>{play.textContent='Play';});
v.addEventListener('timeupdate',()=>{seek.value=v.currentTime;clock.textContent=mmss(v.currentTime)+' / '+mmss(+seek.max);});
document.addEventListener('keydown',e=>{if(e.key===' '&&!/TEXTAREA|INPUT|BUTTON/.test(document.activeElement.tagName)){e.preventDefault();toggle();}});
function mmss(t){t=Math.max(0,t);return Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0');}
function sentenceAt(t){let k=-1;SENTENCES.forEach((s,i)=>{if(s[0]<=t)k=i;});return k;}
function chapterAt(t){let k=0;chs.forEach((c,i)=>{if(+c.dataset.t<=t)k=i;});return k;}

const lost=document.getElementById('lost'),panel=document.getElementById('panel'),status=document.getElementById('status');
const note=document.getElementById('note'),where=document.getElementById('where'),quote=document.getElementById('quote');
const save=document.getElementById('save'),cancel=document.getElementById('cancel');
const box=document.getElementById('mine'),list=document.getElementById('notes'),count=document.getElementById('count');
let db=null,moment=null,kind='picture';

function fill(t){
  const k=sentenceAt(t),ch=chapterAt(t);
  moment=Object.assign(moment||{},{t:Math.round(t*10)/10,chapter:CHAPTERS[ch][0],chapter_title:CHAPTERS[ch][1],
    sentence:k>=0?SENTENCES[k][1]:null,sentence_text:k>=0?SENTENCES[k][2]:'',
    previous:k>0?SENTENCES[k-1][1]:null,previous_text:k>0?SENTENCES[k-1][2]:''});
  where.textContent=mmss(t)+' · '+CHAPTERS[ch][1];
  quote.replaceChildren();
  if(moment.previous_text){const p=document.createElement('span');p.className='prev';p.textContent=moment.previous_text;quote.append(p);}
  quote.append(document.createTextNode(moment.sentence_text||'(before the narration starts)'));
}
function openPanel(){v.pause();moment=null;fill(v.currentTime);panel.hidden=false;note.focus();status.textContent='';}
function closePanel(){panel.hidden=true;note.value='';moment=null;lost.focus();}
lost.addEventListener('click',openPanel);
cancel.addEventListener('click',closePanel);
if(AUTHOR){
  document.getElementById('kinds').addEventListener('click',e=>{const k=e.target.dataset.kind;if(!k)return;kind=k;
    [...document.querySelectorAll('[data-kind]')].forEach(b=>b.setAttribute('aria-pressed',b.dataset.kind===k));});
  const nudge=d=>{if(!moment)return;const t=Math.max(0,moment.t+d);v.currentTime=t;fill(t);};
  document.getElementById('minus').addEventListener('click',()=>nudge(-1));
  document.getElementById('plus').addEventListener('click',()=>nudge(1));
  document.addEventListener('keydown',e=>{if(e.key!=='a'&&e.key!=='A')return;
    if(/TEXTAREA|INPUT/.test(document.activeElement.tagName)||lost.hidden)return;e.preventDefault();openPanel();});
}
save.addEventListener('click',async()=>{
  if(!db||!moment)return;
  save.disabled=true;
  const body=Object.assign({},moment,{note:note.value.trim().slice(0,2000),version:VERSION,at:new Date().toISOString()},
    AUTHOR?{kind:kind}:{});
  try{await db.collection('feedback').add(body);
    status.textContent='Saved at '+mmss(body.t)+'.';closePanel();
  }catch(e){status.textContent=e&&e.code==='quota_exceeded'?'The notes store is full; delete some notes below.'
      :'Could not save this note. Try again in a moment.';}
  finally{save.disabled=false;}
});
function render(snap){
  const docs=snap.docs.filter(d=>d.exists).map(d=>({id:d.id,...d.data()})).sort((a,b)=>a.t-b.t);
  box.hidden=docs.length===0;
  count.textContent=docs.length+(docs.length===1?' note':' notes')+' saved';
  list.replaceChildren(...docs.map(d=>{
    const li=document.createElement('li');
    const t=document.createElement('button');t.className='t';t.type='button';t.textContent=mmss(d.t);
    t.addEventListener('click',()=>{v.currentTime=Math.max(0,d.t-3);v.play().catch(()=>{});});
    const txt=document.createElement('span');txt.className='txt';
    if(d.note){txt.textContent=(d.kind?'['+d.kind+'] ':'')+d.note;}else{const i=document.createElement('i');i.textContent='(no note) '+(d.chapter_title||'');txt.append(i);}
    const x=document.createElement('button');x.className='x';x.type='button';x.textContent='Delete';
    x.setAttribute('aria-label','Delete the note at '+mmss(d.t));
    x.addEventListener('click',()=>db.doc('feedback/'+d.id).delete().catch(()=>{status.textContent='Could not delete that note.';}));
    li.append(t,txt,x);return li;}));
}
(async()=>{
  try{db=await (window.claude&&window.claude.use?window.claude.use('db'):null);}catch(e){db=null;}
  if(!db)return;
  lost.hidden=false;
  db.collection('feedback').onSnapshot(render,()=>{box.hidden=true;});
})();
"""


def main(args):
    build(args.video)
    return 0
