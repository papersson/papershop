# Extract lineage — column-level `lineage`

This is the hardest module and the highest-value view. Topology and contracts say which services talk;
lineage says **how a single value is produced** — `search.geo` came from `photos.geom`, which was
`copy`d from `exif.gps`, which was `decode`d out of `bytes.body`. You are building the `LINEAGE` block
of `MODEL.md`:

```jsonc
"lineage": {
  "groups":      [ {"id":"...", "label":"...", "x":<num>} ],   // left→right stages
  "fields":      [ [id, groupId, y, label, 0] ],               // a column placed in a stage
  "derivations": [ [fromFieldId, toFieldId, transform] ],      // how the target value is produced
  "nodeSeeds":   { "<map-node-id>": "<field-id>" }             // where a Map drill lands
}
```

The renderer draws `fields` as boxes in their group's column and `derivations` as edges; clicking a
field traces upstream + downstream. Per DESIGN.md the columns are **strict left→right and never share an
x** — `groups[].x` spaced across `0…1340`.

## The gold source: dbt

If the repo has a dbt project (`dbt_project.yml`, `models/**/*.sql`), you already have column-level
lineage — don't reconstruct it by hand. dbt's compiled artifacts hand it to you:

- **`target/manifest.json`** — every model node, its `depends_on.nodes` (model→model edges), the
  compiled SQL, and per-column `columns{}` when documented. This is the lineage graph.
- **`target/catalog.json`** — the *actual* columns and types of each built relation (from the warehouse),
  so field labels match reality rather than the YAML docs.
- `dbt docs generate` builds both; `dbt docs serve` renders the DAG. Newer dbt (1.6+) and tools like
  `dbt-column-lineage` / SQLMesh expose **column**-level edges directly.

Map it straight across:

| dbt artifact | → `lineage` |
|---|---|
| each model (`model.proj.stg_photos`) | a **group** (a left→right stage); order by `depends_on` depth |
| each column of a model | a **field** in that group (`stg_photos.geom`) |
| a column's upstream column (from column-lineage, or parsed from the model's `select`) | a **derivation** `[upstream, this, transform]` |
| the model's materialized relation maps to a Map store/svc node | a **nodeSeed** entry |

```bash
test -f target/manifest.json || dbt compile        # produce artifacts first
# read manifest.json → .nodes[] : unique_id, depends_on.nodes, columns, compiled_code
```

Read the model SQL from `compiled_code` to recover the per-column transform (below) when the manifest
only carries model-grain `depends_on`.

## SQL parsing — CREATE TABLE AS / INSERT…SELECT / views

No dbt, but there is SQL (migrations, view definitions, ETL `.sql`, stored procs)? Lineage lives in
every `SELECT` projection. **Each select expression is one derivation**, and its shape names the
transform:

| SELECT expression | derivation transform |
|---|---|
| `a.owner_id` (bare column / alias) | `copy` (or `rename` if the output name differs) |
| `CAST(taken AS timestamptz)` | `cast` |
| `lower(label)`, `ST_Point(lng,lat)` | name the function: `lower`, `to point` |
| `sum(x)`, `count(*)`, `… GROUP BY` | `aggregate` (`aggregate count`) |
| value gated by `WHERE score > 0.8` | `filter score>0.8` |
| column pulled in via `JOIN users u ON …` | `join` |
| a literal / constant | `const` |

The `FROM`/`JOIN` targets are the upstream fields; the projected names are the downstream fields. For
big or generated SQL, reach for a real parser — **`sqlglot`** (`sqlglot.lineage`) or **`sqllineage`** —
which resolve `SELECT *`, CTEs, and subqueries into column edges. For a handful of statements you can
read the SQL directly; just don't eyeball a 200-line view with three CTEs and claim per-column edges
you didn't trace.

## ORM + application code

Plenty of values are produced in code, never in SQL. Field **assignments and mappers** are derivations —
trace where each persisted or emitted field comes from:

- **DTO → entity**: `Photo(owner_id=req.jwt.sub, taken_at=exif.DateTimeOriginal)` → two derivations into
  the persisted columns, transforms `copy` and `decode EXIF`.
- **entity → event payload**: `PhotoPublished(owner=photo.owner_id, geom=photo.geom)` → derivations from
  store fields to event fields, transform `emit`.
- **entity → search/index doc**: `{ geo: photo.geom, labels: tags.map(t→t.tag) }` → `index` / `project`.
- decode/parse steps (`exif.decode(bytes)`, `json.loads`, a vision model call) are derivations from the
  raw field to the extracted field, transform named for the operation (`decode EXIF`, `vision model`,
  `transcode→webp`).

Grep the persistence and emit sites, then read each in full to recover the real source of every field:

```bash
rg -n "INSERT INTO|\.save\(|session\.add|producer\.send|\.publish\(|index\(" --type-add 'src:*.{py,ts,java,go}' -tsrc
```

## Building the model — the stages

`groups` are the pipeline read left→right; pick the stages that exist and give each an `x`:

```
raw/source → extracted → derived → persisted → events → sinks
   x:70        x:280      x:490      x:710      x:930    x:1140
```

`fields` stack inside a group by `y` (start ≈150, ≈80px apart); the 5th tuple slot is reserved `0`.
`derivations` carry the **named** transform — always a verb the reader can trust: `decode`, `copy`,
`cast`, `rename`, `filter X`, `aggregate`, `join`, `index`, `project`, `emit`. `nodeSeeds` maps each
relevant Map node to a representative field so the drill panel's "trace this data's lineage" button
lands somewhere sensible (the table's primary derived column, the bucket's raw blob, the topic's key
field).

## Worked snippet

A view-style `INSERT…SELECT` plus an event emit in app code:

```sql
-- migrations/030_photos.sql
INSERT INTO photos (owner_id, geom, taken_at)
SELECT  j.owner_id,                          -- from the JWT claim, copied
        ST_Point(e.lng, e.lat) AS geom,      -- built from decoded EXIF gps
        CAST(e.taken AS timestamptz)         -- decoded + cast
FROM    exif e JOIN jwt j USING (upload_id)
WHERE   e.lat IS NOT NULL;
```

```python
# publisher.py
producer.send("photo.published",
    PhotoPublished(owner=photo.owner_id, geom=photo.geom))   # entity → event, emit
```

→ the `lineage` fragments (matching `MODEL.md` tuple order exactly):

```jsonc
"groups": [
  {"id":"extract","label":"Extracted","x":280},
  {"id":"pdb","label":"Photos DB","x":710},
  {"id":"event","label":"Events (Avro)","x":930}
],
"fields": [
  ["exif.gps",    "extract", 150, "exif.gps",        0],
  ["exif.taken",  "extract", 230, "exif.taken_at",   0],
  ["jwt.owner",   "extract", 330, "jwt.owner_id",    0],
  ["photos.geom", "pdb",     150, "photos.geom",     0],
  ["photos.taken","pdb",     230, "photos.taken_at", 0],
  ["photos.owner","pdb",     330, "photos.owner_id", 0],
  ["ev.published","event",   150, "photo.published", 0]
],
"derivations": [
  ["exif.gps",    "photos.geom",  "to point"],
  ["exif.taken",  "photos.taken", "cast"],
  ["jwt.owner",   "photos.owner", "copy"],
  ["photos.geom", "ev.published", "emit"],
  ["photos.owner","ev.published", "emit"]
],
"nodeSeeds": { "pdb": "photos.geom", "kafka": "ev.published" }
```

The `WHERE e.lat IS NOT NULL` would attach as `filter lat≠null` on the `geom` derivation if it changed
the row set you care about; the `JOIN` is implicit in pulling `jwt.owner` and `exif.*` into one row.
See `templates/model.example.json` for the full six-stage Aperture lineage this is a slice of.

## Honest degradation — say it loudly

**Full column-level lineage needs dbt or parseable SQL.** A plain OLTP service that just reads and
writes rows through an ORM does not encode value-level derivation anywhere you can trust. There, do not
invent per-column edges:

- **Degrade to entity/field grain**: one field per table / DTO / event (e.g. a single `photos` field, not
  `photos.geom` + `photos.owner_id`), with derivations meaning **"writes / derives"** rather than a
  precise transform (`writes`, `derives`).
- **Mark it coarse** in the field labels and the handoff (`photos (table)`), and tell the user the
  Lineage view is entity-grain, not column-grain.
- **Never fabricate a precise derivation you can't trace.** Per `MODEL.md → Honesty`, a wrong lineage
  edge lies with the authority of the canonical diagram — a `cast` you guessed is worse than an honest
  `derives`. When unsure whether `b` comes from `a`, leave the edge out and note the gap.

If there is no dbt, no SQL, and no traceable mapper at all, omit `lineage` entirely — the view-tab
disappears, which is more honest than a fabricated derivation graph.
