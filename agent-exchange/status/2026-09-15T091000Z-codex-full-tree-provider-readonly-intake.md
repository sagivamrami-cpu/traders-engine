# Agent Exchange Result

Target:
Codex / project memory

Sender:
Codex architecture controller

Created at:
2026-09-15T09:10:00Z

Request:
Persistent project objective: continue the approved causal tree-replay plan.

Status:
REVIEW_REQUESTED

Summary:

Completed additional read-only source intake for the future full-tree causal
provider. The current `CausalReplay` only accepts `level_reversal:5m`; it
cannot be described as a full-tree historical runner. The actual `TreeReader`
and `TreeRevalidation` components use raw ports beyond the current causal
admission context and some dependent readers deliberately issue repeated reads.

The intake confirms that a future provider must preserve source calls rather
than collapsing all market state into one computed snapshot. Examples: WM,
liquidity pools and liquidity run each fetch frames independently; checklist
and Brinks reads use their own timeframes/lookbacks; options consumes report
list/bytes, TradingView CSV and its own clock. Their caught failures can mean
unknown/absent context and must not be converted into a fabricated negative
fact.

Changed files:

- `agent-exchange/inbox/groq/2026-09-15T090000Z-codex-full-tree-causal-provider-intake-review.md`
  — read-only independent review request; no runtime changes.
- This status note.

Verification results:

- PASS (inspection): `CausalReplay` has `_SUPPORTED_VARIANT = "level_reversal:5m"`.
- PASS (inspection): `TreeReader` consumes raw corrected frames, `now_utc`,
  calendar text, options report listing/bytes and TradingView CSV through its
  actual readers.
- PASS (inspection): dependent raw reads were located in
  `_vendor/{wm,liquidity,checklists,brinks,optionswall}.py`; repeated calls are
  source behavior, not duplicate test scaffolding.
- PASS (scope check): `check_tree_walk_source_parity.py` and
  `check_causal_replay_source_parity.py` are static source-faithfulness audits.
  Their ready flags remain false and they do not exercise a full-tree
  point-in-time provider, its availability schedule, or its checkpoint resume.
- PASS: `git diff --check` for the review request produced no whitespace errors.

Decisions needed:

- Human approval of the full-tree causal-provider design before code is written.
- Independent review verdict from the requested Groq intake.

Blockers:

No source access blocker. Implementation is intentionally paused at the design
approval boundary; no economic, dataset, model, broker, or live authority is
requested or implied.

Recommended next action:

Read the independent intake review, resolve any source-contract discrepancy,
then present the full-tree causal-provider design for human approval. Do not
extend `CausalAdmissionContext` by implication and do not make a complete
`Walk` an admission, fill, outcome, or label.

The future proof set must therefore include runtime, ordered-call and
checkpoint/resume tests in addition to the existing static parity audits.

Notes:

This result does not accept the pending Outer Admission component and does not
replace either of its requested independent reviews.
