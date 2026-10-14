# Gates: what the user decides, and when

Every misfire in two recent videos was a gate: a draft not shown before the work started, a "go
ahead" read as more than it said, a final rendered before the user was done with previews, a desk
the user had to ask about, an animatic nobody showed them. This file is the one list of the user's
decisions, in the order they come, and how each is asked.

## How to ask

- **One question, and what yes unlocks.** End a gate with a question that names what happens on
  yes ("Shall I build the boards and the animatic from this? I'll post them on the desk.") rather
  than a summary that leaves the user to guess whether you are waiting.
- **"Go ahead" covers the next gate, no further.** Record the scope of each approval in the
  narrative's Decisions. When a user hands over the whole job ("work autonomously until the first
  desk version is done", "keep working until the video is finished"), that scope is the job: don't
  stop at the next gate to ask again.
- **Never ask again what was already decided.** A routine fix to an approved direction needs no
  new approval; a genuine change of scope does.

## The decisions, in order

| Decision | When | How the user sees it | Enforced by |
|---|---|---|---|
| Setup | first use, or a missing tool | the install plan in chat (`setup.md`) | prose |
| The draft | when the user asks for one, before anything else | a treatment in chat: numbered sections, each with its narration and what is on screen, the camera and the sound | prose |
| The narrative | before any script | `research/narrative.md` with its risks (`propose.md`) | prose |
| The look | before scenes are animated | stills and the look sheet, on the desk | prose |
| Boards and animatic | as soon as they exist | posted on the desk, with a link; nothing waits on them in background mode | prose (the desk shows them) |
| Each cut | as it is made | the desk, with the changes listed; notes go on sentences | the desk |
| The final | when the user says a cut is ready | `studio review-status VIDEO approval passed --cut N --reason "…"` | the kit: `cut --quality final` and `publish` refuse without it |
| Publishing locally | after the approval | `studio publish` (`publishing.md`) | the kit: receipts and the full check |
| Uploading, posting | only when asked | the Artifact tool or the user's own channel | prose |

**The draft comes first.** "Remember you need to give me the draft before you do anything": a user
who asks for an outline or a draft gets it in chat before folders, research runs or tools. Write it
from what you know, mark what needs checking, and do the research once they have seen the shape.

## The desk is how the user sees the video

Start `studio desk VIDEO` before the first cut and give the user its address; say so again when a
new cut is up. Never send a raw MP4 path or a viewer of your own instead: the desk is where notes
land on sentences, where the user's round is marked received, and where the known issues show.
"Doesn't my plugin have a desk where I can give feedback?" came after a builder served its own.

In background mode the desk plays the latest cut, boards and animatic included, so the user can
watch the video take shape without waiting on the builder; in interactive mode it draws the current
scenes as they are saved (`desk.md`). When the user asks how long until there is something to see,
the answer is the desk's address if anything is on it.
