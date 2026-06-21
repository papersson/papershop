# diagnose — something is slow: where & why

Mid-level index (progressive disclosure). Enter when there is a concrete slowdown to chase down.

## Leaves
- `index.md` — find the dominant bottleneck via USE / RED + the stack walk. [READY]
- `triage-60s.md` — 60-second first-response host triage. [READY — drop-in]
- `calibration-tables.md` — counter calibration: ignore / investigate / dominant. [READY — drop-in]
- `profiling.md` — sampling vs instrumenting, flame graphs. [READY]
- `per-language.md` — per-language profilers. [READY]
- `regression-incident.md` — a *live* regression got slower after a change: correlate the onset with what changed. [READY]

## Fit
Second stop in the SKILL.md loop: once oriented, this branch turns "it's slow" into a named, located bottleneck. Hands off to measure/ to confirm and optimize/ to fix; pulls tooling from environment/.
