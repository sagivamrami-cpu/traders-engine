# Task 5 documentation implementation report

## Status

Documentation implementation completed for review. This report does not record
final acceptance, does not change Task 5 plan checkboxes, and does not assert
that the bounded replay spine is ready for public replay or training.

## Source contract read

Read the required project guidance, Task 5 brief, closed-bar causal replay
design, accepted Task 4 status, and Task 4 evidence-binding re-review. Inspected
the current `causal_replay_contracts.py`, `causal_replay.py`,
`causal_replay_checkpoint.py`, replay tests, and provider usage interfaces
before documenting them.

## Changed documentation

- Added `docs/architecture/CAUSAL-REPLAY-USAGE.md`.
  - Documents explicit supplied-evidence construction with a caller-selected
    initial `ReplayClock`; it does not invent `ReplayEvidenceBundle.start_at`.
  - Documents the exact supported `ClosedBarCausalReplay` constructor,
    `run()`, `run_until()`, `restore()`, ledger inspection, and retained
    `ReplayProviderBaseline` requirement for resume.
  - States the exact three-field `evidence_binding` payload and the
    exact-one-required-event rule for internal-reversal inputs, plus the unique
    binding requirement for due admission publications.
  - Describes raw-payload-free event commitments and the source-auditor command.
  - Lists excluded scope and preserves false public replay/training readiness.
- Updated `AGENTS.md` with a pointer and narrow summary of the accepted Task 4
  slice, explicitly stating that Task 5 evidence and review remain pending.
- Updated `docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md` so Plan
  area C and the execution sequence accurately distinguish accepted Tasks 1-4
  from pending Task 5 acceptance evidence/review and all remaining vertical
  replay/model work.

## Scope controls preserved

No production code or tests changed. No plan checkbox changed. No final
acceptance/status file was created. No raw market payload, economic output,
dataset/training output, source execution, commit, push, or subagent action was
performed.

## Verification

```powershell
python -B -c "from pathlib import Path; assert Path('docs/architecture/CAUSAL-REPLAY-USAGE.md').is_file(); print('DOC_EXISTS')"
```

PASS: `DOC_EXISTS`

```powershell
python -B -c "from pathlib import Path; text=Path('docs/architecture/CAUSAL-REPLAY-USAGE.md').read_text(encoding='utf-8'); required=('ReplayClock','run_until(pass_count)','ClosedBarCausalReplay.restore','evidence_binding','INTERNAL_REVERSAL_INPUT','ADMISSION_PUBLICATION','required_event_ids','raw-payload-free','check_causal_replay_source_parity.py','ready_for_replay=False','ready_for_training=False'); assert all(item in text for item in required); assert 'bundle.start_at' not in text; print('DOC_CONTENT_OK')"
```

PASS: `DOC_CONTENT_OK`

```powershell
git diff --check -- AGENTS.md docs/architecture/CAUSAL-REPLAY-USAGE.md docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md .superpowers/sdd/2026-09-15-closed-bar-causal-replay/task-5-docs-report.md
```

PASS: no whitespace errors. Git emitted only the existing LF-to-CRLF warning for
`AGENTS.md`; it did not report a diff-check violation. The named usage, tracker,
and report files are currently untracked in the shared worktree, so Git's
tracked-file diff check has no patch for those files; their content was also
reviewed directly.

## Concerns

- The Task 5 brief's illustrative constructor referenced `bundle.start_at`, but
  the inspected `ReplayEvidenceBundle` API exposes no such field. The usage
  document instead requires an explicit initial clock time matching the
  supplied providers.
- Task 4 is accepted, but Task 5 final acceptance evidence and independent
  review remain pending. The documentation consequently makes no broad
  ready-for-replay claim and retains false public readiness.
