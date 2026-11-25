# domain — the vocabulary, the source of truth, and what's buildable

Mid-level index (progressive disclosure). Enter when the deciding uncertainty is what the words
actually mean, which system to believe, or whether the data you'd build on exists at all.

## Leaves
- `ubiquitous-language.md` — the real, contested vocabulary; the homonyms and synonyms that become
  field names and seam candidates. [CORE]
- `systems-of-record.md` — which system creates each entity, which holds stale copies, where they
  disagree. The single-source-of-truth myth, refused. [CORE]
- `integration-reality.md` — what each system actually exposes, and what the data quality really is.
  Buildability, before design. [CORE]

## Fit
Third stop in the SKILL.md default order, but often the first you descend on an ops tool: more builds
die on "the words mean three different things" or "nobody can say which system to trust" than on
anything the as-is blueprint catches. **One of language or source-of-truth is almost always the
buildability-deciding uncertainty** — never skip both. Integration-reality decides whether the design
is even possible to ship and where access exists, Claude can run the feasibility probe directly.

These three artifacts **feed** the data model and never draw it. They surface where the language
fractures and where authority is contested, and leave naming the bounded contexts to architecture.
Mark every output here **"input to architecture, not the design,"** hand it over, and stop. If you
find yourself drawing tables of classes or services, you have crossed the handoff.
