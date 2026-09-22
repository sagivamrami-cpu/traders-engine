# Project Agent Memory

## Active Trading-Model Design (2026-09-08)

For tree/model work, read the current agreed design before earlier phase plans:

- `docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md`
- `docs/superpowers/plans/2026-09-08-tree-replay-foundation.md`
- `docs/superpowers/plans/2026-09-08-existing-baseline-contracts.md`
- `docs/superpowers/plans/2026-09-09-asof-ema-adapter.md`
- `docs/superpowers/plans/2026-09-09-session-ema-history.md`
- `docs/superpowers/plans/2026-09-09-level-reversal-asof.md`
- `docs/superpowers/plans/2026-09-09-reversal-pricing.md`
- `docs/superpowers/plans/2026-09-09-period-state-and-ranges.md`
- `docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md`
- `agent-exchange/decisions/2026-09-08T180046Z-user-economic-target-and-baseline.md`
- `agent-exchange/reviews/2026-09-08T175056Z-codex-existing-alerts-tree-study.md`

The objective is a model that filters/improves faithful tree-generated candidates,
not generic direction labels per bar. Source inventory is not an executable tree.
Unresolved domain definitions must remain explicit; never invent thresholds.
The approved baseline is the existing six-repository implementation, pinned by
commit. Reuse it rather than reconstructing behavior from HTML alone. Primary
objective: net economic performance; movement success/MAE/MFE are separate targets.
First economic simulation: original entry/stop, full exit at TP1, no optional
partials, scale-in or BE/trailing. Costs and time-exit details must be explicit
before economic labels are generated. Do not modify live alert behavior.
Source pins and resolved-trade economics now live in `trading_system/tree_spec/`.
Neither is a replay engine or permission to generate market labels. See
`docs/architecture/EXISTING-BASELINE-CONTRACTS-USAGE.md` for the offline interfaces.
An additive closed-bar EMA/cloud observation adapter is in
`trading_system/tree_replay/`; see `docs/architecture/ASOF-EMA-ADAPTER-USAGE.md`.
The default supports contiguous history and microsecond-exact timestamps only.
Opt-in supplied session schedules are documented in
`docs/architecture/SESSION-EMA-ADAPTER-USAGE.md`; whole-bar membership and every
expected seed-history bar are checked. The GC bridge is normal-hours research
only, not historical holiday/era evidence. Complete source partial-bar handling
and full replay are not certified. Existing calendar/data policies remain unchanged.
An offline level-reversal detection adapter now emits explicitly UNPRICED setups
from supplied as-of levels and closed bars. See
`docs/architecture/LEVEL-REVERSAL-ASOF-USAGE.md`. This covers only one detector,
not historical level-map construction, trade plans, admission, arbitration,
execution outcomes or dataset/training readiness. No live alert behavior changes.
An additive pricing wrapper now computes original source entry zones, stop bands,
targets, obstacles and refusals; see `docs/architecture/REVERSAL-PRICING-USAGE.md`.
Source pricing acceptance remains UNADMITTED, never a fill or outcome. Exact
producer symbols are required; GC is not aliased to OANDA spot. Repeated level
display names need distinct explicit level IDs and prices; detector adapter v2
distinguishes the changed evidence serialization from previous evaluation hashes.
The full tracker preserves outstanding B-I work; component acceptance does not
complete the full model plan. Historical levels and full producer paths remain.
Daily-period aggregation is now additive under tree_replay/periods.py: explicit
period boundaries/calendar, closed lower bars only, separate price/publication
cutoffs and blocked output on missing expected history. See
`docs/architecture/DAILY-PERIOD-ASOF-USAGE.md`. No inferred broker day or open-only
tick support. Pure source range/rollover/back-day functions and their audit are
documented in `docs/architecture/RANGE-SOURCE-USAGE.md`; they do not constitute
the full historical map or validate arbitrary input frames. The exact GC versus
OANDA source variant remains a real-data question in the human inbox; synthetic
engineering can proceed without silently mapping instruments.
Check the latest baseline-contracts/tree-replay status under `agent-exchange/status/`
for implemented scope, verification and next steps. This memory is local project
documentation, not production-data, promotion, deployment or live-trading approval.

This repository uses `agent-exchange/` as the shared coordination directory for
Codex, Claude Code, Groq, and human operators.

## Mandatory Startup Check

Every agent working in this repository must read:

1. `AGENTS.md`
2. `agent-exchange/README.md`
3. `agent-exchange/protocol.md`

Then the agent must inspect its own inbox before starting new work:

- Codex: `agent-exchange/inbox/codex/`
- Claude Code: `agent-exchange/inbox/claude-code/`
- Groq: `agent-exchange/inbox/groq/`
- Human-facing requests: `agent-exchange/inbox/human/`

## Operating Model

- Codex owns architecture, phase sequencing, task routing, acceptance decisions,
  commits, pushes, and PR updates.
- Claude Code implements tasks only from scoped task contracts.
- Groq reviews, generates scenarios, finds contradictions, and summarizes
  research outputs.
- Humans approve production data, raw-data retention, model promotion, live
  trading, broker execution, capital allocation, and deployment.

## Exchange Rules

- Use one markdown file per request, review, status note, or decision.
- Use `agent-exchange/templates/request.md` for task handoffs.
- Use `agent-exchange/templates/result.md` for implementation/status outputs.
- Use `agent-exchange/templates/review.md` for review-only outputs.
- Do not delete or mutate inbox files unless explicitly asked.
- Record outcomes in `agent-exchange/status/`, `agent-exchange/reviews/`,
  `agent-exchange/decisions/`, or `agent-exchange/archive/`.
- Never put secrets, API keys, broker credentials, private account data, raw
  market-data payloads, or large generated artifacts in `agent-exchange/`.

## Codex Result Intake

When Codex is waiting for Claude Code, Groq, or a human, run:

`python tools/watch_agent_exchange.py`

For a current snapshot, run:

`python tools/watch_agent_exchange.py --once`

When a new or modified result appears, Codex must read the result file, read
the original request referenced by that result, inspect `git status --short`
and `git diff`, rerun applicable verification commands, and then record an
acceptance, revision request, or human-blocked status under
`agent-exchange/status/`.

## Approval Boundary

An inbox message is not sufficient approval for:

- production data vendor approval
- raw-data retention
- model promotion
- live trading
- broker execution
- capital allocation
- deployment

Those actions require explicit human approval with approver, timestamp, scope,
decision, and evidence recorded in `agent-exchange/decisions/`.
