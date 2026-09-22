# Agent Exchange Review

Reviewer: Codex independent final reviewer

Target request: `agent-exchange/inbox/codex/2026-09-13T232700Z-outbox-journal-final-review.md`

Created at: 2026-09-13 UTC

Status: REVIEW_READY_FOR_CODEX

Verdict:

- Spec compliance: PASS. The six-file component is an offline supplied-port projection of the pinned outbox journal. It preserves idempotent minute/text IDs, raw JSONL merge/deduplication, append-lock ownership and cleanup, malformed-line behavior, terminal/PENDING/LATE state handling, exact-text resolving, real `LifecycleIdentity` composition, and per-instance birth memory. The independent audit pins the retained source and checks the full projected vendor AST plus the real lifecycle-identity/tracker-admission audit chain. It keeps replay/training readiness false.
- Task quality: NEEDS MINOR DOCUMENTATION FIX. The implementation, proof, CLI, and focused regression coverage are otherwise approved; the included usage document still says that the source audit is pending/not built after the accepted audit and controller verification.

Findings:

#### Minor

- M1 — stale completion state in [OUTBOX-JOURNAL-SOURCE-USAGE.md](docs/architecture/OUTBOX-JOURNAL-SOURCE-USAGE.md:3) and [OUTBOX-JOURNAL-SOURCE-USAGE.md](docs/architecture/OUTBOX-JOURNAL-SOURCE-USAGE.md:46): it reports the source audit and task/final acceptance as pending and says the independent proof is not built. The accepted Task 2 status records that the audit exists and that the controller obtained 140 passing component tests plus a verified retained-source CLI result. Update the usage text to distinguish accepted source audit/controller verification from this still-pending combined final acceptance. This is documentation-state drift, not a runtime or source-projection defect.

No critical or important findings.

Evidence reviewed:

- Offline effect boundary and composition: `trading_system/tree_replay/_vendor/outbox_journal.py:37-40`, `:55-77`, and `:95-124`. The constructor is inert and owns `LifecycleIdentity`/instance `_BORN`; validation occurs before the clock; read/decision/write share one append lock; `_write` asserts the supplied sink is offline before opening it.
- Required pending-duplicate birth-memory regression: `tests/tree_replay/test_outbox_journal.py:254-268`. The parametrized 120/180 and ordinary/group-upgrade paths remember birth 90, enqueue the duplicate, then require the later 721 new PENDING row to omit `born`; this catches a `pop`-to-retain regression before either duplicate return path.
- Inert complete projection and inherited proof: `trading_system/tree_spec/outbox_journal_source.py:94-130` builds the expected AST from pinned source substitutions; `:149-189` checks repository/commit/blob, compares the vendor AST, and propagates real lifecycle-identity audit blockers. `:137-142` fixes both readiness flags false.
- CLI and audit tests: `tools/check_outbox_journal_source_parity.py:13-19` uses an explicit source root, emits JSON, and returns only verified/blocked exit codes; `tests/tree_spec/test_outbox_journal_source.py:41-48`, `:51-109`, `:174-199`, and `:217-232` cover the actual inherited graph, projection/order drift, child failure, explicit-root behavior, and inert-import guard.
- Static integrity: all six current SHA-256 values match the accepted Task 2 status record, including runtime `AEAF…84C3`, runtime tests `4DCF…19EC`, usage `5009…B9AF`, audit `8147…78DC`, CLI `E2E9…EF0F3`, and audit tests `3A4E…51B3`.

Open questions:

None requiring a human decision.

Recommended next action:

Make the M1 usage-document status correction, then have the controller record the combined component outcome. Do not expand this verdict into delivery, durability, replay certification, fills, economics, labels, training, or model readiness.

Verification reviewed:

- Direct static inspection of the request, final-review brief, plan, contract, both accepted task statuses, prior task/audit reviews, and all six scoped working-tree files.
- Focused static hash comparison against `agent-exchange/status/2026-09-13T232003Z-codex-outbox-journal-task2.md` and fixed-text verification of the stale usage statements.
- The controller-reported 140-case suite (22.38s) and retained-source CLI `VERIFIED` were reviewed as reported evidence and deliberately not rerun. No original source or replay runtime was imported/executed; no test suite was run.
