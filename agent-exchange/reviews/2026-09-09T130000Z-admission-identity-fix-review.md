# Agent Exchange Review

Reviewer:
Codex, continuing the final component review seat; requesting-code-review/code-reviewer.md. No nested agents.

Target request:
agent-exchange/inbox/codex/2026-09-09T130000Z-admission-identity-fix-review.md

Created at:
2026-09-09

Status:
REVIEW_READY_FOR_CODEX

Verdict:
Minor2: ADDRESSED.
Scoped spec compliance: PASS. Scoped quality: APPROVED.
No new Critical or Important issues caused by this fix. Minor1 remains deferred before another runner/CI. Parent retains component acceptance responsibility.

Findings:

- Minor2 ADDRESSED: `trading_system/tree_replay/state.py:24` retains the existing exact-string, nonempty and trimming checks, then validates UTF-8 encoding and translates UnicodeError into a field-specific ValueError. The existing constructor calls cover event_id, key and journal_id, so malformed identities now fail during ingestion rather than after an accepted journal reaches snapshot hashing or checkpointing. Valid identity text is neither normalized nor replaced; publication selection, payload handling and serialization are otherwise unchanged.
- Regression coverage directly exercises the reported defect: `tests/tree_replay/test_state.py:316` supplies lone high and low surrogates across all three identity fields and requires the field-specific UTF-8 error. The positive control at `:324` uses Hebrew, an emoji and an accented character, restores a checkpoint and verifies the snapshot identities and tracker row. This prevents an ASCII-only restriction from masquerading as the fix.
- Critical: none. Important: none. No additional finding within the requested fix scope.
- Minor1 from review125600Z remains explicitly deferred: `tests/tree_spec/test_admission_source.py:14` uses the machine-specific retained-source root. This fix neither addresses nor changes that finding; make the test root configurable before another runner/CI without silently skipping source verification.

Open questions:
None for the identity fix. The request describes the parent's expanded 677-case suite as running; this review does not claim its completion or result. The earlier component review's causal-frame, full-log, gate/lifecycle and false-readiness boundaries continue to apply.

Recommended next action:
Parent may close Minor2 and use this scoped approval with its completed integration evidence when recording component acceptance. Keep Minor1 deferred and preserve the earlier full-component scope limitations. No further identity runtime revision is requested.

Verification reviewed:

- Read the fix request first. Reused the original125600Z request/review, full ADMISSION-DEPENDENCIES-CONTRACT.md, reviewer instructions and mandatory repository startup reads from this same review session; refreshed the Codex inbox listing and inspected scoped git status. No broad review restart or other plan scratch.
- Read current state.py and the last24 test lines. A read-only comparison against the previously reviewed combined package confirmed exactly four runtime lines added to `_identity`, all original311 test lines unchanged, and20 appended test lines defining the seven new cases. No unrelated runtime change was included.
- Parent-reported RED: identity-selected cases6failed (DID NOT RAISE),1passed,93deselected in1.20s. Not independently rerun on the old code.
- Independently ran only the focused regression selection to verify the original serialization failure now rejects at ingestion while valid Unicode still reaches checkpoint/snapshot output:

  `python -B -m pytest tests/tree_replay/test_state.py -q --tb=short -p no:cacheprovider -k 'non_utf8_identity or non_ascii_identities'`

  PASS:7 passed,93 deselected in0.57s; exit0, clean output. Bytecode and pytest cache writes were disabled. No broad suite or source audit rerun.
- This requested review artifact is the only write. No nested agents, runtime/test edits, commits, acceptance/status changes, external data or domain-policy changes.
