"""`studio publish VIDEO`: the final cut, its web encode, and the page to publish.

Renders a final-quality cut unless the latest cut already is one, encodes out/web.mp4 (small
enough for an artifact page), grabs the poster frame named in video.json, and writes out/page/:
index.html, video.mp4 and poster.jpg. The page is the video, its chapters and a feedback button
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

from . import render
from . import timeline as tl

WEB_CRF = 27


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
    if rec and rec["quality"] == "final" and rec["video"] and not any(
            c["key"] != k for c, (_, k, _) in zip(rec["clips"], render.plan(video, tl.load(video), "final"))):
        return rec
    return render.make_cut(video, "final")


def build(video):
    video = Path(video).resolve()
    cfg = json.loads((video / "video.json").read_text()) if (video / "video.json").exists() else {}
    t = tl.load(video)
    rec = final_cut(video)
    src = render.cuts_dir(video) / f"cut{rec['cut']}" / rec["video"]
    out, page = video / "out", video / "out" / "page"
    page.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:v", "libx264", "-preset", "slow",
                    "-crf", str(WEB_CRF), "-tune", "animation", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "128k", "-movflags", "+faststart", str(out / "web.mp4")], check=True)
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
  <div class="player"><video id="v" controls preload="metadata" poster="poster.jpg" playsinline>
    <source src="video.mp4" type="video/mp4"></video></div>
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
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  padding-inline:16px;padding-block:28px 56px}
.wrap{max-width:1080px;margin:0 auto;display:flex;flex-direction:column;gap:18px}
header{display:flex;align-items:baseline;justify-content:space-between;gap:8px 20px;flex-wrap:wrap}
h1{font-weight:600;font-size:clamp(22px,3vw,30px);line-height:1.15;margin:0;text-wrap:balance}
.len{font:500 13px "IBM Plex Mono",ui-monospace,monospace;color:var(--muted);font-variant-numeric:tabular-nums}
.player{background:#000;border:1px solid var(--line);border-radius:10px;overflow:hidden;aspect-ratio:16/9;max-width:100%}
video{display:block;width:100%;height:100%}
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
