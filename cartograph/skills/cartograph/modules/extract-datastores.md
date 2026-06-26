# Extract datastores — store nodes + durability

Maps a system's persistence to `MODEL.md`: every place state lives becomes a `role:"store"` node, and
every service that reads or writes it becomes an edge. The one judgement that earns its keep here is
`opts.dur` — the durability class — because it powers the Durability layer and is what someone reaches
for during a DR conversation ("what can we lose and rebuild, what can we never lose?").

## Sources — where persistence declares itself

Work top-down from the most authoritative source you have:

- **DB config / env** — `DATABASE_URL`, `REDIS_URL`, `ELASTICSEARCH_URL`, `*_DSN`, JDBC strings,
  `docker-compose` service blocks (`image: postgres:16`, `redis:7`, `elasticsearch`). The scheme names
  the engine (`postgres://`, `redis://`, `mysql://`, `mongodb://`, `s3://`).
- **ORM models + migrations** — ground truth for a relational store and its tables: Prisma
  (`schema.prisma`), SQLAlchemy / Alembic, ActiveRecord (`schema.rb`, `db/migrate`), TypeORM entities,
  Ecto (`schema`, `priv/repo/migrations`), Django (`models.py`, `migrations/`). Migrations are the
  strongest signal — a real `CREATE TABLE` cannot be a guess.
- **IaC** — Terraform / CDK / CloudFormation declare managed stores: `aws_db_instance` / RDS,
  `aws_s3_bucket`, `aws_dynamodb_table`, `aws_elasticache_cluster`, `google_bigquery_dataset`,
  `google_storage_bucket`. These also carry replication / backup / TTL settings that inform `dur`.
- **Cache clients** — Redis / Memcached client construction (`new Redis(...)`, `redis.from_url`).
- **Search** — Elasticsearch / OpenSearch / Algolia clients and index definitions.
- **Warehouse** — BigQuery / Snowflake / Redshift datasets, dbt `profiles`/targets.
- **Object storage** — S3 / GCS / Azure Blob SDK calls (`PutObject`, `upload_fileobj`).

## Create the store node — `[id, x, y, "store", name, team, opts]`

One node per logical store (collapse a primary + its read-replica into one). Set `role:"store"`, give
it a human `name`, the owning `team`, and in `opts`:

- `tag` — the engine badge, shown bottom-right: `Postgres`, `Redis`, `S3`, `Elastic`, `BigQuery`,
  `DynamoDB`, `Snowflake`. Keep it to the engine, not the version.
- `dur` — the durability class (next section).

Place stores in the bottom band of the viewBox (sinks sit bottom-right; `y` ≈ 600–690 in the worked
example). Then draw an edge from every service that touches the store:

- `tx` is the transport: `sql` for relational/queryable engines, `cache` for Redis/Memcached, `bytes`
  for object storage (S3/GCS) blob PUT/GET. (Edge fields 3–8 come from `extract-contracts`; for a write
  to a SoT use `delivery:"exactly-once"`, `consistency:"strong"`; a cache GET is `best-effort` / `stale`.)
- `payload` is the operation signature: `INSERT photos(owner_id, ...)`, `GET/SET sess:{tok}`,
  `PUT orig/{id} (octet-stream)`, `batch load events_fact`.

## Assign `dur` — the call that matters

`dur` is one of three, and the whole point is to separate what you must protect from what you can
rebuild:

- **`sot`** (source of truth) — the authoritative copy. Losing it loses data. A store is `sot` when it
  is **written by exactly one owning service as the record of truth** and nothing upstream can
  regenerate its contents. Your primary Postgres/MySQL and your canonical object store are usually `sot`.
- **`derived`** — a rebuildable projection of a SoT. Search indexes, denormalized read-models, the
  warehouse, a CDN origin cache. Tell-tale: it is **populated by replaying events or running a sync /
  ETL / reindex job**, not by an original write. Losing it costs a rebuild, not the data.
- **`ephemeral`** — in-flight or throwaway state: caches, session stores, anything **TTL'd** or
  reconstructable on next request. Redis used as a cache is `ephemeral`; Redis used as the only home of
  a value is `sot`.

Three questions decide it: (1) Is it written by one owner as the record of truth? → leans `sot`.
(2) Is it populated by replaying events / a sync job from somewhere else? → `derived`. (3) Does it have
a TTL or get reconstructed on demand? → `ephemeral`. The same engine can be any class — judge by role,
not by `tag`. (Stores left without `dur` render as plain "stateless", which is wrong for a store —
always set it.)

## Worked snippet

Sources:

```prisma
// schema.prisma  →  Postgres, owns the photos record of truth
model Photo { id String @id  ownerId String  geom Unsupported("geometry") }
```
```ts
const redis = new Redis(process.env.REDIS_URL);     // sessions, EX 3600  → cache
await s3.putObject({ Bucket: "originals", Key: `orig/${id}` });  // canonical blob
```

Becomes three store nodes + their edges:

```jsonc
"nodes": [
  ["pdb",   680, 690, "store", "Photos DB",     "Photos Core", { "dur": "sot",       "tag": "Postgres" }],
  ["redis", 280, 375, "store", "Session Cache", "API Platform",{ "dur": "ephemeral", "tag": "Redis" }],
  ["s3",    500, 690, "store", "Object Store",  "Media Ingest",{ "dur": "sot",       "tag": "S3" }]
],
"edges": [
  ["photos", "pdb",   "sql",   0, "exactly-once", "strong", 0, "p0", "INSERT photos(owner_id, geom, ...)"],
  ["gw",     "redis", "cache", 0, "best-effort",  "stale",  0, "p1", "GET/SET sess:{tok} EX 3600"],
  ["upload", "s3",    "bytes", 0, "exactly-once", "strong", 0, "p0", "PUT orig/{id} (octet-stream)"]
]
```

Add a `derived` store the moment you find its rebuild path — e.g. an Elastic index fed by a reindex
consumer off the photos table: `["es", 330, 600, "store", "Search Index", "Search", { "dur": "derived", "tag": "Elastic" }]`.

## Confidence + degradation

Migrations and IaC are ground truth — a store backed by a `CREATE TABLE` or an `aws_db_instance` is a
fact, mark it confirmed. The `dur` class is the soft part: it's a judgement from how the store is used,
and use is spread across the codebase. When you can't trace the write path, **prefer the safer/looser
label** — treat an unknown store as `sot` rather than risk badging a real source of truth as throwaway
(a `derived` tag tells DR "feel free to drop it"; being wrong there is the dangerous direction). Note
any `dur` you inferred rather than confirmed in the handoff (MODEL.md → "Honesty") — a trusted-but-wrong
durability badge lies with the authority of the diagram.
