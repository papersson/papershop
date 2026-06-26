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

**The invariant (this is what's being dogfooded):** to diagram a new project you produce only a model;
you never touch the renderer. If a real repo forces a renderer change, that is a **finding** — stop and
record it (see DESIGN.md → "Extending the spine"), don't quietly patch the spine.

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

## Validate — don't trust the first extraction

Have an agent that did **not** build the model check it against the code: do the claimed edges exist? are
transports/datastores right? Mark anything unconfirmed rather than asserting it. A precise-but-guessed
badge is worse than a vaguer-but-true one (MODEL.md → "Honesty").

## Render — inject the model into the spine

1. Read `templates/renderer.html`.
2. Replace the contents of its `<script id="cartograph-model" type="application/json"> … </script>`
   block with the project's model JSON (validate it parses first).
3. Write the result to `<system-name>.html` where the user wants it (default: repo root or cwd).

The renderer is unchanged otherwise. The output is one self-contained file (no network, system fonts).

## Verify — the deterministic rung

Drive `agent-browser` (start `agent-browser --help`): open the file, confirm a clean console, that it
is self-contained (one request), renders intact at ~390px and ~1280px, the global-layer toggle
recolours the graph, and the lineage trace highlights upstream/downstream. A failing check is a
blocking defect. Then open it for the user.

## Hand off — honestly

Tell the user what was mapped, **what was extracted vs inferred**, and what's missing (a source not
present, a subsystem not covered, lineage only at entity grain). Point them at the file. If a view is
absent because the data wasn't there (no events ⇒ no event bus; no status enum ⇒ no lifecycle), say so.

## Read these as you go

- `MODEL.md` — the contract. Read before extracting.
- `DESIGN.md` — the visual system. Read if you touch presentation or want the model to render its best.
- `templates/model.example.json` — a complete, real model to pattern-match against.
