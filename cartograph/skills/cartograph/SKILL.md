---
name: cartograph
description: >
  Map a real codebase as ONE navigable, self-contained HTML diagram. Use when the user wants to
  understand or document a system's architecture, see how a service connects to others, trace where
  data comes from and flows to (data lineage), onboard onto an unfamiliar repo, or produce a living
  architecture diagram. Reads the system from its OWN structured sources (docker-compose/k8s,
  OpenAPI/protobuf/GraphQL/AsyncAPI, ORM models/migrations, CODEOWNERS, event topics, dbt/SQL for
  column-level lineage), emits a system-model JSON, and renders it with a fixed visual spine: a
  typed-map home you scan one global layer at a time and drill per-element, plus column-level data
  lineage and sequence/lifecycle siblings. No legends, full-bleed, zero external requests. NOT for a
  single script or a trivial library — it gates on whether a system has enough moving parts to map.
---

# cartograph

Map any system as **one** diagram. The architecture has a hard seam, and crossing it casually is the
one thing not to do:

- **The renderer is the spine.** `templates/renderer.html` reads ONE system-model JSON and draws every
  view. It is project-agnostic and **byte-stable across projects**. You never edit it to fit a target.
- **The model is the contract.** `MODEL.md` — the JSON schema the renderer reads. Worked example:
  `templates/model.example.json` (the Aperture system, which is also the renderer's built-in default).
- **Extraction is the adapter.** Reading a real repo and emitting that model is the whole job, and the
  only thing that varies per project.

**The invariant — logic, not layout.** A new project is a new *model*, never new renderer *logic*. The
model carries every **semantic** decision (which nodes/edges exist, transports, ownership, durability,
live-vs-planned state); the renderer must never grow project-specific *branching*. But hand-tuning
**layout** — node placement, de-cluttering a dense graph, routing — is **not** a violation; it is a
sanctioned editorial phase (see "Editorial pass"). The line is logic vs. layout: a forced change that
adds *placement* is expected and fine; a forced change that adds *logic* is a finding that should grow
the spine **for everyone** (see DESIGN.md → "Extending the spine"), not a per-project fork.

## Gate — is there a system to map?

Map when the repo has real moving parts: multiple services/processes, datastores, async messaging,
external integrations. Don't map a single script, a pure library, or a CRUD app with one table and no
dependencies — say so and offer a one-paragraph description instead. A diagram of nothing is overhead.

## Orient — what does this repo give you?

Before extracting, scout what structured sources exist; they decide how much is ground-truth vs
inferred. Look for: `docker-compose*.yml`, `k8s`/`helm` manifests, `*.proto`, `openapi`/`swagger`,
GraphQL SDL, `asyncapi`, ORM models + migrations, `CODEOWNERS`, message-topic definitions, `dbt`
project / SQL models. The more of these exist, the more deterministic (and trustworthy) the model.

## Extract — produce the model

Build the model bottom-up, **highest-signal source first**, loading the matching module only when the
source exists. Each module maps a source to part of `MODEL.md`:

- `modules/extract-topology.md` — compose/k8s/import-graph/mesh → `nodes` + `edges` (the skeleton)
- `modules/extract-contracts.md` — OpenAPI/protobuf/GraphQL/AsyncAPI → edge `tx` + `payload`, drill schemas
- `modules/extract-datastores.md` — DB config/ORM/migrations/IaC → store nodes + `dur` (durability)
- `modules/extract-ownership.md` — CODEOWNERS/dir structure → `team`
- `modules/extract-events.md` — Kafka/pub-sub/schema-registry → async edges + the event bus
- `modules/extract-lineage.md` — dbt/SQL/ORM field-mappings → column-level `lineage` (hardest, highest value)
- `modules/extract-temporal.md` — entry-point trace → `sequence`; status enum → `lifecycle` (best-effort)

Rules of extraction:
- **Prefer deterministic sources over inference.** A claimed edge should trace to a real call, config, or
  contract. Infer from code only to fill gaps, and mark inferred elements low-confidence.
- **Place nodes by data-flow** (sources top-left, sinks bottom-right, bus in the middle) — see DESIGN.md.
  Good `x,y` is most of what makes it look designed; `null` falls back to auto-layout.
- **Shape the model to render well** — keep `payload` signatures short, name transforms on lineage edges,
  draw the ONE critical request for the sequence.
- For a large repo, this is a natural fan-out (one extractor per service / source) and a good fit for the
  `orchestrate` plugin; validation (below) is the adversarial pass.

## Validate — the factual rung (at least as important as "it renders")

A diagram that renders cleanly over a *wrong* model is not shippable, and "it renders" is dangerously
easy to mistake for done. This step has teeth.

Run an **auditor that did NOT build the model**, one pass per claim class, each re-reading source
independently and returning, per claim, `supported` / `unsupported` / `unconfirmable` with a `file:line`
citation:

- **edges exist** — each edge traces to a real call / config / connection
- **transports correct** — REST vs gRPC vs Kafka vs SQL matches the actual client/contract
- **datastores + durability correct** — the store exists and its sot/derived/ephemeral class is right
- **teams correct** — ownership matches CODEOWNERS / catalog, not a guess
- **payloads match a real contract** — the signature is real (a query/RPC/topic that actually exists)
- **live vs planned correct** — an edge shown live is wired in code, not logged-only / feature-flagged

**The bar:** every `unsupported` claim is fixed or downgraded to inferred (vaguer-but-true, MODEL.md →
"Honesty") before ship; `unconfirmable` is marked, never asserted. A confidently wrong label trades on
the diagram's authority — the worst outcome. For a large system this fans out cleanly (one auditor per
class over the repos) — a good `orchestrate` job. A passing render check over an unvalidated model is
**not** shippable.

## Render — inject the model into the spine

1. Read `templates/renderer.html`.
2. Replace the contents of its `<script id="cartograph-model" type="application/json"> … </script>`
   block with the project's model JSON (validate it parses first).
3. Write the result to `<system-name>.html` where the user wants it (default: repo root or cwd).

The renderer is unchanged otherwise. The output is one self-contained file (no network, system fonts).

## Verify — two rungs: it renders (floor) AND it looks right (ceiling)

**Deterministic floor.** Drive `agent-browser` (start `agent-browser --help`): open the file, confirm a
clean console, that it is self-contained (one request), renders intact at ~390px and ~1280px, the
global-layer toggle recolours the graph, and the lineage trace highlights upstream/downstream. A failing
check is a blocking defect. *Caution:* the daemon can crash under rapid open/eval/screenshot cycling —
drive it **serially, with a ~500ms pause between cycles and a ~3-attempt retry guard.**

**Editorial ceiling (the loop a render check can't replace).** A single render pass will not surface a
hairball, a mis-drawn marker, or label collisions. Run an **adversarial visual-quality loop**: a critic
agent that is *not* the builder reviews screenshots at both widths against DESIGN.md's non-negotiables
and returns blocking findings until every view passes, then SHIP. This is do → critique → fix, not one
shot. Then open it for the user.

## Editorial pass — sanctioned layout tuning

Publication quality on a dense real graph needs a hands-on layout pass: place nodes by data-flow,
de-clutter (DESIGN.md → "Taming a dense graph"), tune routing. This is **expected and allowed** — it is
layout, not logic, so it does not break the invariant. Record what you tuned. Anything that needs new
*logic* rather than placement is a finding that should grow the spine instead.

## Hand off — honestly

Tell the user what was mapped, **what was extracted vs inferred**, and what's missing (a source not
present, a subsystem not covered, lineage only at entity grain). Point them at the file. If a view is
absent because the data wasn't there (no events ⇒ no event bus; no status enum ⇒ no lifecycle), say so.

## Read these as you go

- `MODEL.md` — the contract. Read before extracting.
- `DESIGN.md` — the visual system. Read if you touch presentation or want the model to render its best.
- `templates/model.example.json` — a complete, real model to pattern-match against.
