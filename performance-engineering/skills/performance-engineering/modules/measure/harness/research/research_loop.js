// Self-driving research loop for the performance-eval-harness project.
//
// This is a Workflow script (run by the orchestrate/Workflow harness, not by
// node). It embodies the meta loop: read the lab notebook, pick the highest-
// value open claim, design and run a REAL experiment, verify it with a separate
// agent, write findings back to the notebook, then repeat until an adversarial
// critic can find no high-value work left (or an iteration cap is hit).
//
// Run it:  Workflow({ scriptPath: "<repo>/research/research_loop.js",
//                     args: "perf-harness-research-loop" })
// Resume:  add resumeFromRunId: "<runId>" after editing.

export const meta = {
  name: 'research-loop',
  description: 'Self-driving research loop: read the lab notebook, pick the highest-value open claim, design and run a real experiment, verify it, write findings back, and repeat until an adversarial critic finds no high-value work left.',
  phases: [
    { title: 'ReadState' },
    { title: 'Iterate' },
    { title: 'Report' },
  ],
}

const REPO = '/Users/patrikpersson/Code/performance-eval-harness'
const MAX_ITERS = 3

const SPINE = `## PROJECT CONTEXT (shared — fold in, do not re-derive)

We are developing transferable knowledge: "how to build performance-evaluation
harnesses for any codebase." This is empirical methodology development (the
scientific method). Experiments exist to attack FALSIFIABLE CLAIMS, not to make
numbers. A refuted claim is a success — it updates the theory.

Project root: ${REPO}

The lab notebook is the source of truth — read and update it:
  research/THEORY.md  -- current best understanding (spine, regimes, framework).
  research/CLAIMS.md  -- the falsifiable claim ledger with statuses.
  research/LOG.md     -- append-only iteration history.

The harness has a SHARED SPINE (four stages, talking only via plain data):
  probe/adapter -> runner -> raw_samples -> aggregator (stats) -> reporter
Files:
  src/harness/core.py    -- in-process runner + Probe contract + correctness gate.
  src/harness/stats.py   -- aggregate(samples)->summary + bootstrap CI. Backbone.
  src/harness/report.py  -- plot_scaling(stats,x_key,...) + format_table; reads only stats.
  src/harness/cli_regime.py -- the CLI regime adapter (wraps hyperfine).
  experiments/<name>/{target.py, run.py}; artifacts in results/<name>/.

Raw-sample schema (load-bearing contract; one dict per measurement):
  { "probe": str, "params": dict, "rep": int, "batch": int, "seconds_per_op": float }
Summary schema from aggregate() (what report reads):
  { probe, params, n, min, median, mean, stdev, p90, p99, ci_low, ci_high }

CORE INVARIANT (claim C1): adding a new TARGET requires only a probe/adapter; you
do not modify the spine. Reuse stats.py and report.py unchanged for targets. A
DELIBERATE, general improvement to the spine (e.g. adding provenance fields used
by all regimes) is allowed — but it is INFRASTRUCTURE evolution that must be
documented in LOG.md/CLAIMS.md, never a hack bent to fit one target.

Regimes: LIBRARY/in-process (confirmed), CLI/subprocess via hyperfine (confirmed),
SERVICE/load (untested). Regime + wrap/build choice is governed by the
REGIME-AND-SOURCING (R&S) framework in THEORY.md.

Environment: macOS, uv 0.4.27, brew available (installing standard benchmark
tools is allowed — hyperfine is already installed). /usr/bin/time -l gives peak
RSS on macOS. Run scripts with: cd ${REPO} && uv run python <script>. Keep runs
modest (a couple of minutes). Generate inputs deterministically.

Candidate directions (not exhaustive; the planner chooses by value):
  - SERVICE/load regime (third regime; also exercises tail-latency CIs -> claim C2).
  - Provenance-aware spine evolution recommended by R&S (metric/unit/clock/
    includes_startup fields; aggregate() refusing to pool mismatched units).
  - A non-time metric (peak memory via /usr/bin/time -l, or allocations) -> tests
    the Q0 metric-type gate and whether the schema generalizes past seconds.
  - Stress the median+bootstrap default on a heavy-tailed distribution (C2).`

// ---------- Schemas ----------
const STATE_SCHEMA = {
  type: 'object',
  required: ['goal', 'open_items'],
  properties: {
    goal: { type: 'string' },
    open_items: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'statement', 'status', 'why_valuable', 'tractable_in_one_iteration'],
        properties: {
          id: { type: 'string' },
          statement: { type: 'string' },
          status: { type: 'string' },
          why_valuable: { type: 'string' },
          tractable_in_one_iteration: { type: 'boolean' },
        },
      },
    },
    notes: { type: 'string' },
  },
}

const PLAN_SCHEMA = {
  type: 'object',
  required: ['claim_id', 'hypothesis', 'regime', 'experiment_design', 'success_criteria', 'status'],
  properties: {
    claim_id: { type: 'string', description: 'the claim/item id this attacks' },
    hypothesis: { type: 'string', description: 'the falsifiable prediction under test' },
    regime: { type: 'string' },
    experiment_design: { type: 'string', description: 'concrete, runnable design: targets, params, what is measured, what artifacts' },
    tools_needed: { type: 'array', items: { type: 'string' } },
    expected_artifacts: { type: 'array', items: { type: 'string' }, description: 'paths the run will produce' },
    success_criteria: { type: 'string', description: 'what confirms vs refutes the claim' },
    preflight_notes: { type: 'string', description: 'tool availability checked; fallback if missing' },
    status: { type: 'string', enum: ['OK', 'BLOCKED'] },
  },
}

const SNAP_SCHEMA = {
  type: 'object',
  required: ['core', 'stats', 'report'],
  properties: { core: { type: 'string' }, stats: { type: 'string' }, report: { type: 'string' } },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['experiment_runs', 'artifacts_present', 'validity_gate_ok', 'spine_change_kind', 'claim_outcome', 'verdict', 'observed_hashes', 'notes', 'required_fixes'],
  properties: {
    experiment_runs: { type: 'boolean' },
    artifacts_present: { type: 'boolean' },
    validity_gate_ok: { type: 'boolean', description: 'correctness/validity gate genuinely applied where applicable' },
    spine_change_kind: { type: 'string', enum: ['none', 'infrastructure', 'per_target_hack'] },
    claim_outcome: { type: 'string', enum: ['confirmed', 'partial', 'refuted'] },
    verdict: { type: 'string', enum: ['sound', 'needs_revision'], description: 'sound = valid result (incl. documented refutation or documented infra change); needs_revision = fixable bug (no run / missing artifacts / no gate / per_target_hack to revert)' },
    observed_hashes: { type: 'object' },
    notes: { type: 'string' },
    required_fixes: { type: 'array', items: { type: 'string' } },
  },
}

const CRITIC_SCHEMA = {
  type: 'object',
  required: ['remaining_high_value_items', 'breakable', 'dry', 'rationale'],
  properties: {
    remaining_high_value_items: {
      type: 'array',
      items: { type: 'object', required: ['question', 'why'], properties: { question: { type: 'string' }, why: { type: 'string' } } },
    },
    breakable: { type: 'boolean', description: 'could you invent a realistic target the framework cannot place or that breaks the spine contracts?' },
    dry: { type: 'boolean', description: 'true ONLY if there is no high-value open work AND you cannot break the framework' },
    rationale: { type: 'string' },
  },
}

function verifyPrompt(plan, snap) {
  return `${SPINE}

## YOUR TASK — independently verify the iteration for ${plan.claim_id} (you did NOT build it)
Spine sha256 BEFORE this iteration:
  core=${snap ? snap.core : 'unknown'}
  stats=${snap ? snap.stats : 'unknown'}
  report=${snap ? snap.report : 'unknown'}

In ${REPO}:
1. Recompute sha256 of src/harness/core.py, stats.py, report.py (shasum -a 256); compare to the before-hashes; record observed_hashes.
2. Re-run the experiment fresh using its run command under experiments/. Confirm exit 0 and that the expected artifacts exist and are non-empty (a PNG must be a valid image). Expected: ${(plan.expected_artifacts || []).join(', ') || '(infer from the experiment)'}.
3. Confirm any validity/correctness gate is genuinely applied (executed), not merely declared.
Judge:
- spine_change_kind: 'none' if the three spine files are byte-unchanged; 'infrastructure' if a spine file changed as a DELIBERATE general improvement (used across regimes, documented), NOT specific to one target; 'per_target_hack' if the spine was bent to fit this single target (a C1 violation).
- claim_outcome for ${plan.claim_id}: confirmed | partial | refuted, judged against: ${plan.success_criteria}
- verdict: 'sound' if this is a valid result (INCLUDING a documented refutation or a documented infrastructure change). 'needs_revision' ONLY for fixable bugs: does not run, missing/empty artifacts, missing gate, or a per_target_hack that should be reverted.
Return the structured verdict.`
}

// ---------- Phase: read notebook state ----------
phase('ReadState')
const state0 = await agent(
  `${SPINE}\n\n## TASK\nRead research/THEORY.md, research/CLAIMS.md, research/LOG.md in ${REPO}. Return the current state: the goal, and every OPEN item worth an experiment (any claim not yet 'confirmed', any untested regime, any recommended-but-unbuilt spine improvement). For each, judge whether it is tractable in a single ~2-minute experiment on this machine. Be concrete.`,
  { schema: STATE_SCHEMA, label: 'read-state', phase: 'ReadState', effort: 'high' }
)
if (!state0 || !state0.open_items || state0.open_items.length === 0) {
  return { status: 'BLOCKED', decision_needed: 'No open items to drive the loop', why_cannot_proceed: 'state agent returned no open items', work_already_done: { state0 } }
}

// ---------- Phase: the self-driving loop ----------
phase('Iterate')
let state = state0
const iterations = []
const attempted = []
let stoppedReason = 'cap'

for (let i = 0; i < MAX_ITERS; i++) {
  const n = i + 1
  // 1. Plan: value function picks the single highest-value open item.
  const plan = await agent(
    `${SPINE}\n\n## CURRENT NOTEBOOK STATE\n${JSON.stringify(state)}\n\n## ALREADY ATTEMPTED THIS RUN (do not repeat these claim ids)\n${JSON.stringify(attempted)}\n\n## TASK\nValue function: choose the SINGLE highest-value open item — the one whose resolution most reduces uncertainty about the goal AND is tractable in one ~2-minute experiment here. Design a concrete, runnable experiment that attacks it as a falsifiable claim. Preflight: name the tools needed and confirm they exist (or can be 'brew install'ed); if nothing tractable remains, return status=BLOCKED. Otherwise status=OK.`,
    { schema: PLAN_SCHEMA, label: `plan:i${n}`, phase: 'Iterate', effort: 'high' }
  )
  if (!plan || plan.status === 'BLOCKED' || !plan.experiment_design) {
    stoppedReason = 'no-tractable-plan'
    if (plan) iterations.push({ plan })
    break
  }
  attempted.push(plan.claim_id)
  log(`Iteration ${n}: attacking ${plan.claim_id} — ${plan.hypothesis}`)

  // 2. Snapshot the spine so the verifier can judge any change independently.
  const snap = await agent(
    `Compute the sha256 of these three files in ${REPO} using 'shasum -a 256' and return them: src/harness/core.py (as core), src/harness/stats.py (as stats), src/harness/report.py (as report).`,
    { schema: SNAP_SCHEMA, label: `snapshot:i${n}`, phase: 'Iterate', effort: 'low' }
  )

  // 3. Implement + run the experiment for real.
  const impl = await agent(
    `${SPINE}\n\n## EXPERIMENT PLAN (build and run this in ${REPO})\n${JSON.stringify(plan)}\n\n## TASK\nWrite the real code and run it. Preflight tools first (brew install standard benchmark tools if needed). Create experiments/<name>/ (target.py + run.py) and write artifacts to results/<name>/. Reuse the spine (stats.aggregate, report.plot_scaling/format_table) unchanged for the target. If the plan calls for a deliberate, general spine improvement (e.g. provenance fields), implement it cleanly so ALL regimes benefit and document it — do not bend the spine to one target. Include a validity/correctness gate where comparing implementations. Run via 'uv run python ...' until it produces the artifacts and any plot renders. Keep runs modest. Report: files created/changed, whether and why the spine changed, the gate result, and the headline numbers.`,
    { label: `implement:i${n}`, phase: 'Iterate', effort: 'high' }
  )

  // 4. Verify (separate agent) with a bounded fix loop.
  let v = await agent(verifyPrompt(plan, snap), { schema: VERDICT_SCHEMA, label: `verify:i${n}:r1`, phase: 'Iterate', effort: 'high' })
  let r = 1
  while (v && v.verdict === 'needs_revision' && r < 3) {
    log(`Iteration ${n} verify r${r}: needs_revision — ${v.notes}`)
    await agent(
      `${SPINE}\n\n## Fix the experiment for ${plan.claim_id} in ${REPO}.\nVerifier notes: ${v.notes}\nRequired fixes:\n${(v.required_fixes || []).map((f) => '- ' + f).join('\n')}\nConstraints: reuse the spine unchanged for the target (a per-target spine hack is the bug to remove); any artifacts must be produced by the run command; the validity gate must really execute. Report what you changed.`,
      { label: `fix:i${n}:r${r}`, phase: 'Iterate', effort: 'high' }
    )
    r++
    v = await agent(verifyPrompt(plan, snap), { schema: VERDICT_SCHEMA, label: `verify:i${n}:r${r}`, phase: 'Iterate', effort: 'high' })
  }
  if (!v) { iterations.push({ plan, snapshot: snap, implementation: impl, verdict: null }); stoppedReason = 'verifier-died'; break }

  // 5. Record findings back into the notebook.
  const rec = await agent(
    `${SPINE}\n\n## TASK — update the lab notebook in ${REPO}/research to reflect this iteration honestly.\nClaim ${plan.claim_id} outcome = ${v.claim_outcome}. Spine change = ${v.spine_change_kind}.\n1. CLAIMS.md: update status/evidence for ${plan.claim_id} (and any other claim this moved). A refutation is a real result — record it.\n2. THEORY.md: fold in what was learned (regime status, framework refinement, spine evolution if any).\n3. LOG.md: append a new dated iteration entry (question, method, result, headline numbers, claims moved).\nKeep it tight and factual.\nPlan: ${JSON.stringify(plan)}\nVerifier verdict: ${JSON.stringify(v)}\nImplementer summary: ${typeof impl === 'string' ? impl.slice(0, 1500) : ''}`,
    { label: `record:i${n}`, phase: 'Iterate', effort: 'high' }
  )

  // 6. Re-read state, then run the adversarial stop-condition critic.
  const updated = await agent(
    `${SPINE}\n\n## TASK\nRe-read research/CLAIMS.md and research/THEORY.md in ${REPO} and return the current state with all remaining OPEN items (as in read-state).`,
    { schema: STATE_SCHEMA, label: `reread:i${n}`, phase: 'Iterate', effort: 'medium' }
  )
  const critic = await agent(
    `${SPINE}\n\n## CURRENT STATE\n${JSON.stringify(updated || state)}\n\n## ALREADY ATTEMPTED THIS RUN\n${JSON.stringify(attempted)}\n\n## TASK — adversarial stop-condition critic (the "target generator")\nTry hard to (a) invent a REALISTIC target the R&S decision framework cannot place, or whose measurement would break the spine contracts; and (b) list remaining high-value open claims worth a future iteration. Set dry=true ONLY if there is genuinely no high-value open work left AND you cannot break the framework. Do not declare dry merely to stop; an honest "not dry" with concrete next work is the expected answer while open claims remain.`,
    { schema: CRITIC_SCHEMA, label: `critic:i${n}`, phase: 'Iterate', effort: 'high' }
  )

  // 7. Persist the critic's forward agenda so the NEXT run builds on it without
  //    a human hand-copying it (this is what makes the loop self-chaining).
  if (critic && Array.isArray(critic.remaining_high_value_items) && critic.remaining_high_value_items.length) {
    await agent(
      `${SPINE}\n\n## TASK — persist the critic's forward agenda into ${REPO}/research/CLAIMS.md\nRead CLAIMS.md. Under the "## Open agenda" section (create it at the end of the file if absent), ADD any of the candidate items below that are not already represented there. Dedupe by topic against existing entries; do NOT duplicate, remove, or reorder existing items, and do not touch the claim table. Keep each new item to 2-3 lines: a short bold title, the test, and a one-line why. Preserve any DONE markers already present.\n\nCANDIDATE ITEMS (from the iteration ${n} critic):\n${JSON.stringify(critic.remaining_high_value_items)}`,
      { label: `persist-agenda:i${n}`, phase: 'Iterate', effort: 'low' }
    )
  }

  iterations.push({ plan, snapshot: snap, implementation: impl, verdict: v, record: rec, critic })
  if (updated && updated.open_items) state = updated
  if (critic && critic.dry === true) { stoppedReason = 'critic-dry'; break }
}

log(`Loop finished after ${iterations.length} iteration(s); reason: ${stoppedReason}.`)

// ---------- Phase: meta-report over the whole run ----------
phase('Report')
const reportBase = (typeof args === 'string' && args) ? args : 'perf-harness-research-loop'
const reportPath = `/tmp/orchestrate-reports/${reportBase}.html`
const manifest = {
  goal: state0.goal,
  iterations_run: iterations.length,
  stopped_reason: stoppedReason,
  iterations: iterations.map((it) => ({
    claim: it.plan ? it.plan.claim_id : null,
    hypothesis: it.plan ? it.plan.hypothesis : null,
    regime: it.plan ? it.plan.regime : null,
    design: it.plan ? it.plan.experiment_design : null,
    verdict: it.verdict || null,
    critic: it.critic || null,
  })),
}
const reportResult = await agent(
  `Write a single SELF-CONTAINED HTML file to exactly ${reportPath} (inline CSS + inline SVG only; ZERO external requests). Create /tmp/orchestrate-reports/ if needed.\n\nThis reports a SELF-DRIVING RESEARCH LOOP that ran autonomously over ${iterations.length} iteration(s) of developing a performance-evaluation-harness methodology. It stopped because: ${stoppedReason}.\n\nLead with and dominate on the SCIENCE, not the machinery:\n1. The goal, and how the loop works in one paragraph: it reads the lab notebook, a value function picks the highest-value open falsifiable claim, it runs a real experiment, a separate agent verifies it, findings are written back, and an adversarial critic decides whether to continue.\n2. For EACH iteration, a clear section: which claim it attacked, the hypothesis, what experiment ran (real targets + numbers), the separate verifier's verdict and the claim outcome (confirmed/partial/refuted — show refutations honestly), and whether the spine stayed intact or evolved as documented infrastructure.\n3. A CLAIM-LEDGER DELTA across the whole run (before -> after), and the loop's convergence behavior (did the critic go dry, or did it hit the cap with named remaining work?).\n4. What the loop leaves open — the critic's remaining high-value items — as the agenda for the next run.\nDemote orchestration mechanics to one compact collapsible 'How this was produced' section.\n\nInclude paste-ready commands: re-run the loop is Workflow scriptPath ${REPO}/research/research_loop.js; re-run any experiment is 'cd ${REPO} && uv run python experiments/<name>/run.py'.\nStyle: clean, Anthropic-minimal, outline-only SVG (a small loop/cycle diagram helps). Write prose like a thoughtful human engineer; vary sentences; do not corrupt numbers/commands/verdicts. Diagrams visible and unclipped at ~390px and ~1280px.\nAfter writing, return ONLY the absolute path.\n\nMANIFEST:\n${JSON.stringify(manifest)}`,
  { label: 'report:write', phase: 'Report', effort: 'high' }
)
const reportVerify = await agent(
  `Verify the HTML report at ${reportPath} using agent-browser (run \`agent-browser --help\` first). Confirm: (a) renders without errors; (b) self-contained — network/HAR shows effectively one request; (c) all SVG diagrams visible and unclipped at ~390px and ~1280px; (d) console clean. Fix in place and re-verify if any check fails. Return a short summary: { renders, self_contained, diagrams_ok, console_clean, fixes_made }.`,
  { label: 'report:verify', phase: 'Report', effort: 'medium' }
)

return {
  status: 'OK',
  reportPath,
  iterationsRun: iterations.length,
  stoppedReason,
  attempted,
  outcomes: iterations.map((it) => ({ claim: it.plan ? it.plan.claim_id : null, outcome: it.verdict ? it.verdict.claim_outcome : null, verdict: it.verdict ? it.verdict.verdict : null, spine: it.verdict ? it.verdict.spine_change_kind : null })),
  remaining: iterations.length ? (iterations[iterations.length - 1].critic || null) : null,
  reportVerify,
}
