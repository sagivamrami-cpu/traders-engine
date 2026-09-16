### Spec Compliance

- **Spec compliant for the reviewed Task 2 implementation.** All four required files appear in the supplied package: `trading_system/tree_replay/pricing.py:1`, `tests/tree_replay/test_pricing.py:1`, `trading_system/tree_replay/levels.py:19`, and `trading_system/tree_replay/reversal.py:18`. Requirements are Task 2 and Global Constraints only in `docs/superpowers/plans/2026-09-09-reversal-pricing.md:14` and `:47`.
- **Cannot verify from this diff:** the complete Task 1 source-parity gate, including the authoritative producer's exact supported-symbol inventory. The wrapper imports the local source subset at `trading_system/tree_replay/pricing.py:97` and declares the three required exact identities at `:13`; `configs/trees/reversal-pricing-contracts.json:4` names commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`. The parent should retain Task 1's independent source-audit acceptance. The reported successful parity CLI was not rerun.
- **Cannot verify from this diff:** migration of previously stored level evidence/evaluation hashes or historical adapters. The optional field at `trading_system/tree_replay/levels.py:19` changes serialized evidence even when its value is null; `trading_system/tree_replay/reversal.py:18` correctly distinguishes this with adapter v2. Documentation remains Task 3; historical migration is not certified here.

### Strengths

- `trading_system/tree_replay/pricing.py:67`: the requested interface materializes bars once, recomputes detection internally, preserves blockers/no-candidate results, and restricts pricing to exact supported identities. It accepts no externally supplied candidate payload.
- `trading_system/tree_replay/pricing.py:99`: pricing reselects the detector's window and reconstructs all source Reversal fields before passing the full supplied level tuple to `build_plan` at `:123`. Source entry zones, stop bands, obstacles, measured targets, refusals, and warnings remain delegated to the pinned subset.
- `trading_system/tree_replay/pricing.py:24`: finite/positive validation covers entry, stop, ATR, zone boundaries, risk, targets, and obstacles; RR values must be finite. Missing targets become NOT_APPLICABLE at `:60`, while legitimate zero RR on refused plans remains intact.
- `trading_system/tree_replay/pricing.py:82`: pricing version and source commit augment the detector evaluation hash, which already includes selected inputs, level IDs, pandas/NumPy versions, and calendar evidence. Candidate IDs and detection snapshots are retained (`tests/tree_replay/test_pricing.py:121`).
- `trading_system/tree_replay/pricing.py:110`: publication time includes every selected bar, supplied levels, and calendar. Pricing features are PRE_ENTRY (`:58`); source acceptance remains explicitly unadmitted (`:129`). Existing candidate `tradeable=False`, `trade_plan=None`, and readiness flags survive (`tests/tree_replay/test_pricing.py:48`).
- `trading_system/tree_replay/levels.py:57`: repeated display names require distinct explicit IDs and prices; duplicate IDs and duplicate name/price observations are rejected. Numerical detector logic and signature have no changes in the supplied before-image diff. Repeated Q-QUARTER targets and identity fingerprint changes are tested at `tests/tree_replay/test_pricing.py:209` and `:240`.
- `tests/tree_replay/test_pricing.py:32`: synthetic integration tests assert actual long/short 5m/15m geometry, refusal semantics, source instruments, unsupported identities, generators, deterministic evidence, JSON serialization, and future-suffix exclusion. The 138-line wrapper separates orchestration, source-plan validation, and snapshot projection without introducing strategy thresholds or execution logic.

### Issues

- **Critical:** None found.
- **Important:** None found.
- **Minor:** None requiring a change in this task.

### Checks and evidence boundaries

- Read the supplied diff once; used its new-file contents and existing-file before-image hunks. Base/head are supplied as unchanged `c1b6071633c55376c64f0a98ece843706f420f49`; no Git commands, commits, worktrees, cleanup, or nested agents were used.
- **Named risk: as-of/provenance.** Checked `trading_system/tree_replay/bars.py:117`, `session_bars.py:22`, and the detector before-image at `.superpowers/sdd/2026-09-09-reversal-pricing/reversal-before.py:104`. Selection excludes unpublished/future bars; detector level blockers precede pricing. Existing negative coverage is present at `tests/tree_replay/test_reversal.py:118`, `:178`, and `:294`.
- **Named risk: candidate identity.** Checked the detector before-image at `:174` and `trading_system/tree_replay/_vendor/level_reversal.py:86`, `:210`. Source episode identity and confluence arbitration intentionally remain independent of explicit level IDs; level IDs distinguish evaluation evidence. The wrapper preserves that contract.
- **Named risk: original source contract.** Read the local pure `trading_system/tree_replay/_vendor/reversal_pricing.py:9` and relevant pricing functions/properties at `_vendor/pricing.py:195` and `:333`, plus the pinned manifest and Task 1 source handoff. No original source module was executed. Full source parity remains the cross-task item above.
- **Named risk: unchanged detector.** Compared the supplied version-only detector hunk with its before-image and inspected inherited blocker coverage. Numerical detection was not altered; serialized evaluation identities intentionally change under v2.
- **Focused verification: PASS.** Ran an inline `python -B -` probe using synthetic test fixtures: an interior bar published one second after decision produced HISTORY_GAP; future level publication produced LEVELS_UNAVAILABLE; levels observed 371 seconds earlier against a 370-second budget produced LEVELS_STALE. Each returned BLOCKED with no candidates. This specifically checks wrapper blocker propagation beyond the new test assertions at `tests/tree_replay/test_pricing.py:148`.
- Parent verification of **197 passed** is supplied evidence, also recorded at `.superpowers/sdd/2026-09-09-reversal-pricing/task-2-report.md:11`; the suite was not repeated. Only this review artifact was written.

### Assessment

**Task quality: Approved.** No blocking spec or quality defect was found within Task 2. The wrapper preserves source pricing semantics and as-of evidence while keeping admission, execution, and outcomes separate. This approval does not complete B-I, establish profitability, or authorize raw feeds, economic labels, fitting, promotion, deployment, or live alerts; the full goal remains active.
