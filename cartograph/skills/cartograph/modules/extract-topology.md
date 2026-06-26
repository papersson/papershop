# Extract: topology → the skeleton (`nodes` + `edges`)

This module builds the load-bearing frame of the model: the services, datastores, and brokers
(`nodes`) and the calls between them (`edges`). Everything else — transports, schemas, durability,
teams, lineage — hangs off this frame in later modules. Get the skeleton right and the rest is
decoration; get it wrong and every layer lies.

Your output is `nodes` and `edges` tuples exactly as `MODEL.md` defines them:

```
NODES  [id, x, y, role, name, team, opts?]
EDGES  [from, to, tx, async, delivery, consistency, _, crit, payload]
```

At this stage you fill `id, role, name` and place `x, y`; you sketch each edge's `from, to, tx` and a
rough `payload`. Leave `team`, `dur`, schemas, and precise delivery/consistency for the modules that
own them — but write a best guess rather than a hole, and mark guesses (see Confidence).

## Where topology lives — read in this order

Highest-signal (ground-truth) first. Stop climbing the moment a source answers the question.

| Source | Find it | What it gives you |
|---|---|---|
| **docker-compose** | `docker-compose*.yml`, `compose.yaml` | one node per `service:`; edges from `depends_on`, `links`, and env connection strings |
| **k8s + helm** | `glob **/*.yaml` with `kind: Deployment\|StatefulSet\|Service`; `helm/**/templates`, `values.yaml` | one node per Deployment/StatefulSet; `Service` names are the DNS targets other pods dial |
| **service mesh** | Istio `VirtualService`/`DestinationRule`, Linkerd `ServiceProfile`, Consul `service-defaults` | authoritative caller→callee routes and retry/timeout policy |
| **Procfile / systemd** | `Procfile`, `*.service` units | each line/unit is a process node (`web`, `worker`, `scheduler`) |
| **Terraform / IaC** | `glob **/*.tf`; `aws_ecs_service`, `google_cloud_run_service`, `aws_db_instance`, `aws_sqs_queue`, `aws_msk_cluster` | managed services + datastores + brokers as nodes; security-group / IAM refs hint edges |
| **monorepo package graph** | `package.json` workspaces, `go.mod`, `Cargo.toml`, `pnpm-workspace.yaml`, Nx/Bazel targets | which package depends on which — a build-time edge, weaker than a network call |
| **import graph** | `rg "import\|require\|from .* import"` per service entrypoint | last-resort inference of who calls whom (low confidence) |

Read each suspected file **in full** — a compose file's `environment:` block is where half the edges
hide (a `DATABASE_URL` pointing at another service is an edge even with no `depends_on`).

## Deriving `nodes`

One service / process / datastore / broker → one node.

**`role`** (field 3) — classify by *what the thing is*, not what it's called:

- `client` — the caller you don't own: browsers, mobile apps, external partners, a load generator.
- `edge` — the ingress tier: CDN, API gateway, reverse proxy, load balancer, BFF.
- `svc` — anything that runs your code and serves requests: app servers, workers, cron jobs.
- `store` — holds state: Postgres, MySQL, Redis, S3/blob, Elastic, a cache. (Durability is set later.)
- `broker` — moves messages: Kafka, RabbitMQ, SQS/SNS, NATS, Pub/Sub. One bus often becomes a single
  wide `bus:true` node many services drop into — don't make six Kafka nodes.

Heuristics: a compose `image:` of `postgres`/`redis`/`rabbitmq` ⇒ `store`/`broker`. An nginx/traefik/
envoy image at the front ⇒ `edge`. A k8s `StatefulSet` is usually a `store`. Your own `build:` context
or a Procfile `web:`/`worker:` ⇒ `svc`.

**`id`** (field 0) — short, stable, edge-referenced: the compose service key or k8s Deployment name,
slugged (`api-gateway` → `gw`, `photo-metadata` → `photos`). **`name`** (field 4) is the human label.

**`x, y`** (fields 1–2) — place by data-flow per `DESIGN.md`: sources top-left, sinks bottom-right,
the broker as a horizontal spine across the middle, ~150px between centres, banded by role
(client → edge → svc → broker → store, left to right). Hand-placed beats `null` auto-layout; place the
nodes that matter and `null` the rest. Leave `team` (field 5) for `extract-ownership`; leave `opts`
(`dur`, `tier`, `tag`) for the datastore/contract modules. A bare node is `["s3", 500, 690, "store", "Object Store", ""]`.

## Deriving `edges`

A dependency you can name → one edge: a `depends_on`, a mesh route, a connection string, a mounted/
injected client, a service-discovery lookup. **Direction is caller → callee** (the one that initiates),
*not* the data direction — a service reading from Postgres is `svc → store`.

Spot the **`tx`** (field 2) from the *target's nature plus the wire*, enough to colour the base layer;
the exact contract is `extract-contracts`' job:

- target is a SQL store, or the client lib is `pg`/`psycopg`/`sqlx`/`gorm` → `sql`
- target is Redis/memcached, used as a cache → `cache`
- target is a broker (Kafka/SQS/Rabbit/NATS) → `kafka`, and set `async = 1`
- HTTP/JSON, REST, GraphQL, a `:80`/`:8080` port → `rest`
- a `:50051` port, a `.proto` client, `grpc.Dial` → `grpc`
- raw object/blob transfer (S3 `PutObject`, a file copy) → `bytes`

Set **`async`** (field 3): `1` for fire-and-forget / queue publishes / event consumers (renders
dashed), `0` for request/response. At this stage write conservative defaults for the rest —
`delivery="exactly-once"`, `consistency="strong"`, `_=0`, `crit="p1"` for sync RPC; for a broker edge
`delivery="at-least-once"`, `consistency="eventual"`. The events module corrects these. **`payload`**
(field 8) starts as a rough signature (`"reads photos"`, `"publishes photo.uploaded"`) and is sharpened
once the contract source is read.

## Worked example — a compose file → tuples

```yaml
# docker-compose.yml
services:
  web:
    build: ./web
    ports: ["80:8080"]
    depends_on: [api]
  api:
    build: ./api
    environment:
      DATABASE_URL: postgres://orders:***@db:5432/orders
      REDIS_URL: redis://cache:6379
    depends_on: [db, cache, broker]
  db:    { image: postgres:16 }
  cache: { image: redis:7 }
  broker:{ image: rabbitmq:3 }
```

Five `service:` keys → five nodes; `web` fronts traffic so it's `edge`. Placed by flow, brokers
mid-band, stores bottom-right:

```jsonc
"nodes": [
  ["web",   95, 130, "edge",   "Web",       ""],
  ["api",  340, 130, "svc",    "API",       ""],
  ["broker",560, 360, "broker","RabbitMQ",  "", { "bus": true }],
  ["db",   780, 600, "store",  "Orders DB", "", { "tag": "Postgres" }],
  ["cache",560, 600, "store",  "Cache",     "", { "tag": "Redis" }]
]
```

Edges, caller→callee. `web→api` from `depends_on`; the other three from `api`'s env + `depends_on`:

```jsonc
"edges": [
  ["web", "api",    "rest",  0, "exactly-once",  "strong",   0, "p1", "HTTP /orders"],
  ["api", "db",     "sql",   0, "exactly-once",  "strong",   0, "p1", "orders table"],
  ["api", "cache",  "cache", 0, "best-effort",   "stale",    0, "best","GET/SET order:{id}"],
  ["api", "broker", "kafka", 1, "at-least-once", "eventual", 0, "p1", "publishes order.created"]
]
```

Note `api→broker` is `async=1` (dashed) and the `DATABASE_URL`/`REDIS_URL` env vars became edges even
though only `depends_on` listed them — the connection string *is* the edge.

## Confidence & provenance

Tier every element by how you learned it; carry the low-confidence ones into the handoff:

- **Ground truth** — compose, k8s/helm, mesh config, Terraform: the edge is declared. Assert it.
- **Inferred** — derived only from an import graph or a guessed client call: it *might* be dead code or
  a build-time-only dependency. Mark it (a vaguer-but-true `payload` like `"calls api (inferred)"`),
  and flag it for the validation pass. Per `MODEL.md` → Honesty, a trusted-but-wrong edge is the worst
  outcome.

Package-graph edges are build-time, not runtime — include them only if they reflect an actual call,
and prefer the runtime evidence when the two disagree.

## Degradation — no topology sources at all

A plain app repo with no compose/k8s/IaC still has a skeleton; reconstruct it and mark the whole thing
inferred:

1. Find entrypoints (`main.*`, `cmd/`, `index.*`, framework bootstrap, Procfile) — each long-running
   one is a `svc` node.
2. Grep the dependency manifest and code for **client libraries**, which name the stores/brokers:
   `pg`/`psycopg`→Postgres `store`; `redis`/`ioredis`→Redis `store`; `kafkajs`/`sarama`/`confluent`→
   Kafka `broker`; `boto3 s3`/`aws-sdk S3`→blob `store`; an HTTP client with a hard-coded base URL →
   `rest` edge to that host.
3. Read config (`.env.example`, `config/*.yaml`, `settings.py`) for connection strings — same rule as
   compose: each URL is an edge.
4. Place, label, and set every node/edge as inferred; say so in the handoff.

One honest inferred skeleton beats no diagram — but never let it pass as ground truth.

## Current-state vs. planned

A repo often holds a designed-but-not-yet-wired path: an edge whose handler only *logs*
(`log.info("would call …")`), a call gated behind a disabled feature flag, a service defined in IaC
with no live traffic, a stub/`TODO` client. Do **not** draw these as live — that is the live-vs-planned
accuracy bug. Mark them planned: node `opts.state:"planned"` and edge field-6 `state:"planned"`
(MODEL.md), which renders them ghosted with a badge, so a target architecture shows honestly beside what
is actually wired. When unsure whether a path is live, treat it as planned and confirm in Validate.
