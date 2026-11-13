# UI workload, with Bombadil

Bombadil is property-based testing for web and terminal interfaces. It explores the interface by
itself and checks properties written as temporal formulas. It runs locally and in CI; running it
inside Antithesis is optional. Facts below are for version 0.7.10 (`refs/tools.md`).

## Start with the defaults

```
npm install --save-dev @antithesishq/bombadil
npx bombadil browser test --headless --exit-on-violation --time-limit=1m https://your-app.example
npx bombadil terminal test --time-limit=1m your-cli --arg value
```

With no specification, the default properties and action generators run. For a browser they
include "no uncaught exceptions", which alone finds real bugs. Do this before writing anything.

## Then write a specification

A specification is a TypeScript or JavaScript module that exports properties and action
generators. Re-export the defaults, then add your own.

```typescript
import { extract, always } from "@antithesishq/bombadil";
export * from "@antithesishq/bombadil/browser/defaults";

const notificationCount = extract((state) =>
  state.document.body.querySelectorAll(".notification").length);

export const maxNotificationsShown = always(() => notificationCount.current <= 5);
```

- **Extractors** read values from the page or terminal state.
- **Formulas** combine them over time: `always(x)` for safety, `eventually(x)` for liveness,
  `next(x)` for the following state.
- **Action generators** say what the explorer may do. Add custom ones for flows the defaults
  would not find.

Map each property in the catalog that is visible through the interface to one exported formula,
named so the violation report reads as a sentence.

## On a violation

Bombadil prints the violated formula, the time it failed, and two commands: one to inspect the
trace (with screenshots) and one to reproduce it with `--reproduce`. Reproduction must use the
same options as the original run, and is not guaranteed to succeed. A `shrink` command searches
for a shorter trace; it is marked experimental.

## Limits

Only what the interface shows can be checked. A value that is wrong in a store and never rendered
is invisible here; that is the audit's job.
