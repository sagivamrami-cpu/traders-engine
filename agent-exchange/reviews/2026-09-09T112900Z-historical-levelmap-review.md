# Agent Exchange Review

Reviewer:
Codex independent Task 3 reviewer

Target request:
`agent-exchange/inbox/codex/2026-09-09T112900Z-historical-levelmap-review.md`

Created at:
2026-09-09T11:30:03Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
Spec compliance: PASS for the scoped three-file implementation. Controller-owned acceptance obligations remain unverified below.
Task quality: APPROVED. No Critical, Important or Minor defect identified in this review.

Findings:

- Interface and identity requirements are implemented in `trading_system/tree_replay/levelmap.py:28` and `:146`: frozen keyword-only requests, original request keys, exact instrument/timeframe/correction association, native integer policies, tuple validation and unique keys/frame IDs. No symbol mapping or caller-computed readiness is accepted.
- The invocation-local source at `trading_system/tree_replay/levelmap.py:67` reconstructs fetched frames, assesses corrections at the same T with zero lookback, and distinguishes unavailable evidence from ASSESSED proxy/unverified evidence. Actual consumer shape calls at `:134` are recomputed and traced independently. Lazy selection preserves the unused fallback hash boundary.
- The original graph is invoked at `trading_system/tree_replay/levelmap.py:174`. Required daily failure yields no map; unexpected fetch errors remain fatal even when an optional source catch absorbs them (`:179`). Source order and missing strings pass through directly. Emitted nonfinite/nonpositive prices block the entire map (`:185`), rather than being filtered.
- Stable name/kind/price IDs, snapshot compatibility validation, T-valued observation/publication timestamps, separate actual frame timestamps, canonical hashing and false readiness/tradeability are present at `trading_system/tree_replay/levelmap.py:98`, `:166`, `:193`, `:196` and `:212`. Documentation describes these boundaries and remaining scope at `docs/architecture/HISTORICAL-LEVELMAP-USAGE.md:49`, `:81`, `:122` and `:155`.
- Test strengths: literal 41-level family/price/order expectations and forming-state evidence (`tests/tree_replay/test_levelmap.py:113`); future/fallback invariance (`:145`); unavailable daily/optional dependencies (`:162`, `:189`, `:323`); asymmetric gates and actual splice lookbacks (`:202`, `:213`, `:223`); clock-only transition (`:233`); stable repeated-name IDs and mutation isolation (`:243`); invalid inputs (`:262`, `:268`); whole-map invalid-price and real calculation-error handling (`:288`, `:371`, `:382`).
- The integration test at `tests/tree_replay/test_levelmap.py:298` replaces the reference fixture's manual snapshot with the actual built map before invoking the real detector/pricer. It asserts detected candidates, source entry/stop, nontradeability/readiness, and a separate NO_CANDIDATE path. No calculation dependencies are mocked.

Open questions:

- Cannot verify from this Task 3 diff: source parity and prerequisite Task 1/2 acceptance records. The controller reports all six source audits PASS; this review did not independently inspect their execution logs or reopen dependency acceptance.
- Integration and broad results, final combined review, and controller-owned AGENTS/README/master/tracker acceptance edits remain controller obligations. Their absence from the worker's three-file diff is consistent with the brief's explicit ownership split.
- Historical vendor/calendar certification, exact GC/source variant, full producer admission/arbitration, simulation, datasets, models and human approvals remain outside this component. This verdict provides none of those approvals.

Recommended next action:
Accept the scoped implementation gate; complete and record the controller-owned verification and combined acceptance before marking the full task complete. No implementation revision is requested by this review.

Verification reviewed:

- Read the brief first, then report and complete new-file review package, plus AGENTS/exchange startup, Codex inbox listing, original review request, implementation request and review template. Applied `superpowers/subagent-driven-development/task-reviewer-prompt.md` spec-first/quality-second method. The initial tool output truncated the package; bounded reads recovered every hunk. Changed files were reviewed through the package, not separately reread.
- Base and HEAD: `c1b6071633c55376c64f0a98ece843706f420f49`. `git rev-parse HEAD`, `git status --short`, `git diff --stat` and scoped `git diff -- trading_system/tree_replay/levelmap.py tests/tree_replay/test_levelmap.py docs/architecture/HISTORICAL-LEVELMAP-USAGE.md` completed successfully. The scoped files are untracked, so the supplied full new-file package is the substantive diff; ordinary tracked diff output is empty for them. Existing unrelated dirty state was preserved.
- Named dependency risk: adapter exception handling or shape calls could change lazy source behavior. Checked `_vendor/levelmap_build.py:126`, `:206`, `:223`, plus its session/EMA fetch boundaries at `:40` and `:107`; the adapter preserves those boundaries and source lookbacks.
- Named dependency risk: frame reconstruction could expose final higher-timeframe data or misstate publication. Checked `frames.py:109`, `:168`, `:219` and its constructor policy/identity validation. The adapter uses its AVAILABLE rows and retains actual dependency timestamps; it does not promote a caller DataFrame or frame readiness claim.
- Named dependency risk: a false correction shape flag could be confused with temporal unavailability. Checked `corrections.py:53`; ASSESSED includes false shape/unverified inputs, while unavailable payloads are omitted. The adapter preserves that distinction.
- Named dependency risk: repeated names or timestamps could violate the downstream snapshot contract. Checked `levels.py:45` and the exact timestamp/identity helpers at `bars.py:23` and `:35`; generated snapshots satisfy those contracts. Checked `tests/tree_replay/test_pricing.py:13` to confirm the reference fixture's manual levels are replaced in the new integration test.
- `python -m pytest tests/tree_replay/test_levelmap.py -q --tb=short`: worker reports 40 passed in 5.65s; parent independently reports 40 passed in 5.59s. Reviewed as supplied evidence, not rerun here. The report records initial RED (31 missing-feature assertion failures), the corrected floating-point assertion, GREEN and nine supplementary characterization cases. No uncaptured test warnings reported; intentional overflow is asserted with `pytest.warns`.
- `python -m pytest tests/tree_replay tests/tree_spec tests/data_foundation/test_sessions.py -q --tb=short`: controller-owned, result not verified here.
- `python -m pytest -q --ignore-glob='*validator*' --tb=short`: controller-owned, result not verified here; explicitly excludes the legacy validator.
- No routine suites or focused experiments were run: static inspection resolved the named integration doubts. No nested agents, code edits, commits, worktrees, cleanup, live imports or data access. The sole authored artifact is this requested review.
