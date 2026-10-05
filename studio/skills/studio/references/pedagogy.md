# Teaching a usable mental model

Read this when proposing, scripting or reviewing an explainer. This is the shared teaching
method; level controls scaffolding, not whether learning needs to be checked. These are craft
principles informed by the supplied learning-science synthesis and production feedback, not an
experimentally established formula or universal runtime optimum.

## The learning brief

Before an outline, write the audience's prior knowledge and a model delta: **Before, they think
or can do ___. After, they can explain, predict or do ___.** Then write the opening question and
payoff, the key ideas (usually 3–4 for intro), one recurring example, the plausible wrong model
or missing dependency, and three transfer questions. Keep expected answers in instructor material
(`research/transfer-answers.md`), away from the student reviewer.

The approved brief belongs in `research/narrative.md`. SCRIPT.md's Argument is its current
snapshot for reviewers; revise both together when the direction changes and log the decision.
Replace overlapping lists of objectives/takeaways with this brief. Depth means a more useful
model, not more details.

## Build the viewer's sequence of thoughts

Use **phenomenon → prediction → construction → abstraction → friction → compression → transfer**
as a design aid. It need not become seven chapters or a compulsory misconception in every topic.
For each chapter, identify the question, the current model's limitation, the minimum new idea,
what the viewer can now predict, and the point of local closure.

- Start with something worth explaining: a phenomenon, capability, failure or puzzle.
- Let an abstraction solve a problem the viewer has encountered. “This now does X; it still
  cannot do Y” motivates the next idea. Give meanings before names and intuition before notation.
- Reuse one visible example. Alternate example, pattern, abstraction, prediction and another case.
  Prefer a small actual record for data systems. A clearly introduced synthetic example is useful
  too; never present its invented values as measured output.
- Show enough intermediate steps for this audience. Beginners need worked examples and constrained
  predictions; experts may need less scaffolding. The learner thinks; the teacher designs the path.
- Make a plausible wrong model produce a prediction, then test the assumption. The model is the
  thing under pressure, not the viewer. Retain only failures whose diagnosis teaches something.
- Signal the key ideas when they land and gather them in a short recap. Wave plumbing past once.
  Give local closure every few minutes before opening the next question.
- Ask the viewer to predict, reconstruct, explain a causal link or transfer the model. Leave actual
  thinking time: `[predict 3]` before a reveal, not an immediately answered rhetorical question.
- Return to the opening phenomenon and compress its explanation. End the main story on a new case.
  Offer the three transfer questions and a later reconstruction prompt as a lightweight companion.

Write short spoken clauses with causal links. Use few metaphors and deepen them. State the scope
of simplifications and where an analogy breaks. Narration explains while the picture shows;
labels identify things. Production decisions and provenance belong in the logs, not the narration.
A product or filename that is the subject of a code lesson is legitimate.

## Scope and time

An exhaustive request has two deliverables: a main story built around the key ideas and reference
coverage in optional sidebars or a document. For code, map every source region to one of these.
Show this split before building. Honor an explicit choice of a literal walkthrough or build-along,
with checkpoints and navigation; do not silently discard requested detail.

Choose runtime for the cognitive arc and audience. A focused idea may fit five minutes; a richer
investigation may need 10–20 or more. These are planning priors, not learning-science thresholds.
Viewing engagement, comprehension, prediction, transfer and delayed recall are different outcomes.
Do not infer optimal learning length from a retention graph. Record main-story and reference time
separately. Justify a plan above twice the agreed target before expensive production, and estimate
speech plus pauses after scripting. Long arcs need satisfying internal closure.

## One script self-check

Log each result in SCRIPT.md's Review log with a current sentence ID and short quotation:

1. Each chapter serves a question, earns its abstraction and reaches local closure.
2. Each key idea has a landing point, a picture and a recap position.
3. A normal intro explainer has at least two meaningful prediction attempts with 2–3 seconds before
   the reveal. Record a reason for an exception in a very short or different format.
4. The final transfer question follows from the taught model and uses a new case.
5. No 30-second stretch loses its explanatory purpose. Remove a section if the model and necessary
   transitions survive without it. Check for duplicated ideas, not just duplicated words.
6. The number and vocabulary burden fit the audience. Separate quantities to remember from data
   values and identifiers. Every asserted value/behavior has evidence.
7. The outline follows ideas and needs. Source line ranges, document headings or pipeline stages
   alone are a warning of a tour; restructure when their causal purpose is missing.

Recheck affected criteria after edits: sentence IDs are positional. `studio check --only script`
provides cheap diagnostics, not a judgment of pedagogy. An agent student is also a diagnostic,
not a measurement of real learning. Where practical, ask an actual target viewer for a prediction,
transfer and later reconstruction rather than merely “was that clear?”
