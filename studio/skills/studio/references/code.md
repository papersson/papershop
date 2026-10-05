# Explain code by constructing the need

This is an explainer format, using the normal proposal/build/review workflow. Begin with the
smallest meaningful runnable program; run it, show a limitation, and add the idea that resolves
it. File order is useful only when it serves that reasoning. Signal key ideas, mute plumbing,
and move language detail into optional sidebars. An empty main is an example, not a requirement.
For exhaustive coverage, map source regions to the main story, sidebar or companion reference.

## Recorded program steps

`studio steps VIDEO STEPS.json` accepts version 1 manifests. Paths on the right of `files`,
`source` and `inputs` are relative to the manifest; keys are paths inside a clean scratch project.
Commands are argv arrays, with no implicit shell. Every step gets a fresh directory. Commands can
still access the host: this is working-directory isolation, not a security sandbox.

```json
{
  "version": 1,
  "source": {"main.py": "../real/main.py"},
  "inputs": {"rows.json": "../data/rows.json"},
  "timeout": 30,
  "commands": [["python3", "main.py"]],
  "steps": [
    {"id": "first", "files": {"main.py": "versions/first.py"}},
    {"id": "complete", "files": {"main.py": "../real/main.py"}}
  ]
}
```

A step may override `commands`, `timeout` and `cwd`. A command object
`{"argv": ["…"], "expected_exit": 1}` records an intentional failure. Unexpected failures or
timeouts stop the sequence and preserve diagnostics. Declare dependency/lock files in inputs;
include version commands when the toolchain matters. Full-file versions are supported; diffs
are deliberately omitted so patch state cannot leak across steps.

Results live under `data/steps/<run>/`: original source text/hashes/commit, step files, commands,
stdout/stderr (also raw bytes), exit statuses, durations and input hashes. Elapsed time is metadata,
not a benchmark methodology. Each invocation records a new run; `index.json` selects the current
one and hashes it. Rerun deliberately after changes; do not relabel old output as a fresh run.

Import the selected `data/steps/<run>/results.json` directly into the scene. Pass
`results.steps[n].files['main.py']` to `CodePanel` and its `commands` to `Terminal`.
`studio check VIDEO --only code-source` checks the final source against the actual source bytes,
checks the result hash/success and requires the scene import. This proves the recorded files and
declared scene binding; the independent frame reviewer also checks that the visible excerpt is
that program. Missing/changed source fails. A source snapshot records uncommitted content by hash.

## Remotion components (`@studio`)

All take explicit data and progress; derive progress from `useClip().t`, `ramp`, `pulse` and word
cues. Positions use stage units. Text defaults respect the type floor; inspect crops at delivery
size and choose a close-up instead of shrinking long code/tables to fit. These components are
Remotion-only; the evidence files can be used by either engine.

| Component | Data and controls |
|---|---|
| `CodePanel` | `source: {text, sha256}`, optional 1-based `range`, `current`, `plumbing`, `markers`, `tokens: [{line,text,progress}]`; displays unmodified source lines |
| `Terminal` | Captured `runs: [{argv,stdout,stderr,exit}]`, line-reveal `progress`, `maxLines` |
| `RowTable` | `columns`, actual `rows`, cell `highlight: [rowIndex,key]`, row-reveal `progress` |
| `JsonTree` | Actual JSON `value`, key-path `cursor`, row-reveal `progress` |
| `ColumnStrips` | `columns: [{name,bytes,groups?}]`, `h`, drawer `open`; widths follow byte proportions |
| `GeoMap` | `features: [{id,geometry}]`, `selected`, `halo`, `grid`, `h`; normalize WKT to GeoJSON in sims/ |
| `VarCard` | `label`, `value`, `type`, `focus` |
| `Thread` | `from`, `to`, `progress`, `opacity`; a relationship line, not moving data |

Most panels take `at`, `w`, `opacity`, `size`, and `name`. GeoMap supports Point, MultiPoint,
LineString, MultiLineString, Polygon and MultiPolygon coordinates in one already selected
coordinate system; it is a fit-to-stage diagram, not a GIS projection engine. Record units and
projection/simplification in Evidence. Do not use a moving road to mean a copied database row:
keep the map fixed, copy the row in the file view and link the two representations.
