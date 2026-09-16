# Task 3 final independent acceptance review

Created at: 2026-09-14

Status: APPROVED

## Scope and method

Read-only final review of Task 3 in
`docs/superpowers/plans/2026-09-15-closed-bar-causal-replay.md` and its design,
all Task 3 implementation/revision reports and independent reviews, and the
current checkpoint/context/provider code and tests. Startup exchange material
and the Codex inbox were checked. No implementation or test edit, subagent,
commit, retained-source execution, or source-audit CLI execution was performed.

## Acceptance evidence

- **Ledger anchor and event prefix:** `checkpoint_from()` and
  `restore_checkpoint()` both call `_validate_ledger_prefix()`. Each consumed
  ledger row must match the same indexed immutable anchor's `pass_id` and exact
  `decision_time`, and its consumed IDs must equal the ordered
  `events_before_or_at(anchor.decision_time)` prefix. Creation and
  checksum-recomputed restore rejections are covered by
  `test_checkpoint_creation_rejects_a_legal_ledger_for_the_wrong_bundle_anchor`
  and `test_restore_rejects_checksum_recomputed_bundle_incompatible_ledger`.

- **Provider baseline forged source/schedule:** a caller-retained
  `ReplayProviderBaseline` fingerprints the original watch identity and
  admission provider/schedule image. Restore requires that fingerprint and
  exact remaining publication/lock suffixes, reconstructing the expected
  current provider image from only the trusted consumed prefix. Recomputed
  forged watch-source, publication/lock substitution, and publication-addition
  checkpoints are covered by the provider-source/schedule tests.

- **Exact shared-clock identity:** creation requires
  `watch.source._clock is admission._clock`; restore validates one exact
  `ReplayClock` at the checkpoint time and supplies that same object to both
  reconstructed providers. The time-equal but distinct clock rejection is
  directly covered by
  `test_checkpoint_creation_requires_the_same_clock_object_for_both_providers`.

- **Extended and basic submicrosecond timestamps:** both restore parsers reject
  fractional ISO seconds longer than six digits before `datetime.fromisoformat`,
  for extended and basic date/time spellings. Checksum-recomputed outer and
  packed-snapshot regressions cover all four surfaces.

- **Provider-evidence backdating:** trusted-baseline matching rejects a
  checkpoint if any consumed publication is after its restored clock, or if a
  consumed lock step starts or completes after that clock. The publication-only
  and lock-only recomputed-backdate tests each isolate their respective guard.

- **Ledger-anchor clock backdating:** creation and restore call
  `_validate_checkpoint_clock()` after validating the ledger prefix, rejecting
  a nonempty ledger when the shared clock precedes the last consumed immutable
  anchor. Direct creation and checksum-recomputed restore regressions use no
  provider schedule, so this protection is independently demonstrated.

The reviewed paths remain supplied-evidence checkpoint infrastructure only:
they add no runner, tracker recording, delivery, economic label, dataset,
training, model, live-trading, or readiness-positive behavior.

## Verification

```text
python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_admission_context.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_watch_storage.py tests/tree_replay/test_shared_clock.py -q --tb=short -p no:cacheprovider
187 passed in 19.83s
```

## Verdict

APPROVED. Task 3 meets its shared-clock and resumable causal-provider checkpoint
contract. This approval is limited to Task 3 and does not accept the Task 4
replay runner or establish replay, training, economic, or live-trading
readiness.
