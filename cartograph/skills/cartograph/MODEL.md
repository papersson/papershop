# The system-model contract

This is the **only** interface between extraction and rendering. The extractor's whole job is to emit
a JSON object matching this schema; `templates/renderer.html` reads it and draws every view. You never
edit the renderer — you produce this model. A complete worked instance is
`templates/model.example.json` (the Aperture system).

The model is injected into the renderer's `<script id="cartograph-model" type="application/json">`
block (the render step replaces that block's contents). It must be valid JSON.

Fields are **tuples** (positional arrays), not objects, to keep models compact and diffable. Order matters.

```jsonc
{
  "meta":  {
    "name": "<system name>", "subtitle": "<one line>",
    "teamColours":   { "<team>": "<cssVar or hex>" },  // optional; else a deterministic colour per team
    "suppressLabel": ["REST"]                           // optional; edge labels with these values are hidden (show exceptions only)
  },
  "nodes": [ /* see NODES */ ],
  "edges": [ /* see EDGES */ ],
  "lineage":  { /* optional — see LINEAGE */ },
  "sequence": { /* optional, ONE flow — see SEQUENCE */ },
  "sequences":[ /* optional, MANY flows — array of the sequence object; shows a flow selector */ ],
  "lifecycle":{ /* optional — see LIFECYCLE */ }
}
```

`lineage`, `sequence`/`sequences`, and `lifecycle` are optional: omit one and its view-tab disappears.
`nodes` and `edges` are required (the Map is the home view).

## NODES — `[id, x, y, role, name, team, opts?]`

| pos | field | meaning |
|---|---|---|
| 0 | `id` | unique short string, referenced by edges |
| 1 | `x` | viewBox x of the node centre, or `null` for auto-layout (see below) |
| 2 | `y` | viewBox y, or `null` |
| 3 | `role` | one of `client` `edge` `svc` `store` `broker` — sets colour + shape |
| 4 | `name` | display label |
| 5 | `team` | owning team (always shown as the node subtitle; powers the Team layer) |
| 6 | `opts` | optional object: `dur`, `tier`, `tag`, `ddd`, `bus` |

`opts` keys:
- `dur` — durability: `sot` (source of truth) · `derived` · `ephemeral`. Absent ⇒ "stateless". Powers the Durability layer.
- `tier` — criticality: `p0` · `p1` · `best`. Powers the Criticality layer (a node's tier is also inferred from its edges).
- `tag` — a short engine/variant badge shown bottom-right (e.g. `Postgres`, `S3`, `Redis`).
- `ddd` — bounded-context name; defaults to `team`. Surfaces in the drill panel.
- `bus` — `true` marks a wide event-bus bar (only meaningful for `role:"broker"`).
- `state` — `"planned"` renders the node ghosted (designed-but-not-yet-built / target state); default current-state. Use it (with edge `state`) to show a target architecture honestly rather than claiming it's live.

**Layout.** The viewBox is `1280 × 720`. Hand-placed `x,y` look best — place by data-flow (sources
left/top, sinks right/bottom), keep ~150px between centres, group by role into bands. If you set `x,y`
to `null`, a role-tiered auto-layout places the node (columns: client → edge → svc → broker → store).
Mixing is allowed (place the important nodes, null the rest). Prefer placing them. Nodes **auto-size to
their own label and tag** (the renderer measures the text), so long names like `place-quarantine-reaction`
won't overflow — but a wide node needs a little more horizontal room from its neighbours, so leave gaps.

## EDGES — `[from, to, tx, async, delivery, consistency, state, crit, payload]`

| pos | field | values |
|---|---|---|
| 0 | `from` | source node id |
| 1 | `to` | target node id |
| 2 | `tx` | transport: `rest` `grpc` `kafka` `sql` `bytes` `cache` |
| 3 | `async` | `1` async (dashed) · `0` sync (solid) |
| 4 | `delivery` | `exactly-once` · `at-least-once` · `best-effort` |
| 5 | `consistency` | `strong` · `ryw` (read-your-writes) · `eventual` · `stale` |
| 6 | `state` | `0` current-state · `"planned"` renders the edge ghosted (designed-but-not-wired) |
| 7 | `crit` | `p0` · `p1` · `best` |
| 8 | `payload` | the contract on the wire — a short signature shown in the drill panel (e.g. `GetPhoto(id)→Photo`, `INSERT photos(...)`, `photo.published v4`) |

The always-on base paints `tx` colour + `async` line-style; the Delivery / Consistency / Criticality
layers recolour by fields 4 / 5 / 7. Keep `payload` short — it is the per-edge drill content.

## LINEAGE — column/field-level data derivation

```jsonc
"lineage": {
  "groups":      [ { "id": "...", "label": "...", "x": <number> } ],   // left→right stages
  "fields":      [ [id, groupId, y, label, _] ],                       // a column/field; _ = 0
  "derivations": [ [fromFieldId, toFieldId, transform] ],              // an edge: how the value is produced
  "nodeSeeds":   { "<map-node-id>": "<field-id>" }                     // which field a Map node drills into
}
```

- `groups` are vertical columns; space their `x` across `0…1340`, ordered by the flow of data
  (raw → extracted → derived → persisted → events → sinks). `label` is the column header.
- `fields` are the columns/keys themselves; `y` stacks them within a group (≈80px apart, starting ~150).
  The 5th tuple slot is reserved — pass `0`.
- `derivations` are the lineage edges, each carrying the `transform` that produced the target from the
  source (`decode`, `copy`, `filter score>0.8`, `aggregate`, `project`, `emit`, …). Clicking a field
  traces upstream + downstream over these.
- `nodeSeeds` connects the Map's drill to the Lineage view: the "trace this data's lineage" button on a
  node opens the Lineage view focused on the named field.

Column-level lineage is the highest-value, hardest part. Get it from dbt manifests / SQL parse / ORM
field-mappings where they exist; degrade to entity-level (one field per table) elsewhere, and mark it.

## SEQUENCE — the critical path in time

```jsonc
"sequence": {
  "participants":  [ [id, label, role] ],                  // lifelines, left→right
  "messages":      [ [fromId, toId, label, isReturn, isAsync] ],  // ordered top→bottom; flags are 0/1
  "dividerIndex":  8,                                       // optional: draw the "async boundary" before this message; omit for none
  "dividerLabel":  "async · ms–seconds later"              // optional label for that divider
}
```
`role` colours the lifeline header (`client` `svc` `store` `broker` `async` `notify`). `isReturn`/`isAsync`
render dashed. Draw the ONE request that matters, including its unhappy/async tail. The async divider is
per-sequence and optional — there is no baked-in position; set `dividerIndex` only where a flow actually
crosses into async, and omit it entirely for flows that don't.

**Several flows.** When a system has more than one materially-different critical path (e.g. reject /
accept / clean-pass from the same entry point), use `sequences: [ {name, participants, messages,
dividerIndex?, dividerLabel?}, … ]` instead of `sequence`; the view shows a flow selector. Give each a
short `name`. Prefer a single dominant flow and add alternates only when they are genuinely different
paths, not minor branches.

## LIFECYCLE — the central entity's state machine

```jsonc
"lifecycle": {
  "states":      [ [id, x, y, color, name, sub, opts?] ],   // color is a CSS var string; opts.dbl=1 = terminal ring
  "transitions": [ [fromId, toId, label, dir] ]             // dir: "h" horizontal · "v" vertical · "a" auto
}
```
Colours: `var(--client|data|async|live|err|muted)`. Include the error / retry / terminal states — the
unhappy paths are the point.

## Honesty

Every diagram should be honest about what was extracted vs inferred. Where confidence is low, prefer a
vaguer-but-true label over a precise-but-guessed one, and note residual gaps in the handoff. A badge
that is trusted-but-wrong is the worst outcome — it lies with the authority of the canonical diagram.
