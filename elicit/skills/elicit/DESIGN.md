# Why elicit is shaped this way

The skill exists for one gap: a capable model knows far more about a field than it shows unless
an expert asks for the specific thing. An expert plus a model beats a layperson plus the same model
because the expert supplies the important context. The skill has the model write that context
itself, before the work, and has someone who did not do the work check against it.

Two kinds of evidence shaped it. The first is 34 corrections mined from about 790 of the author's
Claude Code sessions, each one a case where the author supplied expertise the model plausibly
already had. The second is the literature in `references/sources.md`. Each choice below says what
it answers and what it gives up.

## Four causes, not missing knowledge

The corrections sorted by main cause as follows: no standard in view during a single pass (19),
answering only the question asked (6), writing to the apparent level of the prompt (4), other (4),
and holding back to stay in scope (1). About 9 of the 34 also showed a review that ran but checked
what was easy to check instead of what the work was for. The literature agrees on the first two
and on the review failure, and finds "act as an expert" adds nothing or harms. A test run of the
first version added a fourth cause: work aimed at avoiding mistakes comes out correct and plain.
So the skill writes down the content of an expert's attention, both what they guard against and
what they reach for. It gives up the brevity of a persona line.

## The brief comes before the work

Criteria in the generation context beat the same criteria applied in a later critique, and
generic self-critique without an external signal rarely finds errors. So the brief, with its
standards and checks, exists before the first line of work. It gives up the discovery that
sometimes happens while working; when the work shows the brief is wrong, the report says so.

## List domains generously, go deep on few

A missed domain was the commonest failure in the corrections and the cost of listing one is a
line. A long checklist, though, spreads attention thin and gives each domain only its basics. So
the map lists every field that could matter and ranks them by how much each moves the effect,
the top three or four get depth, and every other listed domain contributes its single most
critical floor check. It gives up depth in the domains ranked low.

## Borrow from the field best at the effect

In the test run, the brief named the right authorities for its domains and used only their
basics. What lifted the work came from a field the result did not depend on: asked to apply game
feel principles to a 20-second explainer video, the same model added impacts, mass, a camera that
moved close, a stake for the viewer and one material rule across sound and picture, and the result
was far better. No step had asked which other field is best at the effect wanted. Step 2 now does.
It gives up some predictability: the borrowed field is a judgement, and can be the wrong one.

## A best version beside the pre-mortem, and cuts of scope only

A pre-mortem finds the floor. On its own it produced a checklist of measurable floor items, and
the one item about looking cheap dropped out because it had no yes/no check. So step 6 asks what
would impress, the checklist carries at least as many of those items as floor items, and they get
rubric checks too. Cuts remove scope (topics, features, formats) but never craft on the main
moments. It gives up the guarantee that every checklist item is machine-checkable.

## Taste is never handed to the user unexamined

The first version marked fields without a formal standard as "rubric and the user's judgment",
and the test run read that as permission not to pursue "cool". Now a field's best works stand in
for its standard: the brief names exemplars, says what makes them land, and writes a rubric. It
gives up the honesty of saying "this is taste" without effort; the rubric is still judgement, and
the report says so.

## Verifier prompts are written before the work, and run fresh

LLM judges favour their own outputs and outputs whose authorship they recognize, and a judge that
solves the problem first and grades against its own answer is wrong far less often. So each
verifier's prompt, including what an excellent result contains, is written before the work exists,
gets no reasoning or authorship, and runs in a fresh subagent from its file verbatim. Executable
checks come first because external signals are what make critique work. When the request names an
effect, one verifier judges that effect from the audience's side and says what would raise it.
Verifiers cost money, so each must earn its place. It gives up verifier prompts that can react to
specifics only visible in the finished work, beyond the paths filled in at run time.

## Two modes and files in the scratchpad

The brief is a prompt in its own right, so the skill can stop after writing it and hand it over,
or carry on and do the work. Files live in the session scratchpad because subagents need
self-contained prompts and a person may want to read or edit them, and nothing outside the
scratchpad is written unless asked. It gives up keeping briefs across sessions by default.

## What is not yet known

The current version is untested. The first version ran once, on the 20-second video, and passed
its floor checks while producing plain work; the changes above came from that run. The next step
is a benchmark: tasks sampled from an occupation taxonomy so the skill does not overfit to software
security and animation, each run bare, with the skill, and with an expert's must-haves written in,
scored against must-haves sealed from the skill's author.
