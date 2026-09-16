Spec compliance: PASS for the five-file Task2 delta, with verification limits below.
Task quality: Approved; no Critical or Important findings.

# Agent Exchange Review

Reviewer: Codex scoped Task2 reviewer

Target request: `agent-exchange/inbox/codex/2026-09-09T115500Z-reversal-producer-source-review.md`

Request: `agent-exchange/inbox/codex/2026-09-09T115500Z-reversal-producer-source-review.md`

Created at: 2026-09-09

Status: REVIEW_READY_FOR_CODEX

Verdict: Spec compliant within the reviewed scope; quality approved. This is a task review, not controller acceptance or whole-branch approval.

## Spec compliance and strengths

- All five requested deliverables appear as complete new-file hunks: `trading_system/tree_replay/_vendor/reversal_producer.py:1`, `tools/check_reversal_producer_source_parity.py:1`, `configs/trees/reversal-producer-contracts.json:1`, `tests/tree_replay/test_reversal_producer_source.py:1`, and `docs/architecture/REVERSAL-PRODUCER-SOURCE-USAGE.md:1`. Base/head is `c1b6071633c55376c64f0a98ece843706f420f49`; the review uses the supplied uncommitted delta, not HEAD-to-HEAD.
- The sidecar has exactly the prescribed five imports and required keyword-only interface. It imports accepted math instead of reimplementing it; the original docstring precedes only the permitted dependency bindings and explicit clock replacement (`trading_system/tree_replay/_vendor/reversal_producer.py:1`, `trading_system/tree_replay/_vendor/reversal_producer.py:8`).
- The original map-first daily gate, asymmetric bar correction gate, M5/M15 ordering, ten-day requests, per-fetch exception continuation, detector freshness arguments, global confirmation ordering/M5 tie-break, and selected-only pricing remain intact (`trading_system/tree_replay/_vendor/reversal_producer.py:14`, `trading_system/tree_replay/_vendor/reversal_producer.py:18`, `trading_system/tree_replay/_vendor/reversal_producer.py:30`). Complete `conflicts` remains unchanged, including candidate-tradeability asymmetry (`trading_system/tree_replay/_vendor/reversal_producer.py:36`).
- Audit identities and the expected whole manifest are independently defined in code, including the accepted map-manifest seal. Canonical serialization distinguishes false from zero; source preconditions precede transformation; the entire ordered vendor AST is compared (`tools/check_reversal_producer_source_parity.py:18`, `tools/check_reversal_producer_source_parity.py:43`, `tools/check_reversal_producer_source_parity.py:71`, `tools/check_reversal_producer_source_parity.py:152`). The manifest records the same narrow adaptation and false readiness (`configs/trees/reversal-producer-contracts.json:15`).
- The dependency audit is invoked even after a map-manifest error, requires literal true subset flags, empty blockers and literal false readiness, and converts declared input errors into blocked results. The top-level audit requires exactly one matching chart-desk pin, reads source/vendor as text, and exposes the requested CLI precedence and exit codes (`tools/check_reversal_producer_source_parity.py:125`, `tools/check_reversal_producer_source_parity.py:152`, `tools/check_reversal_producer_source_parity.py:188`).
- Tests use explicit synthetic OHLCV histories, supplied low-level maps/corrections, the real detector and real pricing. Detector instrumentation delegates the real call (`tests/tree_replay/test_reversal_producer_source.py:42`, `tests/tree_replay/test_reversal_producer_source.py:77`, `tests/tree_replay/test_reversal_producer_source.py:97`). The reviewed test hunk covers the requested daily/bar gates, fetch exceptions/order, equal/newer confirmation selection, older nonsignal-bar case, both 370-second boundaries, nearest-anchor episode behavior, refused-winner selection, conflicts matrix, and relocated audit mutations. Pricing instrumentation also delegates real math and proves an older paying alternative exists.
- Documentation clearly separates source pricing/conflicts from public admission, explains same-T map responsibility and the internal detector seam, retains false public readiness/tradeability, and leaves outer gates and B-I work open (`docs/architecture/REVERSAL-PRODUCER-SOURCE-USAGE.md:23`, `docs/architecture/REVERSAL-PRODUCER-SOURCE-USAGE.md:65`, `docs/architecture/REVERSAL-PRODUCER-SOURCE-USAGE.md:99`). The 42-line runtime sidecar and 203-line auditor have distinct responsibilities; the larger test file is organized into behavior fixtures and audit mutations.

## Findings

Critical: None found.

Important: None found. The narrow fetch exception continuation at `trading_system/tree_replay/_vendor/reversal_producer.py:21` is the explicitly required, tested source behavior; other runtime failures are not blanket-caught by this sidecar.

Minor: `.superpowers/sdd/2026-09-09-reversal-producer-asof/task-2-report.md:161` records LF/CRLF advisories from the five `git diff --no-index --check -- NUL ...` commands and their combined exit 1. These are verification-output noise, not a demonstrated source defect or a passing zero-exit whitespace check. Preserve that qualification when recording controller verification; the same report at line 83 explicitly says the final pytest run had no warnings.

## Open questions / cannot verify from this diff

- Transitive accepted dependency correctness and the historical acceptance of the independently embedded map-manifest hash are outside these five files. The new auditor visibly invokes and gates the accepted map auditor (`tools/check_reversal_producer_source_parity.py:125`); its inherited implementation and acceptance provenance were not re-reviewed. Controller should connect the reported CLI PASS to the accepted dependency state.
- Existing default APIs/result hashes, absence of edits to all pre-existing dependencies, actual same-T map reconstruction, and false public output flags cannot be established by an additive sidecar diff. Task1 wrappers were separately changed and explicitly excluded; Task3/public bridge integration is also excluded. These are controller integration checks, not missing Task2 deliverables (`docs/architecture/REVERSAL-PRODUCER-SOURCE-USAGE.md:99`).
- RED/GREEN history, the reported unchanged hashes of 29 existing files, and the reported fresh controller CLI run are reported evidence, not independently rerun or reconstructed in this review. No test execution or broad branch-state attestation is claimed.

## Verification reviewed

- Read the assigned request, complete brief and implementer report, review template, and requested task-reviewer instructions. Reviewed `.superpowers/sdd/2026-09-09-reversal-producer-asof/task-2-review-package.diff` as the sole changed-code view. The initial combined tool response was truncated, so the package was retrieved again to obtain its complete text; no changed file was opened separately and no second semantic diff pass was performed.
- Named outside-code risk: an apparently exact source projection could preserve the wrong original body, signature or provenance. One focused read checked `docs/architecture/REVERSAL-PRODUCER-SOURCE-CONTRACT.md` and only the retained checkout's `chartdesk/level_reversal.py:269` through EOF (`conflicts` starts at line 294). The source identity agrees with the contract; direct textual comparison matches the sidecar after the explicitly allowed adaptations. Source text was not executed; commit/blob Git verification itself was not rerun.
- Reviewed reported command `python -m pytest tests/tree_replay/test_reversal_producer_source.py -q --tb=short`: final PASS, 105 passed in 68.07s, following documented RED and fixture-fix runs. Reviewed reported command `python tools/check_reversal_producer_source_parity.py`: PASS/exit 0, VERIFIED, true subset flags, empty blockers, false readiness. These statuses are attributed to the implementer report; no uncovered risk justified repeating them.
- No tests, Git commands, source/feed execution, subagents, implementation edits, commits, pushes or cleanup were performed. The assigned review report is the only write, made with `apply_patch`.

Recommended next action: Controller may accept Task2 after reconciling the explicit dependency/verification limits with its own evidence; continue the separately scoped integration review for Task1/Task3.
