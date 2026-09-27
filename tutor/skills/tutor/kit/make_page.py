"""Build a lesson's page (LESSON_DIR/out/page/index.html) around out/web.mp4.

    python kit/make_page.py LESSON_DIR

The page is only the video, its chapters, a captions toggle and a "Lost me here" button. The button
saves the moment (time, chapter, the sentence on screen and the one before it) and an optional note
to the artifact's database, collection "feedback", where the tutor reads them to revise the lesson.
lesson.json in the lesson folder gives the title, the one-line description, the version and the
poster frame.
"""
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

LESSON = Path(sys.argv[1]).resolve()
OUT = LESSON / "out"
PAGE = OUT / "page"
META = json.loads((LESSON / "lesson.json").read_text())
T = json.loads((LESSON / "audio" / "timings.json").read_text())


def mmss(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def chapters():
    out = []
    for i, s in enumerate(T["segments"]):
        d = s["end"] - s["start"]
        out.append(f'<button class="ch" type="button" style="flex-grow:{d:.2f}" data-t="{s["start"]:.2f}" '
                   f'data-end="{s["end"]:.2f}" aria-label="Chapter {i + 1}: {html.escape(s["title"])}">'
                   f'<span class="ch-bar"></span><span class="ch-name">{html.escape(s["title"])}</span></button>')
    return "\n".join(out)


CSS = """
:root{
  --bg:#0E1216;--surface:#151B22;--raise:#1B232C;--line:#27303A;--ink:#E6EBF0;--muted:#8C97A4;--faint:#5E6874;
  --amber:#F2A93B;--ice:#8FD3FF;--coral:#E4715F;
  color-scheme:dark;
}
body{background:var(--bg);color:var(--ink);font:16px/1.5 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  padding-inline:20px;padding-block:28px 56px}
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
.ch.on .ch-name{color:var(--ink)}
.ch:hover .ch-name{color:var(--ink)}
.ch:focus-visible .ch-bar{outline:2px solid var(--ice);outline-offset:3px}
.bar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.btn{all:unset;cursor:pointer;font:500 13px "IBM Plex Mono",ui-monospace,monospace;color:var(--muted);
  border:1.5px solid var(--line);border-radius:6px;padding:6px 11px;white-space:nowrap}
.btn:hover{color:var(--ink);border-color:var(--faint)}
.btn:focus-visible{outline:2px solid var(--ice);outline-offset:2px}
.btn[aria-pressed="true"]{color:var(--bg);background:var(--ice);border-color:var(--ice)}
.btn.lost{color:var(--amber);border-color:rgba(242,169,59,.45)}
.btn.lost:hover{border-color:var(--amber)}
.btn.primary{color:var(--bg);background:var(--amber);border-color:var(--amber)}
.right{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.status{font-size:13px;color:var(--muted)}
.credit{margin:0;font-size:12px;color:var(--faint)}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px;display:flex;flex-direction:column;gap:12px}
.panel .where{font:500 12px "IBM Plex Mono",ui-monospace,monospace;color:var(--muted);letter-spacing:.04em;text-transform:uppercase}
.panel blockquote{margin:0;padding-left:12px;border-left:2px solid var(--amber);color:var(--ink);max-width:70ch}
.panel blockquote .prev{display:block;color:var(--muted);font-size:14px;margin-bottom:4px}
.panel label{font-size:14px;color:var(--muted)}
textarea{font:15px/1.45 "IBM Plex Sans",system-ui,sans-serif;color:var(--ink);background:var(--bg);border:1px solid var(--line);
  border-radius:6px;padding:10px;min-height:72px;resize:vertical;width:100%;box-sizing:border-box}
textarea:focus-visible{outline:2px solid var(--ice);outline-offset:1px}
.actions{display:flex;gap:10px;flex-wrap:wrap}
details{color:var(--muted);font-size:14px}
summary{cursor:pointer;width:max-content}
summary:focus-visible{outline:2px solid var(--ice);outline-offset:2px}
.notes{list-style:none;margin:10px 0 0;padding:0;display:flex;flex-direction:column;gap:8px}
.notes li{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:12px;align-items:baseline}
.notes .t{all:unset;cursor:pointer;font:500 13px "IBM Plex Mono",ui-monospace,monospace;color:var(--ice);font-variant-numeric:tabular-nums}
.notes .t:focus-visible{outline:2px solid var(--ice)}
.notes .txt{color:var(--ink)}
.notes .txt i{color:var(--muted)}
.notes .x{all:unset;cursor:pointer;color:var(--faint);font-size:13px}
.notes .x:hover{color:var(--coral)}
@media (max-width:640px){.ch-name{display:none}.chapters{gap:4px}}
"""

JS = r"""
const v=document.getElementById('v');
const chs=[...document.querySelectorAll('.ch')];
const titles=CHAPTERS;
chs.forEach(b=>b.addEventListener('click',()=>{v.currentTime=+b.dataset.t;v.play().catch(()=>{});}));
function tick(){
  const t=v.currentTime;
  chs.forEach(c=>{const a=+c.dataset.t,b=+c.dataset.end;c.classList.toggle('on',t>=a&&t<b);
    c.style.setProperty('--p',(t>=b?100:t<=a?0:(t-a)/(b-a)*100)+'%');});
}
v.addEventListener('timeupdate',tick);v.addEventListener('seeked',tick);tick();

const track=v.addTextTrack('captions','English','en');
CUES.forEach(c=>track.addCue(new VTTCue(c[0],c[1],c[2])));
track.mode='hidden';
const cc=document.getElementById('cc');
cc.addEventListener('click',()=>{const on=track.mode!=='showing';track.mode=on?'showing':'hidden';
  cc.setAttribute('aria-pressed',on);cc.textContent='Captions '+(on?'on':'off');});

function mmss(t){t=Math.max(0,t);return Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0');}
function cueAt(t){let k=-1;CUES.forEach((c,i)=>{if(c[0]<=t)k=i;});return k;}
function chapterAt(t){let k=0;chs.forEach((c,i)=>{if(+c.dataset.t<=t)k=i;});return k;}

const lost=document.getElementById('lost'), panel=document.getElementById('panel'), status=document.getElementById('status');
const note=document.getElementById('note'), where=document.getElementById('where'), quote=document.getElementById('quote');
const save=document.getElementById('save'), cancel=document.getElementById('cancel');
const box=document.getElementById('mine'), list=document.getElementById('notes'), count=document.getElementById('count');
let db=null, moment=null;

function openPanel(){
  v.pause();
  const t=v.currentTime, k=cueAt(t), ch=chapterAt(t);
  moment={t:Math.round(t*10)/10, chapter:'s'+(ch+1), chapter_title:titles[ch],
          sentence:k>=0?CUES[k][3]:null, sentence_text:k>=0?CUES[k][2]:'',
          previous:k>0?CUES[k-1][3]:null, previous_text:k>0?CUES[k-1][2]:''};
  where.textContent=mmss(t)+' · '+titles[ch];
  quote.replaceChildren();
  if(moment.previous_text){const p=document.createElement('span');p.className='prev';p.textContent=moment.previous_text;quote.append(p);}
  quote.append(document.createTextNode(moment.sentence_text||'(before the narration starts)'));
  panel.hidden=false;note.focus();status.textContent='';
}
function closePanel(){panel.hidden=true;note.value='';moment=null;lost.focus();}
lost.addEventListener('click',openPanel);
cancel.addEventListener('click',closePanel);
save.addEventListener('click',async()=>{
  if(!db||!moment)return;
  save.disabled=true;
  const body=Object.assign({},moment,{note:note.value.trim().slice(0,2000),version:VERSION,at:new Date().toISOString()});
  try{
    await db.collection('feedback').add(body);
    status.textContent='Saved at '+mmss(body.t)+'. The tutor reads these and revises that part.';
    closePanel();
  }catch(e){
    status.textContent=e&&e.code==='quota_exceeded'?'The notes store is full; delete some notes below.'
      :'Could not save this note. Try again in a moment.';
  }finally{save.disabled=false;}
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
    if(d.note){txt.textContent=d.note;}else{const i=document.createElement('i');i.textContent='(no note) '+(d.chapter_title||'');txt.append(i);}
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


def main():
    PAGE.mkdir(parents=True, exist_ok=True)
    shutil.copy(OUT / "web.mp4", PAGE / "video.mp4")
    lines = {l["id"]: l for s in T["segments"] for l in s["lines"]}
    pid, off = META.get("poster", [T["segments"][0]["lines"][0]["id"], 1.0])
    t = lines[pid]["end"] + off if off < 0 else lines[pid]["start"] + off
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(OUT / "video.mp4"),
                    "-frames:v", "1", "-vf", "scale=1280:-2", "-q:v", "4", str(PAGE / "poster.jpg")], check=True)
    cues = json.dumps([[round(l["start"], 2), round(l["end"] + 0.25, 2), l["caption"], l["id"]]
                       for s in T["segments"] for l in s["lines"]])
    titles = json.dumps([s["title"] for s in T["segments"]])
    doc = f"""<title>{html.escape(META['title'])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
  <header><h1>{html.escape(META['title'])}</h1><span class="len">{mmss(T['total'])}</span></header>
  <div class="player"><video id="v" controls preload="metadata" poster="poster.jpg" playsinline>
    <source src="video.mp4" type="video/mp4"></video></div>
  <nav class="chapters" aria-label="Chapters">{chapters()}</nav>
  {f'<p class="credit">{html.escape(T["credit"])}</p>' if T.get("credit") else ""}
  <div class="bar">
    <button id="cc" class="btn" type="button" aria-pressed="false">Captions off</button>
    <div class="right"><span id="status" class="status" role="status"></span>
      <button id="lost" class="btn lost" type="button" hidden>Lost me here</button></div>
  </div>
  <section id="panel" class="panel" hidden aria-label="What lost you">
    <div id="where" class="where"></div>
    <blockquote id="quote"></blockquote>
    <label for="note">What didn't make sense? A few words is plenty, and you can leave it empty.</label>
    <textarea id="note" maxlength="2000"></textarea>
    <div class="actions"><button id="save" class="btn primary" type="button">Save</button>
      <button id="cancel" class="btn" type="button">Cancel</button></div>
  </section>
  <details id="mine" hidden><summary id="count"></summary><ul id="notes" class="notes"></ul></details>
</div>
<script>const CUES={cues};const CHAPTERS={titles};const VERSION={json.dumps(META['version'])};{JS}</script>
"""
    (PAGE / "index.html").write_text(doc)
    print(PAGE / "index.html")


if __name__ == "__main__":
    main()
