# Reviews: who judges what, and when it stops

A context that holds a draft anchors every later judgment to it, so content is judged in fresh
contexts that see only what they need. This file is the one copy of the review rules: the reviewer
contract, each kind of review and its stop rule, the user's listening and approval, and waivers.
The stage each one gates is in the stage tables (`explainer.md`, the genre files); the receipts'
policies are declared in `kit/src/studio_kit/reviews.py`.

## The reviewer contract

- **The main session dispatches.** A background builder reports **ready for script review**,
  **ready for motion review** or **ready for frame review** and gets the result back; it never
  reviews its own work and calls it independent. A builder's own pass is a craft check, named so.
- **Package first, then dispatch.** `studio review-motion` and `studio review-frames` print the
  bundle's folder and its manifest. Start the reviewer only after that line, on that bundle: one
  started on a raw MP4 while the bundle was still being made judged the wrong thing.
- **The reviewer's raw result goes in one place**, `VIDEO/.studio/work/review/<kind>-cut<N>.md`
  (never /tmp, never inside the bundle), and is imported with `--result` that path. A bundle takes
  one result, so a reviewer is not re-rolled.
- **Severity belongs to the reviewer.** The main session may ask a reviewer what a finding means,
  but never argues it down; a finding it disputes goes to the user with both readings. One editor's
  blocking finding was retracted under pushback, and the review stopped meaning anything.
- **Reviewers see the material, not the history**: no Review log, no earlier verdicts, no transcript.
  An empty folder reduces leakage but is not a sandbox; record unavailable isolation honestly.
- **A cap leaves findings open; it never makes them pass.** Record an unavailable or user-waived
  review with `studio review-status VIDEO ROLE unavailable|waived --reason "…"`; a waiver's reason is
  the user's authorization. A material edit invalidates an earlier receipt.

## Script review

Every teaching explainer gets one student pass before narration, including author drive at intro
level: `studio review VIDEO ROUND --only student`. Learner drive or deep-dive level also requires
expert and editor review; for risky claims in an author/intro video, add roles in
`video.json.review_roles`. Inputs are separated: expert gets script and evidence, student gets
audience, script and transfer questions without answers, editor gets argument, chain and script.
Review receipts are tied to the current teaching material. A narrative can be reviewed before any
script with `studio review VIDEO 1 --narrative FILE`.

Fix blockers and apply relevant smaller fixes once. The cap is three rounds (the third for a
blocking issue), economy two, thorough six, per revision of the script: the kit counts the scripts
reviewed since the latest structural stage mark, whatever ROUND says, and a re-run on an unchanged
script is the same round. A structural revision (`studio stage VIDEO revision --kind structural
--summary …`) marked over a script that changed since its last review starts the count again; a
mark alone does not. Raising `max_rounds` is the learner's decision. Repeatedly opposed advice is
surfaced to the user, not endlessly rewritten. A simulated student is a diagnostic, not evidence of
real learning. After a material teaching edit, rerun the affected review.

Three reviewers passed narration that only said what the picture showed, and lines that read as
written by a model rather than said by a person (`taste/narration.md`); the editor
(`prompts/reviewers/editor.md`) now looks for both. A style pass with the prose skill is not a
review; review its result.

## Motion review (Stage 11, Polish)

`studio review-motion VIDEO [--cut N]` packages the cut (the latest rendered one by default) into
`research/motion_review/cut<N>-<rev>/`: a strip of consecutive frames (about 15 a second, each
labelled with its frame number) around every event of the cut's beat sheet, the contact outlined
and usually the fourth frame so its anticipation and settle show, and over every significant move no
event covers. The bundle also holds an index of the windows with what the narration says and the
effects cued in each, the events that got no window and why, the cut's Script section, the look
sheet, and `prompt.md` from `prompts/motion_review.md` (with `taste/comic.md`'s motion questions
when the tone is comic, and the last round's findings to check for regressions). The response puts
its findings in a fenced `findings` block and the regression check in a `regressions` block; the
import (`studio review-motion VIDEO --cut N --result FILE`) needs the bundle's REVISION and a
`MOTION: PASS` or `MOTION: FIX` line, refuses a FIX with no finding it can read, and takes the status
from the findings (the verdict is a cross-check).

**The stop rule.** The review stops at a round with no must-fix findings, or after video.json
`motion_rounds` rounds (default 2), whichever comes first. Rounds count per cut lineage: each cut
motion-reviewed is a round, since the latest structural stage mark (or fork) made over a picture
that changed substantially (a new chapter, or half the chapters or more). Should-fix findings
plateaued at 25 to 45 a round in one long session, so the last round's should-fix and nit findings
go on the cut record as `known_issues`; later cuts carry them and the desk shows them, so nobody
raises them again. The receipt says how it ended: `passed`, `known-issues`, or `findings` with
`stopped: "cap"` (must-fix findings open at the cap). That last one is open, never passed: report
it to the user, who either has them fixed and records acceptance with `studio review-status VIDEO
motion waived --reason …`, or asks for more rounds by raising `motion_rounds`. A third round is
refused. After the cap, a fix's own regression may be re-checked by a fresh reviewer on a scoped
bundle; say that it was, rather than verifying it yourself.

An ended review stands for its lineage: later small edits (frame-review fixes, desk notes) are
judged by the frame review and the user, not by another motion round. It stops standing when a
chapter is new or half the chapters or more changed since the reviewed cut; publish names them and
asks for a structural mark, a fresh cut and a new review.

**Which videos need it.** An explainer with a teaching contract built in background mode publishes
only with a settled motion receipt (`passed`, `known-issues` or `waived`). In interactive mode the
user watches every cut on the desk, so it runs only when they ask; a background video's user can
also let their desk notes stand in, as a waiver whose reason names the notes by id:
`studio review-status VIDEO motion waived --reason "the user's desk notes ab12cd34, 9f00e1aa stand in"`.

## Frame review (Stage 12)

Required before delivering a deep-dive, a shared video, or when video.json `frame_review` is true.
First run `studio sheets VIDEO VIDEO/out/sheets` for the current cut, adding `--strip CLIP T` for
mechanism-sensitive transitions (`--windows FILE` lists many). `studio review-frames VIDEO [--cut N]`
packages that directory with the cut's stills, script and data/; a cut older than the sources gets
its own stills and script only. The reviewer uses `prompts/frame_review.md` and judges
full-resolution crops and transition frames, not thumbnails; validate each finding against a
full-resolution still. Import with `studio review-frames VIDEO --result FILE`; it needs the
bundle's REVISION and FRAMES verdict. A frame receipt goes stale when what its reviewer saw changes
(a chapter's frames, the Script or Evidence section, data/), not after a sound-only edit; a result
for a cut older than the sources is recorded as stale, naming the chapters changed since, and
publish refuses it.

## The user's listening

With effects or music, the user listens once to the finished mix at the timecodes audio-check
chose, and the builder records it: `audio.md`, Heard once.

## The user's approval

A final render is the user's call. Agreeing to a stage of work ("go ahead with the expansion") is
not approving a final: previews go on until the user says a cut is ready. Then record their words:
`studio review-status VIDEO approval passed --cut N --reason "their words"`. The receipt stands for
the frames revision that cut recorded, so it lapses as soon as the picture changes; `studio cut
--quality final` and `studio publish` refuse without a standing one, and say how to get it.
When the user hands over the whole job ("keep working until the video is finished"), their words
are the approval; record them, and still show them the cut.
