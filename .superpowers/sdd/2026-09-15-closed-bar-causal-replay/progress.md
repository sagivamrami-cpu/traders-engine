# SDD ledger — plan: docs/superpowers/plans/2026-09-15-closed-bar-causal-replay.md

## Setup

- Workspace: current dedicated branch `plan/tree-to-trained-model-langgraph` in
  the shared program checkout. `git-dir` equals `git-common-dir`, so it is not
  a linked worktree. Ruling: retain this user-scoped branch rather than create
  a second worktree over the large intentional dirty program. Cost if wrong:
  unrelated local edits could obscure a review diff; mitigate with exact scoped
  paths, pre/post status inspection, and focused verification.
- Base commit: `c1b6071633c55376c64f0a98ece843706f420f49`.
- Authority read: `docs/superpowers/specs/2026-09-15-closed-bar-causal-replay-design.md`.
- Plan read: `docs/superpowers/plans/2026-09-15-closed-bar-causal-replay.md`.
- Tooling ruling: the supplied SDD Bash script has CRLF line endings under the
  Windows Bash host. The workspace path is nevertheless fixed by its documented
  formula and this ledger occupies that exact path. Cost if wrong: helper
  artifacts might need manual paths; no runtime/product behavior is affected.

## Task 3 - accepted after corrective review

- Initial checkpoint review found six causal-resume defects: unbound ledger
  anchors, mutable provider evidence, distinct clocks, over-precision time
  parsing, provider-evidence backdating, and ledger-anchor clock backdating.
- The accepted implementation adds an externally retained provider baseline,
  exact ledger-anchor/event-prefix binding, exact shared-clock identity, strict
  extended/basic ISO precision checks, and monotonic schedule/anchor chronology.
- Evidence: full compatibility suite `187 passed`; final independent acceptance
  APPROVED in `.superpowers/sdd/2026-09-15-closed-bar-causal-replay/task-3-acceptance-review.md`.
- Boundary maintained: offline supplied-evidence/checkpoint infrastructure only;
  no runner, tracker row, delivery, economic label, dataset, model, or readiness claim.

## Task 4 - accepted after corrective review

- The runner now validates event-to-provider binding before moving the shared
  clock: one required internal-reversal event for the exact pass input, plus
  exactly one matching eligible event per due admission publication.  Every
  ledger row commits full event-payload digests, binding metadata and the
  retained provider-baseline fingerprint without retaining raw payload.
- Initial independent review found that a non-required event could substitute
  for the required reversal-input event.  Fix round 1 requires the one exact
  required event itself to carry the current pass binding and proves that the
  globally unique eligible binding is the same event.  Two regression cases
  prove unbound and wrong-pass required events block before provider use.
- Evidence: controller verification `240 passed in 45.22s`; initial binding
  review `CHANGES_REQUESTED`; scoped re-review `ACCEPTED`, with one finding
  addressed and none open, in
  `.superpowers/sdd/2026-09-15-closed-bar-causal-replay/task-4-binding-r1-rereview.md`.
- Boundary maintained: offline supplied-evidence replay only; new selected
  plans remain `OBSERVE_ONLY`, and there is no tracker creation, delivery,
  broker, economics, dataset, training, model or readiness claim.

## Task 5 - complete

- Published `docs/architecture/CAUSAL-REPLAY-USAGE.md` and updated project
  memory/tracker with the exact bounded API, event-binding rule, checkpoint
  boundary, static source-audit command and excluded scope. The documentation
  does not invent a bundle start time or promise public replay/training
  readiness.
- Controller acceptance evidence: source CLI returned `VERIFIED`, with no
  blockers and both readiness flags false; the prescribed focused suite passed
  `278` tests in `65.96s`.
- Independent final review found `0` Critical and `0` Important findings and
  accepted Tasks 1-5 in
  `.superpowers/sdd/2026-09-15-closed-bar-causal-replay/final-acceptance-review.md`.
- Task 5: complete (documentation, acceptance evidence and final review clean).
- Boundary maintained: the accepted component is not a historical data feed,
  full outer admission loop, economic simulator, outcome-label/dataset builder,
  trained model or production/trading permission.

## Task 2 - accepted after corrective review

- Initial independent review correctly rejected a presence/order-only outer-gate
  proof: a future source pin could preserve calls and line numbers while disabling
  the rejecting branch.
- The accepted revision proves each of the six exact outer-gate predicates and
  its loop-targeting rejection continue before record, and includes direct
  tree-before-reversal and engine-before-reversal mutation coverage.
- Evidence: focused suite `38 passed`; explicit parent-root CLI returned JSON
  `VERIFIED` with both readiness flags false; corrective independent review
  APPROVED in `.superpowers/sdd/2026-09-15-closed-bar-causal-replay/task-2-revision-independent-review.md`.
- Boundary maintained: static parse-only source proof. The public projection
  labels outer gates only `UNWIRED_OUTER_ADMISSION`; it implements no replay,
  tracker row, delivery, economic label, dataset, model, or readiness claim.

## Task 1 - accepted after corrective review

- Initial independent review rejected the first submission because hidden forbidden
  fields were accepted in payloads/diagnostics and payload timestamps could be
  silently truncated beyond microsecond precision.
- The accepted revision rejects the four forbidden keys recursively in event
  payloads, candidates, and diagnostics, and rejects over-microsecond payload
  timestamps before parsing.
- Evidence: focused suite `53 passed`; `py_compile` passed; scoped whitespace
  checks passed; corrective independent review APPROVED in
  `.superpowers/sdd/2026-09-15-closed-bar-causal-replay/task-1-revision-independent-review.md`.
- Boundary maintained: supplied immutable evidence/ledger only. No tracker row,
  delivery, source execution, network/filesystem action, economic label,
  dataset, model, or readiness claim was introduced.

## Preflight interface scan

| Tasks | Producer / consumer | Finding and ruling |
| --- | --- | --- |
| 1 → 3 → 4 | Task 1 owns bundle, pass, ledger and digest contracts; Tasks 3 and 4 consume them | Compatible. Ruling: Task 1 canonical digest is the sole bundle/ledger identity authority; later tasks must not hash mutable provider objects. |
| 2 → 4 → 5 | Task 2 produces static source-order proof; Task 4 follows the verified subset; Task 5 reruns it | Compatible. Ruling: static audit is not imported by runtime; it guards acceptance only. |
| 3 → 4 | Task 3 supplies one shared clock and reconstructable causal providers; Task 4 advances/restarts them | Compatible. Ruling: preserve omitted-clock behavior in `CausalAdmissionContext`; only explicit clocks join replay. |
| 4 → 5 | Task 4 emits raw observations/lifecycle facts; Task 5 documents acceptance | Compatible. Ruling: no `tracker.record`, economic, dataset, training or readiness field may be introduced in Task 4 or asserted in Task 5. |
| 1 ↔ 2 | Activation evidence names alert-enabled source state while Task 2 proves the source guard | Compatible. Ruling: activation is a ledger diagnostic only in this slice because outer admission is unbound; it cannot create a tracker row. |
