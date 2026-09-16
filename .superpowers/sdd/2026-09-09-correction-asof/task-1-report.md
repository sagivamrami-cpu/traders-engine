# Task 1 implementation report

Status: IMPLEMENTED_AWAITING_CODEX_REVIEW
Created at: 2026-09-09T10:41:12Z
Implementer: Codex scoped worker
Request: agent-exchange/inbox/codex/2026-09-09T103339Z-correction-asof.md
Requirements: .superpowers/sdd/2026-09-09-correction-asof/task-1-brief.md

## Outcome and scope

Implemented the seven assigned Task 1 files, with self-review complete. Independent
review, acceptance, integration and broad verification remain controller-owned.
No other implementation scope was taken. The two explicitly requested report
files are additional reporting deliverables.

The pinned complete Correction class and EXCHANGE_NATIVE are retained, with the
broker_shape_ok predicate specialized only by renaming, adding the mandatory
keyword-only replay time, and replacing its single wall-clock expression.
The entire vendor module passes the fixed-source AST audit.

The public frozen CorrectionEvidence uses the existing validation conventions.
The assessor validates association and policy before temporal assessment, preserves
the required missing/future/unavailable/stale precedence, returns original quality
predicates for eligible evidence, and prevents blocked payloads from contributing
to either usable evidence or its hash. ASSESSED does not imply admission.
Both readiness flags remain false throughout.

## Changed files

All seven are newly created; no pre-existing implementation file was changed.

1. trading_system/tree_replay/_vendor/correction.py — complete source class,
   exact native set, narrowly specialized explicit-clock predicate.
2. trading_system/tree_replay/corrections.py — immutable evidence, validation,
   temporal assessment, canonical serialization and SHA256.
3. tools/check_correction_source_parity.py — fixed pins/manifest/imports/ordered
   symbols, source text/blob and full-module AST checks, fail-closed CLI.
4. configs/trees/correction-source-contracts.json — independently checked
   dependency scope, pins and three explicit adaptations.
5. tests/tree_replay/test_correction_source.py — source behavior and real CLI
   mutation tests using temporary copies, without changing fixed auditor pins.
6. tests/tree_replay/test_corrections.py — synthetic temporal, identity, quality,
   validation, immutability and hash behavior.
7. docs/architecture/CORRECTION-ASOF-USAGE.md — interfaces, synthetic example,
   policies, audit invocation, limitations and legacy replay-hook caveat.

Reporting deliverables:

- .superpowers/sdd/2026-09-09-correction-asof/task-1-report.md
- agent-exchange/status/2026-09-09T103339Z-worker-correction-asof.md

## Requirements and source checks

- Read Task 1 brief first, AGENTS.md, exchange README/protocol, original request,
  existing validators/auditor patterns, relevant design and current status.
- Inspected the Codex inbox without changing request status or any inbox file.
- Source was read only as text; never imported, executed or downloaded.
- Commit: 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9.
- basis.py Git blob: f3396f3a9fefd71f0f71422001a5521af0a05cd2.
- Retained source:
  C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk.
- Read and followed test-driven-development/SKILL.md and its full
  writing-good-tests.md instructions; used verification-before-completion.
  Behavioral expectations use literals and real evidence/source objects.
  Audit tests execute the actual auditor against temporary text fixtures;
  there are no monkeypatched production pins or substitute predicate mocks.

## RED evidence

Before creating any production file, ran exactly:

```text
python -m pytest tests/tree_replay/test_correction_source.py tests/tree_replay/test_corrections.py -q --tb=short
```

Exit 1. Exact progress and final output:

```text
FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF [ 35%]
FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF [ 71%]
FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF                [100%]
201 failed in 2.42s
```

Exact representative failure lines (repeated traceback details omitted):

```text
E   AssertionError: Missing assigned sidecar: trading_system.tree_replay._vendor.correction
E   AssertionError: Missing assigned sidecar: tools.check_correction_source_parity
E   AssertionError: Missing assigned source auditor
E   AssertionError: Missing assigned corrections adapter
```

These were assertion failures caused by the not-yet-created assigned modules and
auditor, not collection errors, missing retained source or live-service failures.
The tool truncated the long repeated RED traceback output; this report preserves
exact excerpts and the terminal count rather than claiming an untruncated log.

After the initial RED and production implementation, the controller supplied the
legacy replay-hook finding and requested explicit literal coverage. Added five
characterization cases: replay/OANDA and replay/native BTC in both predicate and
wrapper tests, plus rejection of the legacy dictionary note. These exercise
already-correct behavior and did not require production changes. No separate RED
is claimed for those five later-requested cases. Final total is 206.

## GREEN evidence

Ran the same required command after implementation and those additions:

```text
python -m pytest tests/tree_replay/test_correction_source.py tests/tree_replay/test_corrections.py -q --tb=short
```

Exit 0. Complete stdout, combining the initial tool chunk and terminal continuation:

```text
........................................................................ [ 34%]
........................................................................ [ 69%]
..............................................................           [100%]
206 passed in 21.83s
```

Ran:

```text
python tools/check_correction_source_parity.py
```

Exit 0. Complete stdout:

```json
{
  "blockers": [],
  "ready_for_replay": false,
  "ready_for_training": false,
  "source_commit": "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9",
  "source_subset_verified": true,
  "subset_verified": true
}
```

The configured retained source was available. Audit mutation coverage includes
manifest commit/blob/symbol/order/import/readiness drift, false-to-zero drift,
extra fields and malformed JSON; missing/duplicate/altered baseline pin; changed
source constant/branch/clock/additional clock/executable/syntax; changed vendor
constant/branch/restored wall clock/signature/import/rebinding/duplicate executable
definition/module order/omission/docstring/syntax; missing source/manifest/vendor/
baseline; CLI environment/argument precedence and CRLF source normalization.
Mutated files reside in temporary synthetic fixtures, never the retained source.
Missing fixture failures are explicit, not skips.

The focused behavioral coverage includes 7/20-day seam boundaries at one
microsecond before/exact/after; None, broker, native, proxy, replay and new vendor
sources; exact/wrong-case/wrong-venue identities; absent/current/future seam;
narrow unverified logic; complete class render/show behavior; offset signs;
validation of timestamps/numerics/text/association; delayed/future/stale evidence
and exact zero/integer freshness boundaries; canonical result fields and hash;
policy/evidence hash changes; blocked payload noninterference; frozen inputs and
independence of returned dictionaries.

No broad suite or integration tests were run, per controller instruction.
The controller's reported 65 source-range passes are external baseline context,
not verification performed by this worker.

## Self-review

- Compared the vendor body against the pinned source text and verified the
  full module AST audit succeeds. No extra vendor imports or executable code.
- Reviewed auditor expectations as independent literals, baseline multiplicity,
  blob newline normalization, the pre-specialization clock count, entire-module
  AST comparison, exception handling and exit codes. Auditing imports neither
  live source nor vendor module.
- Reviewed the public constructor and call contract: no enum narrowing, no
  association inference, no negative-offset rejection, no seam requirement for
  tv_spliced, no implicit age/lookback policy, zero age budget accepted.
- Reviewed temporal precedence and null blocked payload. Canonical hashes cover
  versions, policy, identity, decision time, readiness and selected evidence.
  An unavailable correction's payload does not influence the blocked hash.
- Reviewed literal replay source tests against basis.py lines 753–754, read as
  text: Correction(symbol, 0.0, "replay", "high", {"replay": True}). OANDA shape
  stays false; native BTC shape stays true; typed public notes remain strings.
- Reviewed all seven newly created files. git status confirmed their untracked
  status; git diff --check exited 0 on the tracked worktree changes, with
  pre-existing AGENTS.md/README.md CRLF advisories only. This git check does not
  inspect untracked files; those were inspected directly.
- No unresolved correctness finding or contract ambiguity identified.

## Concerns, boundaries and next action

No Task 1 blocker or decision is outstanding. Known boundaries are intentional:

- ASSESSED, source-shape true and audit success certify only this dependency.
  They do not construct the complete historical map, certify source frame
  contents, apply offsets or grant trade admission/replay/training readiness.
- Frame/provenance fields are caller attestations, not independently fetched
  or authenticated evidence.
- The legacy replay-hook dictionary note is deliberately not accepted by the
  typed public interface. Source replay is not mapped to tv_daily.
- Missing local pinned source will fail the tests/auditor; configure
  TR_CHARTDESK_SOURCE_ROOT or --source-root when moving to another machine.
- Broad tests, independent review and acceptance remain controller-owned.

Preserved unrelated dirty files. No subagents, commits, pushes, worktrees,
workspace cleanup, live imports, source downloads, real-data access, training,
deployment, live alerts or broker actions. Temporary fixture mutations solely
serve the explicitly requested fail-closed audit tests.

Recommended next action: controller independently reviews Task 1 and reruns the
focused verification before acceptance and any later integration.

