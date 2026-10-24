# Why Studio keeps these parts

## The brief decides the explanation

The same tools can produce a useful undergraduate explanation or an overwhelming catalogue.
Viewer level, a few ideas and a small recurring example change the result more than additional
review machinery. The story session therefore gets deliberate time with the user. A one-page
brief keeps those choices visible, and a reel of boards held to the actual voice makes density
and breathing room perceptible before scene code is expensive to change.

There are two decisions: the user locks the story, then says when to ship. Routine construction
and corrections proceed within those decisions. The skill is a router for story, shoot and desk;
five references supply taste, collaboration and the tools needed for each job.

## Taste is durable context

A model can write an animation and describe good teaching. It cannot infer the user's specific
preferences from first principles. `references/taste.md` retains those preferences with their
reasons: canonical level, a toy example, full explanatory sentences, a clean overview, close-ups,
performed events and time to look. Its final section keeps new lessons tied to actual viewer notes.
The brief supplies any departure needed for a particular video.

## One timeline keeps picture and sound together

Narration, words, captions, clips and cues share a frame grid. Every frame is a function of time,
so a still, a rendered chapter and the live desk show the same state. A named event times the
picture and its sound on one frame. Recorded sounds use their transient peak rather than their
file's start. The beat sheet makes contact, consequence and settling part of the authored story.

Chapter cues are separate source files merged by one timeline build. Each chapter agent has its
own scene and data directory. Private check workspaces let agents inspect their work concurrently
without replacing the shared timeline or each other's cache. The main session applies shared
changes and makes the combined cut once the chapters are ready.

## Fast versions keep the user involved

The user wants to see the work, give a note and see its effect in minutes. The live engine draws
plain JavaScript scenes directly on the desk and hot-reloads them. The same renderer captures
stills and movies. Incremental keys include scene dependencies, data, assets, layout and each
chapter's relative timeline, so a changed chapter can render alone. Cached narration preserves
unchanged paragraphs. Draft cuts keep feedback fast; the shipping decision requests the final.

The desk records notes on the sentence and saved cut the user saw, replies beneath them and keeps
earlier versions available. HTTP range requests preserve video seeking. Whole-story feedback in
chat complements sentence notes. Suggestions from reviewers remain visibly separate until the
user accepts them. A reviewer cannot substitute for the viewer's judgment of level or pace.

## Reviews provide evidence

The story panel reads once through three parallel perspectives: expert, viewer and editor.
Each gets the supplied brief and script in an empty working folder to reduce context leakage.
That directory is isolation of context, not a security sandbox. Missing perspectives are reported.
Findings remain plain files and the user sees unresolved questions.

After the first scene cut, one reviewer per chapter considers motion and frames together, in
parallel. Each bundle samples the saved cut and includes sound evidence around its events.
The findings become suggested desk notes. A changed script or an applied correction never
invalidates permission to continue. The checks remain independent of a reviewer's verdict.

## Voice and sound are assets

Kokoro paragraph synthesis carries intonation across sentences. A fixed voice and speed keep a
video coherent and avoid retiming every word late in production. The lexicon preserves deliberate
pronunciations. Voice checking caught missing synthesized sentences, and alignment gives effects
and labels useful word anchors. ElevenLabs remains an explicitly selected option with cached
responses, so a rebuild can reproduce paid speech.

Recorded CC0 material sounds, key recordings and typed-code streams make actions tactile.
Typing replays actual file versions and uses the same keystroke events for picture and sound.
The mix bus supplies shared room, presence and ducking. A fixed whole-track loudness gain and
true-peak limiter preserve quiet pauses; dynamic normalization once lifted room noise between
sentences. Audio checks measure sync, audible effects, masking, pause space and loudness.
Listening still supplies judgments those measurements cannot make.

## The picture has room to explain

Captions occupy a reserved band because covering the subject makes the explanation harder to
read. They are chunked from the narration with phrase breaks and a minimum reading time. Stage
labels identify things. A clean map and large close-ups keep detail from accumulating indefinitely.
One colour retains one meaning, and outer contours carry more weight than internal dividers.

Live 3D helps when a flat diagram hides a spatial relation. It shares the timeline, legend and
checks with SVG. The lit look and Blender plates remain available for physical hero shots whose
material matters. Projected labels stay live and readable. A plate probe measures its cost before
a long render. Remotion remains for its established code and terminal components until they can
be ported and verified in live.

## Checks catch specific bugs

Length checks caught disagreement between Python and JavaScript at half-frame boundaries.
Determinism checks catch state that depends on earlier frames. Bounds, band, contrast and
legibility checks catch clipped or unreadable elements. In-frame and occlusion warnings expose
narrated objects that the picture hides. Colour-legend checks catch meanings that change colour.
Motion and flash checks inspect rendered frames. Asset provenance and code-view checks preserve
source relationships. Some checks are heuristic warnings; the story explains whether a hold or
an overlap is intentional.

Setup is inspectable through preflight and doctor. The launcher enters a pinned environment and
caches it to avoid repeated startup cost. Exports keep separate layouts and cache keys while
sharing the timeline. Publish produces the final master, web copy, poster and colophon from that
same source. The user's shipping decision is one line with a name and time.

## Measure the whole loop

File locks prevent competing shared writes by waiting. Stage timing measures elapsed production
and user waiting without limiting the work. The standing ablation prepares matching starts for
a bare agent and Studio, with the same topic, model and length. The useful comparison is the
videos and the user's verdict, alongside the time to reach them. A tool earns its place through
what it contributes to that result. The next proof is a complete shoot watched with the user.
