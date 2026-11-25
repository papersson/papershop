# Extract temporal — `sequence` + `lifecycle`

The two TEMPORAL siblings answer "what happens in time?". Everything else in the model is a static
graph; these two are the only views that show **order**. They are also the hardest to auto-extract:
there is rarely one source file that declares them, so they lean on tracing call paths and on a human
pointer. Treat this module as **best-effort / semi-assisted**, not deterministic.

Two independent outputs, from `MODEL.md`:

- `sequence` — the ONE request that matters, traced hop-by-hop across services (incl. its async tail).
- `lifecycle` — the central entity's state machine (incl. error / retry / terminal states).

They are independent: extract either, both, or neither. **If you cannot identify a defining request,
omit `sequence`; if there is no stateful central entity, omit `lifecycle`** — the tab simply
disappears. Inventing a plausible-but-fictional one is the worst outcome (`MODEL.md → Honesty`).

---

## SEQUENCE — the critical path in time

### Pick the ONE request

A system exists to do one thing; the sequence view draws that thing. Not a CRUD read, not a health
check — the **defining operation** (for a photo service: upload-and-publish; for a checkout: place
order; for a pipeline: ingest-an-event). Choose it by signal:

- The operation the README / service name is about.
- The entry point with the most downstream hops, async work, or fan-out.
- The path that touches the most `nodes` you already mapped (it traverses the system).

If two candidates tie, or nothing obviously dominates, **ask the user**: "Cartograph draws one
critical request as the sequence view — is it `POST /photos`, or something else?" One question beats a
guessed trace.

### Trace it, hop by hop

Start at the **entry point** — an HTTP handler, an RPC method, or a message consumer — and follow the
calls it makes, in source order, across service boundaries. Each call (and each notable return) is one
message. The `messages` tuple from `MODEL.md`:

```
[fromId, toId, label, isReturn, isAsync]   // ordered top→bottom; flags 0/1
```

- `label` is the operation on the wire — reuse the edge `payload` style (`POST /photos`,
  `PUT original`, `enqueue(process)`).
- `isReturn=1` for a response/ack flowing back (renders dashed-back); `isAsync=1` for fire-and-forget
  (enqueue, deliver, push — renders dashed).
- **The async tail is the point.** Don't stop at the `202 Accepted`. Keep going: the enqueue, the
  worker claiming the job, the writes it makes, the push back to the client. That unhappy/deferred tail
  is what a static map can't show and why this view earns its place.

`participants` are the lifelines — the services and stores the request touches, left→right in roughly
call order. The tuple is `[id, label, role]`; `role` colours the header
(`client svc store broker async notify`). Reuse your `nodes` ids where they line up.

### Worked example — a handler trace → tuples

```python
# upload_service.py — entry point for the defining request
@router.post("/photos")              # client → gateway → here
def create_photo(file, meta):
    blob.put(original_key, file)     # → object store, sync
    db.insert(Photo(status="stored"))# → db, sync
    queue.enqueue("process", id)     # → broker, async (fire-and-forget)
    return Accepted(photo_id=id)     # → back to client, 202

# worker.py — the async tail
def on_process(id):                  # broker delivers the job
    img = blob.get(original_key)     # → object store
    blob.put(thumb_key, thumbnail(img))
    db.update(id, tags=…, status="live")
    push.notify(owner, "ready")      # → notifier, async
```

→ participants and messages (matches `model.example.json` exactly):

```jsonc
"sequence": {
  "participants": [
    ["client","Client","client"], ["gw","Gateway","svc"], ["up","Upload","svc"],
    ["blob","Blob","store"], ["q","Queue","broker"], ["wk","Worker","async"],
    ["db","DB","store"], ["push","Push","notify"]
  ],
  "messages": [
    ["client","gw","POST /photos",        0,0],
    ["gw","up","forward (authed)",        0,0],
    ["up","blob","PUT original",          0,0],
    ["blob","up","200 OK",                1,0],
    ["up","db","INSERT status=stored",    0,0],
    ["up","q","enqueue(process)",         0,1],   // async hand-off
    ["up","gw","202 Accepted",            1,0],
    ["gw","client","202 + photoId",       1,0],
    ["q","wk","deliver job",              0,1],   // ── async tail begins
    ["wk","blob","GET original",          0,0],
    ["wk","blob","PUT thumbnail",         0,0],
    ["wk","db","UPDATE tags, status=live",0,0],
    ["wk","push","notify(ready)",         0,1],
    ["push","client","APNs / FCM push",   0,1]
  ]
}
```

The request returns `202` to the client halfway down, then the trace keeps going through the broker and
worker. That second half is the value.

---

## LIFECYCLE — the central entity's state machine

### Find the entity's states

Pick the system's central entity (usually the noun the sequence acts on — the `Photo`, the `Order`,
the `Job`). Find its states from the highest-signal source available:

| Source | Find it |
|---|---|
| Enum/`status`/`state` column | migration or ORM model: `status = Column(Enum("stored","live",…))`, a `CHECK status IN (…)`, a Rails enum |
| State-machine library | XState (`createMachine`), AASM (`aasm do … state …`), `transitions`, `statemachine` gems/pkgs |
| Transitions in code | `status = "live"` / `update(status=…)` assignments scattered across handlers |

A declared enum or state-machine config is near-ground-truth. Transitions reconstructed from scattered
assignments are inference — mark them.

### States → nodes, transitions → edges

The `lifecycle` tuples from `MODEL.md`:

```
states:      [id, x, y, color, name, sub, opts?]   // opts.dbl=1 = terminal ring
transitions: [fromId, toId, label, dir]            // dir: "h" horizontal · "v" vertical · "a" auto
```

- `label` on a transition is the **trigger** (`flush`, `enqueue`, `claim`, `timeout / err`,
  `retry ≤3`, `user deletes`) — the event that moves the entity, not the target state name.
- **Include error / retry / terminal states.** `Failed`, `Deleted`, `Cancelled`, `Expired` are where
  the value is; a happy-path-only lifecycle is a list, not a machine.
- Layout: happy path left→right along `y≈200`; failure/terminal states **below** at `y≈420`. Colours
  are CSS vars — `var(--client)` start, `var(--data)`/`var(--async)` working, `var(--live)` success,
  `var(--err)` failure, `var(--muted)` terminal. Mark truly terminal states `{"dbl":1}`.

### Worked example — a status enum + transitions → tuples

```python
class Photo:
    status = Enum("uploading","stored","queued","processing","live","failed","deleted")
    # transitions in code:
    #   uploading → stored   on flush
    #   stored    → queued   on enqueue
    #   queued    → processing on worker claim
    #   processing→ live     on done
    #   processing→ failed   on timeout/err   ;  failed → queued on retry (≤3)
    #   live      → deleted  on user delete
```

→ states and transitions (matches `model.example.json`):

```jsonc
"lifecycle": {
  "states": [
    ["up",200,200,"var(--client)","Uploading","client → server"],
    ["st",420,200,"var(--data)",  "Stored",   "bytes durable"],
    ["qd",640,200,"var(--async)", "Queued",   "awaiting worker"],
    ["pr",880,200,"var(--async)", "Processing","thumbs + tags"],
    ["lv",1110,200,"var(--live)", "Live",      "servable", {"dbl":1}],
    ["fa",880,420,"var(--err)",   "Failed",    "exception"],
    ["dl",1110,420,"var(--muted)","Deleted",   "tombstoned"]
  ],
  "transitions": [
    ["up","st","flush","h"], ["st","qd","enqueue","h"], ["qd","pr","claim","h"],
    ["pr","lv","done","h"],
    ["pr","fa","timeout / err","v"],   // failure drops down
    ["fa","qd","retry ≤3","a"],        // retry loops back up
    ["lv","dl","user deletes","v"]     // terminal
  ]
}
```

The happy row runs `Uploading → … → Live`; `Failed` sits below `Processing` with a retry edge back to
`Queued`, and `Deleted` is the tombstone. Drop those two and you've hidden the only states an operator
gets paged about.

---

## Confidence & degradation

- **Declared = trustworthy.** A lifecycle from a state-machine config or an enum column, and a sequence
  whose every hop traces to a real call, can be asserted plainly.
- **Reconstructed = best-effort.** A trace stitched from reading handlers, or transitions inferred from
  scattered `status =` assignments, is a guess — say so in the handoff and prefer a vaguer-but-true
  label over a precise invented one.
- **No critical request? Omit `sequence`. No stateful entity? Omit `lifecycle`.** A missing tab is
  honest; a fabricated one lies with the authority of the canonical diagram. When you omit a view,
  note it in the handoff (`SKILL.md → Hand off`) so the gap is explicit, not silent.

## Several flows

A system can have more than one materially-different critical path from the same entry point (reject /
accept / clean-pass). For these, emit `sequences: [ {name, participants, messages, dividerIndex?,
dividerLabel?}, … ]` instead of a single `sequence` (MODEL.md) — the view shows a flow selector, one
per `name`. Discipline: still pick the ONE dominant flow first; add an alternate only when it is a
genuinely different path, not a minor branch. The async divider is per-flow — set `dividerIndex` only
on flows that actually cross into async, and omit it on the ones that don't.
