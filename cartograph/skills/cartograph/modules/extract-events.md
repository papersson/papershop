# Extract: async messaging → the event-bus spine

Load this module when the system has async messaging: a Kafka/Pulsar cluster, an SNS/SQS/EventBridge
mesh, NATS, RabbitMQ, or a transactional outbox. Its job is to find the **topics**, their **producers**
and **consumers**, and render them as the diagram's middle spine — one wide broker node with async edges
dropping in from producers above and drawn out to consumers below (DESIGN.md → Layout). It writes the
`bus:true` broker NODE and the `async:1` EDGES described in MODEL.md.

If there is no async messaging, **omit the bus entirely** and say so in the handoff. A lone broker node
with nothing flowing through it is a lie about the architecture. The events feed nothing; don't draw them.

## Where the truth lives (highest signal first)

| Source | Gives you | Confidence |
|---|---|---|
| **Schema registry** (Confluent/Apicurio): Avro/Protobuf/JSON schemas + `subject` + version | topic name, payload shape, **version** | ground-truth |
| **AsyncAPI spec** (`asyncapi.yaml`) | channels, who publishes/subscribes, message schemas | ground-truth |
| **Broker config / IaC**: Terraform `kafka_topic`, `aws_sns_topic` + `aws_sns_topic_subscription`, `aws_sqs_queue`, EventBridge rules, RabbitMQ `bindings` | topics/queues exist, routing wiring | ground-truth (topology), but not who in code uses them |
| **Pub/sub call sites in code**: `producer.send(...)`, `consumer.subscribe(...)` | producer vs consumer direction | inferred — lower confidence |
| **Outbox table**: an `outbox`/`events` table + a relay/CDC publisher | exactly-once-ish producer, the delivery semantics | mixed (table is ground-truth, relay wiring often inferred) |

Prefer the registry + AsyncAPI: they give you the topic **and** the version **and** the schema without
guessing. Fall back to call-site inference only to fill gaps, and mark those edges low-confidence in the
handoff.

## Finding producers vs consumers in code

Direction is the one thing you must get right — it decides which side of the bus the edge sits on. Grep
per ecosystem, then read each hit to confirm the topic literal:

- **Kafka (Java/Kotlin)** — producer: `KafkaTemplate.send(`, `producer.send(new ProducerRecord(`;
  consumer: `@KafkaListener(topics=`, `consumer.subscribe(`.
- **Kafka (Node/Go/Python)** — `producer.send({topic` / `producer.produce(` vs `consumer.subscribe({topic` /
  `@app.agent(topic)` (Faust) / `reader.ReadMessage` (segmentio).
- **Pulsar** — `client.newProducer().topic(` vs `client.newConsumer().topic(...).subscribe()`.
- **NATS** — `nc.Publish(subj,` / `js.Publish(` vs `nc.Subscribe(subj,` / `js.Subscribe(`.
- **RabbitMQ** — `channel.basicPublish(exchange,routingKey,` vs `basicConsume(queue,` plus the
  `queueBind(queue, exchange, routingKey)` that ties them.
- **SNS/SQS/EventBridge** — `sns.publish({TopicArn` / `eventbridge.putEvents` vs an SQS poller
  (`sqs.receiveMessage`) or a Lambda `EventSourceMapping` / EventBridge rule `target`.

A service that both publishes topic A and subscribes to topic B gets **two** edges (one each direction) —
that is normal and the layout handles it.

## Recovering topic + schema + version from the registry

The `payload` field on each async edge is the topic name plus version, e.g. `photo.published v4`. Get it
from the registry, not the code string:

```bash
# Confluent schema registry: list subjects, then the latest version of one
curl -s $REGISTRY/subjects | jq -r '.[]'
curl -s $REGISTRY/subjects/photo.published-value/versions/latest \
  | jq '{subject, version, type, schema: (.schema|fromjson|.name)}'
# → { "subject": "photo.published-value", "version": 4, "type": "AVRO", "name": "PhotoPublished" }
```

The `-value` suffix is the convention for the message body (vs `-key`). The version number is the `v4`.
For Protobuf, read the `.proto` + its registry subject; for raw `.avsc` files in-repo, the topic is
usually the filename/`namespace` and you carry the file's version or git history as the version.

## Modeling the bus

**One broker node, `bus:true`.** Every topic shares it; do not make a node per topic (that rebuilds the
hairball the spine exists to tame). Place it mid-canvas as the horizontal spine.

```jsonc
// NODE — [id, x, y, role, name, team, opts]
["kafka", 640, 360, "broker", "kafka — event backbone · Avro + registry", "Data Platform",
 { "dur": "ephemeral", "bus": true }]
```

`dur:"ephemeral"` because the broker is a transport, not a source of truth (the topic retains, it doesn't
own). Tag the engine in the name or via a `tag`.

**Each producer→bus and bus→consumer is its own async edge.** Field meanings from MODEL.md → EDGES:
`tx:"kafka"` (violet, the always-on transport colour for the bus), `async:1` (dashed), and `payload` =
topic + version. Defaults are `delivery:"at-least-once"`, `consistency:"eventual"` — correct for the vast
majority of pub/sub.

```jsonc
// EDGES — [from, to, tx, async, delivery, consistency, _, crit, payload]
["photos", "kafka", "kafka", 1, "at-least-once", "eventual", 0, "p0", "photo.published v4"],
["kafka", "search", "kafka", 1, "at-least-once", "eventual", 0, "p1", "photo.published"],
["kafka", "feed",   "kafka", 1, "at-least-once", "eventual", 0, "p1", "photo.published · deleted"]
```

Producer edges carry the full `topic vN`; consumer edges can shorten to just the topic(s) they read,
since the version is already stated on the producer side. When one consumer reads several topics, fold
them into one edge (`tagged · published`) rather than drawing five near-parallel lines.

**When the defaults are wrong** — change them, and only then:
- **Exactly-once / transactional outbox / Kafka transactions** (`enable.idempotence=true` + an outbox
  relay, or `read-committed` EOS) → `delivery:"exactly-once"`. The outbox table also makes the *producer*
  a source of truth for the event, worth a note.
- **Fire-and-forget** (no retry, no DLQ, metrics/notifications you can drop) → `delivery:"best-effort"`.
- **Consumer reads a compacted/keyed topic as current state** → `consistency:"stale"` rather than
  `eventual`, because it's reading a snapshot, not a stream of changes.

## Worked example

Code found by grep:

```java
// upload-service — producer
kafkaTemplate.send("photo.published",
    new PhotoPublished(id, urls, tags));          // → producer of photo.published

// search-indexer — consumer
@KafkaListener(topics = "photo.published")
void index(PhotoPublished e) { ... }              // → consumer of photo.published
```

Registry lookup: `photo.published-value` is at **version 4**, Avro record `PhotoPublished`.

Yields one bus node and two async edges:

```jsonc
"nodes": [
  ["kafka", 640, 360, "broker", "kafka — event backbone", "Data Platform", { "dur": "ephemeral", "bus": true }]
],
"edges": [
  ["upload", "kafka",  "kafka", 1, "at-least-once", "eventual", 0, "p0", "photo.published v4"],
  ["kafka",  "search", "kafka", 1, "at-least-once", "eventual", 0, "p1", "photo.published"]
]
```

## Confidence & degradation

- **Registry + AsyncAPI are ground-truth** — topic, version, schema, and (for AsyncAPI) direction all
  come from one declared source. Trust those edges.
- **Call-site inference is lower-confidence.** A `send(...)` proves a producer exists, but a topic name
  built from a variable or config key may be wrong; the version is unknown without the registry (use `v?`
  or omit the version rather than guessing one). Mark these in the handoff and let validation (SKILL.md →
  Validate) confirm them against the code.
- **No async messaging found ⇒ no bus.** Don't synthesize one from a single in-process `EventEmitter` or a
  cron job — that's not a message bus. Omit the broker node, note "no async messaging" in the handoff, and
  the Map is honestly synchronous.
</content>
</invoke>
