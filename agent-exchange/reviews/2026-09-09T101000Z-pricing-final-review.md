# Agent Exchange Review

Reviewer:
Codex independent final combined reviewer; no nested agents.

Target request:
`agent-exchange/inbox/codex/2026-09-09T101000Z-pricing-final-review.md`

Created at:
2026-09-09T10:09:16Z (review workstation UTC)

Status:
REVIEW_READY_FOR_CODEX

Verdict:
**Spec: APPROVED. Quality: APPROVED with one deferred Minor.** No Critical or
Important findings. Ready for controller acceptance of the bounded pricing slice;
this is not full B-I acceptance, replay/training readiness or production approval.

Reviewed the reversal-pricing plan, final-review.diff, worker/parent reports,
both task reviews and progress rulings against the assembled implementation and
its bar, session, detector and snapshot dependencies. Applied the specified
`requesting-code-review/code-reviewer.md` criteria directly. Base/head remain
`c1b6071633c55376c64f0a98ece843706f420f49`; changes are uncommitted.

Findings:

### Strengths and combined boundary assessment

- **Consistent input window and provenance:** `trading_system/tree_replay/pricing.py:76`
  materializes input once and recomputes detection; `:99` reselects the same
  validated window and `:125` supplies its numeric frame and the entire level
  tuple to the source builder. Closed/available filtering in `bars.py:147`,
  complete expected-history checks in `session_bars.py:96`, and level guards in
  `reversal.py:123` precede pricing. Publication at `pricing.py:110` includes all
  selected bars, levels and supplied calendar. Snapshot construction enforces
  observation/publication no later than decision. Caller-attested level metadata
  remains distinct from proof of historical construction.
- **Numerical source closure:** `_vendor/reversal_pricing.py:10` reconstructs the
  original builder using the existing Reversal and normalization plus the pure
  pricing, quarter and ATR modules. `_vendor/atr.py:6` preserves unseeded EWM;
  `_vendor/pricing.py:68` preserves zone-edge bands and the source's midpoint
  anchoring ceiling; `:333` preserves obstacle/refusal and measured-rung behavior.
  `pricing.py:24` rejects nonfinite/nonpositive prices, zone endpoints, risk and
  ATR, and nonfinite RR. Valid refused geometry and zero RR remain representable;
  missing targets become NOT_APPLICABLE. No replacement thresholds or numerical
  repairs were introduced.
- **Audited projection and imports:** `tools/check_pricing_source_parity.py:98`
  preserves Plan class metadata and non-method statements plus the four original
  properties. Fixed blob/import/symbol coverage and ordered AST comparison at
  `:129` reject reduced manifests or executable additions; `:145` also requires
  the inherited detector/PVSRA audit. This supports the combined dependency
  boundary without executing the retained source checkout.
- **Event versus evaluation identity:** `pricing.py:82` binds pricing version and
  source commit to the detector evaluation, which already includes input,
  policy, calendar and pandas/NumPy identities (`reversal.py:117`). Candidate
  IDs, source event IDs and detection snapshots survive pricing. The only direct
  detector edit is the v2 version bump. `levels.py:57` rejects duplicate explicit
  IDs and name/price pairs while accepting separately identified repeated names.
  IDs affect evidence hashing, not the original episode or tie-breaking rules.
  The source-driven Q-QUARTER amendment is justified and documented; old and new
  evaluation hashes are explicitly incompatible.
- **Pricing is separate from admission:** `pricing.py:93` requires exact producer
  symbols for detected setups; GC cannot inherit OANDA pricing. Missing input,
  no setup, unsupported pricing and source refusal remain distinct states.
  `pricing.py:129` returns PRICE_ACCEPTED_UNADMITTED or PRICE_REFUSED while
  preserving candidate tradeable=false, trade_plan=null and both readiness
  flags=false. Import/call-site inspection found no new connection to live paths.
- **Documentation:** REVERSAL-PRICING-USAGE.md, the revised detector usage guide,
  AGENTS/README, master-plan pricing progress and the full tracker agree with
  these interfaces and limits. Historical levels, full producer gates,
  arbitration, fills/outcomes and dataset/model work remain explicitly open.

### Critical

None found.

### Important

None found.

### Minor — deferred portability, retained

`tests/tree_replay/test_pricing_source.py:14` hard-codes a user-specific temporary
chart-desk checkout. The positive audit at `:181` cannot pass elsewhere without
recreating or changing that path; removal of the temporary checkout also breaks
reproducibility. This does not invalidate the retained-checkout evidence or block
this local component acceptance. Before CI or another checkout reuses the suite,
make the source root configurable, document the pinned-source prerequisite and
require it in the parity job. Do not silently skip the source audit. This review
retains the existing Minor classification and does not expand it into a pricing
correctness blocker.

Open questions:
None blocking this pricing slice. Historical level lineage, economic fill/cost/
time-exit contracts and remaining B-I requirements are still separate gates.

Recommended next action:
Controller records bounded pricing acceptance and the portability follow-up,
then continues the approved historical level-map/producer work. Component approval
does not establish full replay, a training dataset, profitability, or authority
for data acquisition, retention, orders, fitting, promotion or deployment.

Verification reviewed:

- **Independent read-only inspection: PASS.** `git rev-parse HEAD`,
  `git status --short`, `git diff --stat`, `git diff -- AGENTS.md README.md` and
  `git diff --cached --name-only`: unchanged HEAD, existing dirty work preserved,
  no staged changes. An inline `python -B -` text-only comparison recomputed
  canonical-LF Git blob hashes for all 18 files in final-review.diff: all match
  the packaged new-side hashes. This checks package currency, not source parity.
  Read the changed implementation and inherited dependencies; searched pricing
  references in trading_system/tools/engine/run_daily.py for live integration.
- **Worker evidence, not rerun:**
  `python -m pytest tests/tree_replay/test_pricing_source.py -q`: 74 passed in
  2.61s after reported RED. Source audit command
  `python tools/check_pricing_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk`:
  exit 0, subset verified, empty blockers, replay/training readiness false.
- **Parent evidence, not rerun:** 197 scoped tests passed in 3.66s; 1027
  tree-replay/tree-spec/session integration tests passed in 60.82s. Pricing,
  reversal and EMA source CLIs passed with readiness false, as supplied in the
  request/progress reports. Task 2's independent review also records focused
  blocker-propagation checks for delayed interior bars and future/stale levels.
- **Additional parent evidence supplied during this review:**
  `python -m pytest -q --ignore-glob='*validator*' --tb=short`: 1399 passed in
  177.77s, exit 0. Parent reports only documentation additions since packaging,
  with no pricing-code changes. Excluded legacy validators are not certified.
- No suite, source CLI or behavioral probe was repeated: static inspection left
  no named unresolved concrete risk needing another probe. No retained-source
  execution, nested agents, index/code changes, commits or external actions.
  Only this assigned review result was written, using apply_patch.
