# Extract contracts — edge `tx` + `payload`

Topology (`extract-topology.md`) gives you the edges as bare `[from, to]` pairs. This module fills the
two fields that say **how** they talk and **what** crosses the wire: `tx` (transport) and `payload` (a
short wire-contract signature). Both land in `EDGES` from `MODEL.md`:

```
[from, to, tx, async, delivery, consistency, _, crit, payload]
                ▲                                          ▲
             this module                              this module
```

The renderer paints `tx` as the edge colour and shows `payload` verbatim in the drill panel when you
click an edge. Your job: read the interface-definition sources, set `tx`, and distil each declared
contract into a one-line `payload`.

## Sources — where the contract is declared

Interface definitions are the highest-signal source here: a declared contract is **ground truth**, not
inference. Find them before reading code.

| Source | Find it | Describes |
|---|---|---|
| OpenAPI / Swagger | `openapi.yaml`, `swagger.json`, `**/openapi/*.yml`, `@openapi`/springdoc annotations | REST/JSON paths, request + response bodies |
| protobuf / gRPC | `*.proto` (`service`, `rpc`, `message`) | gRPC methods, request/response messages |
| GraphQL SDL | `*.graphql`, `*.graphqls`, `schema.graphql`, `type Query`/`Mutation` | GraphQL operations + types |
| AsyncAPI | `asyncapi.yaml`, `**/asyncapi/*` | event channels, message schemas, topics |
| JSON Schema / Avro | `*.schema.json`, `*.avsc`, schema-registry exports | event/record payload shapes |

```bash
fd -e proto -e graphql -e graphqls; \
rg -l "openapi:|swagger:|asyncapi:" --glob '*.y*ml'; \
fd -e avsc -e 'schema.json'
```

Read each matching file **in full** — the contract is the point, and partial reads miss the
request/response split.

## Mapping the transport → `tx`

`tx` is one of `rest grpc kafka sql bytes cache`. Pick by the source kind, not by guessing:

| Source / signal | `tx` |
|---|---|
| OpenAPI path, GraphQL operation, plain HTTP/JSON client | `rest` |
| `.proto` `rpc`, gRPC stub/channel | `grpc` |
| AsyncAPI channel, Kafka producer/consumer, pub/sub topic | `kafka` |
| SQL query, ORM call, DB driver | `sql` |
| Object-storage GET/PUT (S3, GCS, blob) | `bytes` |
| Redis / memcached get/set | `cache` |

GraphQL collapses to `rest` (it is HTTP/JSON on the wire); the GraphQL-ness lives in the `payload`
string (`GraphQL uploadPhoto(...)`). Async transports (`kafka`) almost always also set `async=1`,
`delivery=at-least-once`, `consistency=eventual` — see `extract-events.md`.

## Building `payload` — a short signature

`payload` is terse drill content, not a schema dump. A rich proto message or OpenAPI body becomes a
**one-liner** that names the operation and the shape that matters. Derive it per source:

| Source | Distil to | Example |
|---|---|---|
| gRPC `rpc Get(GetReq) returns (Photo)` | `Method(keyArgs)→ReturnType` | `GetPhoto(id)→Photo` |
| OpenAPI `POST /photos` body `{file,meta}` | `VERB /path {keyFields}` | `POST /photos {file,meta}` |
| GraphQL `mutation uploadPhoto(file,meta)` | `GraphQL op(args)` | `GraphQL uploadPhoto(file, meta)` |
| AsyncAPI / Kafka message + schema version | `topic vN` (+ key hint) | `photo.published v4` |
| SQL / ORM write | `VERB table(cols…)` | `INSERT photos(owner_id, geom, …)` |
| Object storage | `VERB key (content-type)` | `PUT orig/{id} (octet-stream)` |
| Cache | `OP key-pattern` | `GET/SET sess:{tok}` |

Rules: keep the **operation name** and **2–4 load-bearing fields**; drop the rest with `…`. Show the
return type only when it carries meaning (`→Photo`, `→{user_id,scopes}`). For events, the **schema
version** is the most useful single token — always include it if the registry/`.avsc` declares one.

## Worked example

A `.proto` and an OpenAPI path, and the edge tuples they produce.

```protobuf
// photos.proto
service Photos {
  rpc GetPhoto(GetPhotoRequest) returns (Photo);
  rpc DeletePhoto(DeletePhotoRequest) returns (google.protobuf.Empty);
}
message GetPhotoRequest { string id = 1; }
```

```yaml
# openapi.yaml
paths:
  /photos:
    post:
      requestBody: { content: { multipart/form-data:
        { schema: { properties: { file: {}, meta: {} } } } } }
      responses: { '202': { description: accepted } }
```

→ the gateway-to-service edges (topology supplied `from`/`to`; this module set fields 2 and 8):

```jsonc
["gw", "photos", "grpc", 0, "exactly-once", "ryw",    0, "p0", "GetPhoto(id)→Photo"],
["gw", "photos", "grpc", 0, "exactly-once", "strong", 0, "p0", "DeletePhoto(id)→∅"],
["clients", "gw", "rest", 0, "exactly-once", "strong", 0, "p0", "POST /photos {file,meta}"]
```

The proto's two `rpc`s become two terse `payload`s; the multipart OpenAPI body collapses to its two
named fields. `GetPhoto` is read-mostly (`ryw`); `DeletePhoto` mutates (`strong`) — those fields come
from `extract-topology.md` / your read of the semantics, not from this module.

## Confidence

- **Declared contract = ground truth.** A `tx`/`payload` lifted from a `.proto`, OpenAPI, GraphQL SDL,
  or AsyncAPI file is canonical — assert it plainly.
- **Guessed from code = lower confidence.** A `payload` you reconstructed by reading a handler's
  arguments (no IDL) is a best-effort guess. Mark it (e.g. trailing `?` or a vaguer label) and note it
  in the handoff. Per `MODEL.md → Honesty`, a precise-but-wrong signature is worse than a
  vaguer-but-true one — write `POST /photos {…}` over an invented field list.

## Degradation — no IDL present

Many repos ship no interface definitions. Infer `tx` from the **client libraries** at the call site,
and write a best-effort `payload`, marked:

| Code signal | Infer `tx` | Best-effort `payload` |
|---|---|---|
| `KafkaProducer(...).send("photo.published", …)` | `kafka` | `photo.published?` (no schema → no version) |
| `httpx`/`fetch`/`axios` `POST(url, body)` | `rest` | `POST /photos {…}?` from the body var |
| ORM `session.add(Photo(...))` / `db.query(...)` | `sql` | `INSERT photos(…)?` from the model fields |
| `boto3 s3.put_object(Bucket, Key)` | `bytes` | `PUT {key}?` |
| `redis.get/set(key)` | `cache` | `GET/SET {key}?` |

Read the call site in full to recover the real method/path/topic and the actual argument names — an
inferred-but-specific payload from a real call beats a placeholder. Always flag inferred edges so
validation (`SKILL.md → Validate`) and the handoff can separate them from the declared ones.
