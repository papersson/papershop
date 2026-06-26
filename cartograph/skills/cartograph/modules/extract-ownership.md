# Extract ownership → `team`

Fills slot 5 of every NODES tuple `[id, x, y, role, name, team, opts?]` — the owning team. It is
**always** rendered as the node's subtitle and it powers the Team scan layer, so every node needs a
value even when you have to infer one. Also sets `opts.ddd` (bounded context), which defaults to `team`.

## Why this matters on the diagram

`team` is the only field that overlays the org onto the architecture. The Team layer recolours the graph
by owner, so cross-team **edges** light up — and those edges are where the coupling, the API contracts
that need negotiating, and the on-call handoffs live. An edge inside one team is cheap to change; an edge
that crosses a team boundary is a meeting. Getting `team` right is what turns a box-and-arrow picture into
a map of who you page at 3am.

## Sources, best first

1. **CODEOWNERS** (`.github/CODEOWNERS`, `.gitlab/CODEOWNERS`, `CODEOWNERS`, `docs/CODEOWNERS`).
   Ground-truth: it maps path globs → owning team/handle, and it's enforced on PRs so it stays current.
   This is the one to want.
2. **Service catalog** — Backstage `catalog-info.yaml` (`spec.owner`), OpsLevel, a `service.yaml`. An
   explicit per-service owner, usually a team slug. As trustworthy as CODEOWNERS, often cleaner names.
3. **Monorepo package metadata** — `package.json` (`author`/custom `maintainers`), `pyproject.toml`,
   `go.mod` module path, Bazel `BUILD` owner tags, `OWNERS` files (Kubernetes/Chromium style).
4. **Directory structure** — top-level dirs as teams (`services/photos/…` ⇒ team "Photos"). A decent
   default when nothing above exists, but it encodes folder layout, not the org chart. Mark it inferred.
5. **Git history** — dominant author or author's team over a path. A **weak** fallback only: it tracks who
   last touched code, not who owns it, and skews to whoever did the big refactor. Use to break ties, mark it.

## Mapping a node to its team

A node usually corresponds to a service path or a package. Resolve in order:

1. **Match the node's path/package against CODEOWNERS globs.** Last matching rule wins (CODEOWNERS is
   last-match-takes-precedence, like `.gitignore`). Map the owning handle (`@org/photos-core`) to a short
   human name (`Photos Core`) — keep a tiny handle→name table and reuse it across the model.
2. **Fall back to the owning directory** — the nearest ancestor dir that reads as a team boundary.
3. **Last resort: infer and mark.** Name it from the closest signal (dir, dominant committer) and record
   it as low-confidence in the handoff. Never leave `team` blank — an honest guess beats an empty subtitle.

When a node spans owners (a shared DB written by three services), attribute it to the team that owns its
**schema/source of truth**, not every writer. A store's team is usually the service that owns its writes.

## The `ddd` opt — bounded context

`opts.ddd` is the bounded-context label shown in the drill panel. It **defaults to `team`**, so only set it
when the context differs from the team:

- **Same as team** (the common case): omit it. The renderer uses `team`.
- **Coarser than team**: several teams inside one context — set `ddd` to the shared context. E.g. teams
  "Photos Core" and "Media" both live in the `Photos` bounded context ⇒ give both `{ "ddd": "Photos" }`.
- **Finer than team**: one team owning two contexts — set `ddd` per node to the narrower context.

Source `ddd` from a service catalog's `system`/`domain` field, a domain-named top-level dir, or the
event/schema namespace (`photos.*`, `billing.*`). If you have no domain signal, leave it — `team` is fine.

## Worked example

CODEOWNERS:

```
# .github/CODEOWNERS — last match wins
*                       @acme/platform
/services/upload/       @acme/media-ingest
/services/media/        @acme/media
/services/photos/       @acme/photos-core
/services/sharing/      @acme/sharing
/infra/cdn/             @acme/edge-infra
```

Repo tree:

```
services/upload/   services/media/   services/photos/   services/sharing/   infra/cdn/   services/billing/
```

Resolved nodes (slot 5 = `team`; note `billing` falls through to the `*` default, and `media`+`photos`
share a `Photos` bounded context so they carry `ddd`):

```jsonc
["upload",  500, 250, "svc",   "Upload",         "Media Ingest"],
["media",   880, 150, "svc",   "Media Proc.",    "Media",        { "tier": "p1", "ddd": "Photos" }],
["photos",  690, 150, "svc",   "Photo Metadata", "Photos Core",  { "tier": "p0", "ddd": "Photos" }],
["sharing", 690, 300, "svc",   "Sharing",        "Sharing"],
["cdn",      95, 250, "edge",  "CDN",            "Edge Infra",   { "tag": "Fastly" }],
["billing", 1180,420, "svc",   "Billing",        "Platform"]   // inferred via `*` — mark low-confidence
```

## Confidence & degradation

- **CODEOWNERS / catalog ⇒ trust it.** State "ownership from CODEOWNERS" in the handoff.
- **Single-team repo:** use the one team name everywhere, or the org name if there's no team granularity
  (`"Acme"`). Don't manufacture fake sub-teams — a uniform Team layer is the honest picture.
- **Inferred ownership** (dir or git history): mark it. Per MODEL.md → "Honesty", a `team` badge that is
  trusted-but-wrong lies with the diagram's authority; a vaguer-but-true label is better. If you genuinely
  can't tell, a coarse true label (`"Platform"`, the org name) beats a precise guess.
