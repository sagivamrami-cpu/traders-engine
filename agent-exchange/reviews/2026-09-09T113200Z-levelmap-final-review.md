# Agent Exchange Review

Reviewer:
Codex independent final combined reviewer; no nested agents.

Target request:
`agent-exchange/inbox/codex/2026-09-09T113200Z-levelmap-final-review.md`

Created at:
2026-09-09T11:33:46Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:

- Spec compliance: PASS for the historical-levelmap core implementation and its cross-task integration.
- Quality: APPROVED. No Critical, Important or Minor defect identified in the reviewed package.
- Ready for controller component acceptance: YES, using the supplied completed verification and this review. This is not full-model acceptance, a merge instruction, or production approval.

Findings:

Strengths and named integration risks reviewed:

1. **Source graph and dependency fidelity.** `trading_system/tree_replay/_vendor/levelmap_build.py:126` retains the source family order, asymmetric gates, warmups and fetch exception boundaries with explicit source/clock injection. `trading_system/tree_replay/_vendor/map_tr.py:1` composes existing calculations. `tools/check_levelmap_source_parity.py:208` invokes every inherited audit and independently seals their manifests; `:249` adds fixed, ordered EMA projections. The mutation tests distinguish coordinated repinning and ordering drift from harmless initial documentation. This review relies on the prior source comparison and parent audit execution for pinned-source verification; it does not claim a fresh execution of those audits.

2. **Frames to source calculation: future prices, period ownership and labels.** `trading_system/tree_replay/frames.py:109` requires the actual current daily period, checks active-session ownership, partitions eligible base bars and propagates period blockers. `:168` rebuilds intraday buckets from complete published base prefixes with an explicit origin; `:219` enforces calendar availability/coverage and final freshness. Source index labels remain separate from observation/publication timestamps. `trading_system/tree_replay/levelmap.py:90` consumes only AVAILABLE reconstructed rows, and `:114` constructs a fresh source-shaped DataFrame. The source receives forming higher-frame prefixes, not final future OHLC. Missing expected history is not compressed into a shorter seed. Task2's two prior coverage findings are resolved by the scoped fix and rereview; no parked finding or domain ruling is carried forward.

3. **Correction eligibility versus consumer gates.** `trading_system/tree_replay/levelmap.py:103` assesses correction evidence at the same T with zero lookback, while `:135` recomputes and traces each actual source lookback. Available proxy/replay/unverified evidence is distinct from missing, future, delayed or stale evidence. The graph retains the daily 20-day and PSY seven-day decisions without a blanket broker-shape veto. No correction offset is reapplied and no instrument/feed identity is relabeled. Missing daily input blocks; optional unavailable inputs retain the original omissions. Unexpected adapter errors remain fatal even when an optional source catch absorbs their exception (`:179`).

4. **Lazy fetches, dependency hashes and repeated names.** `trading_system/tree_replay/levelmap.py:77` records actual requests, selected policies and available dependency evidence. Unused fallback values do not enter the result hash. `:193` derives level IDs from name/kind/price, preserving distinct Q-QUARTER prices without enumeration shifts. `:196` binds the snapshot to selected dependency traces and validates it against the existing immutable snapshot contract. Tests at `tests/tree_replay/test_levelmap.py:145` and `:243` cover future/fallback invariance, request ordering, stable IDs and mutation isolation. Invalid source prices block the whole map instead of silently removing levels.

5. **Map clock to reversal/pricing.** Snapshot observed_at and available_at equal T (`trading_system/tree_replay/levelmap.py:196`); actual price timestamps remain in the fetch trace. The clock-only splice transition regression at `tests/tree_replay/test_levelmap.py:233` verifies why these timestamps differ. The unchanged detector rejects levels observed after its newest selected confirmation (`trading_system/tree_replay/reversal.py:114`). The integration at `tests/tree_replay/test_levelmap.py:298` supplies the calculated map at the same confirmation time, replaces the old fixture's manual levels, and invokes the real detector/pricer. It checks detected candidates, entry/stop geometry, false tradeability/readiness and a separate NO_CANDIDATE path. A newly evaluated map at a later T must not be backdated to bypass the consumer guard; asynchronous or delayed-confirmation producer behavior is not certified here.

6. **Documentation and full-plan scope.** The three new usage documents and the controller AGENTS/README/master delta accurately distinguish source audit, causal frames, map construction and producer admission. Closed-base precision, caller-attested calendars/labels/provenance, original silent omissions, exact symbols and false readiness remain explicit. The tracker still leaves public-binding acceptance pending and preserves the broader B-I obligations; the package contains no tracker-content delta. Updating its final acceptance state belongs to controller intake after this review. No documentation in this delta claims a completed simulator, dataset, trained model, profitability result or human approval.

Severity findings:

- Critical: none.
- Important: none.
- Minor: none.

Open questions:

No unresolved implementation question blocks this component review. The following are unverified obligations or retained scope boundaries, not parked defects:

- Controller must record durable combined acceptance and reconcile the Task3 checklist, ledger and tracker with the completed verification. This review does not perform that acceptance write.
- Runtime suites and source audit CLIs were not rerun by this reviewer, as explicitly instructed. Their PASS results are parent-supplied evidence, corroborated by the task records and latest ledger; historical RED chronology and complete execution logs were not independently recertified.
- Legacy validator tests were explicitly excluded from the broad run and remain uncertified.
- Runtime map construction does not run the source audit itself. Future integration/CI must retain mandatory source verification against available pinned source text; successful runtime construction alone is not parity proof.
- Real historical vendor/calendar/feed-era provenance, label/grid correctness and cross-frame price-basis consistency remain supplied attestations. No real-data coverage, exact GC/source variant, holidays or live parity were certified.
- Open-only ticks and partly observed base bars remain unsupported. Source lookback arguments are request identities, not automatic proof of full historical window coverage. Built maps may omit source families and remain UNADMITTED.
- Full producer find/admission/arbitration, other branches and memory, order lifecycle, execution simulation, explicit fill/cost/expiry/time-exit policies, separate economic/movement outcomes, datasets, training, evaluation and shadow deployment remain outside this component. Production data, retention, promotion, deployment, broker execution, live trading and capital allocation require their existing human decisions.

Recommended next action:

Controller may accept the historical-levelmap core and finish its acceptance bookkeeping. No implementation revision is requested. Preserve the remaining producer/model work and existing human gates; do not promote this component verdict to full-model or production acceptance.

Verification reviewed:

- Read AGENTS.md, exchange README/protocol, Codex inbox listing, original final request, complete component plan, current master design, historical source contract, approved baseline/economic decision, review template, scratch progress and all three task reports. Read prior source/frame/adapter reviews, the Task2 fix rereview, prerequisite acceptance records and Task3 intake record.
- Applied the complete `superpowers/requesting-code-review/SKILL.md` and `code-reviewer.md` method directly: plan alignment, quality, architecture, testing, strengths, severity and explicit assessment. The user's no-nested-agents/review-only scope governs execution.
- Read all 13 new-file sections and the controller memory delta in `.superpowers/sdd/2026-09-09-historical-levelmap-core/final-review.diff`; bounded follow-up reads recovered truncated portions. `git hash-object` confirmed that all 13 current file blobs match their package index prefixes. HEAD remains `c1b6071633c55376c64f0a98ece843706f420f49`. Inspected dirty status and tracked diff summary; ordinary tracked diff is not substituted for these untracked-file changes.
- Unchanged code inspection was confined to named integration risks: correction temporal assessment, period/selector completeness and publication, immutable level identity, confirmation-time eligibility and pricing consumption. No unrelated earlier branch work was reopened.
- Parent independent PASS: `python -m pytest tests/tree_replay/test_frames.py tests/tree_replay/test_levelmap_source.py -q --tb=short` — 215 passed in 96.46s, exit 0.
- Parent independent PASS: `python -m pytest tests/tree_replay/test_levelmap.py -q --tb=short` — 40 passed in 5.59s, exit 0.
- Parent independent PASS: `python -m pytest tests/tree_replay tests/tree_spec tests/data_foundation/test_sessions.py -q --tb=short` — 1597 passed in 182.72s, exit 0; completion supplied during review.
- Parent independent PASS: `python -m pytest -q --ignore-glob='*validator*' --tb=short` — 1969 passed in 247.11s, exit 0; completion supplied during review. Legacy validators explicitly excluded. These test counts overlap and are not additive.
- Parent-reported source CLIs PASS, final exit 0, blockers empty and readiness false: `python tools/check_range_source_parity.py`, `python tools/check_correction_source_parity.py`, `python tools/check_levelmap_source_parity.py`; and `python tools/check_ema_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk`, `python tools/check_reversal_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk`, `python tools/check_pricing_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk`. The ledger distinguishes corrected missing-argument invocations from these final successful calls.
- No routine tests or focused runtime experiments were executed; static evidence resolved the integration doubts. No code edits, commits, worktrees, cleanup, source/feed execution, data access or external messages. This requested review file is the sole reviewer write.
