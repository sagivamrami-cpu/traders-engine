# Tracker storage implementation report

Status: IMPLEMENTED_AWAITING_CODEX_REVIEW
Implementer: Codex main inline. Plan/spec named in progress.md.
Request: agent-exchange/inbox/codex/2026-09-09T155700Z-tracker-storage-review.md

Seven new deliverable files exactly as plan. Original _load/_save have explicit
memory/clock/guard/forensic/write ports; full-module independent AST projection
pins source repo,commit,blob and checks existing baseline pin. New causal seed
retains raw JSON key order and unavailable/absent/unreadable distinctions.
Backend records detached operation and artifact effects, fixedT state handoff.
No prior runtime modified, no disk/network/live-clock capability. No lock port
or complete quote/log/watch/lifecycle binding claimed. No model/data run.

## Verified chronology

- Existing tracker baseline106passed1.49s, exit0.
- New runtime tests first; both new runtime files absent. Normal collection then
  RED45failed0.98s, missing-module assertions (head/tail+summary observed, display
  truncated). Before runtime corrected invalid-seed test fixture to use replace
  so ABSENT with nonempty text is actually submitted; not silently normalized.
- Added runtime then samefocused command45passed0.51s, exit0.
- New audit tests before auditor/CLI:RED13failed7.84s missing-feature assertions;
  process24212 observed terminal via same handle after initial delayed return.
- Self-review found forensic serialization omitted in memory backend: source
  serializes before append, but new effect was deep-copied directly. Added
  test_unserializable_forensic_value_does_not_leave_a_creation_effect; focused
  RED1failed0.66s showed an incorrect effect remained after entry=object() failed.
  Fixed single root cause: serialize/UTF8-check effect before appending detached
  decoded data inside original best-effort boundary. Source wrapper unchanged.
- Implemented audit/CLI. Bothnewfiles59passed3.64s (46storage+13audit).
- Planned full5file suite306passed5.61s, exit0. Includes existing tracker,
  admission-frame and state tests; counts overlap previous runs, not additive.
- New parity CLI on retained-source-parent:VERIFIED,_load/_save/no blockers,
  readinessfalse. Tracked/no-index whitespace checks showed only LF/CRLF warnings;
  combined shell exit1 is no-index new-file differences, not parity failure.

Retained root:
C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149.
Exact commands are in usage/plan. All execution is implementer evidence; review
must not describe it as independent reproduction. No goal-completion claim.

## Self-review / adaptation / outstanding work

Read original _load/_save/_audit_creation, _locked and basis._atomic_write.
Source guard, reread, loss boundary, creation-before-quarantine, null treatment,
unsorted JSON and same-second quarantine naming retained. Audit compares full
module, not merely selected methods. New seed guards keep unknown/future/expired
state from turning into{} even under allow_shrink. Source load/record catch paths
retain trace failures. Real tracker tests use actual source storage, controlled
other ports; first matching same-level depends on original root insertion order.

Forensic PID/argv/stack cannot be reconstructed and are NOT fabricated. Explicit
replay_creation_effect rows preserve extraction/serialization boundaries. No
claim of byte-identical forensic logs or OS atomicity. Arbitrary process I/O
failures modeled only through fault-injected boundary tests. Full raw watch logs,
quotes, source lock behavior and state-machine transitions remain required.
State snapshot does not carry all traces/quarantines/forensics and is explicitly
not a complete replay checkpoint. Complete orchestration must own those effects.
No domain threshold/policy ruling. Main critical task inline; independent task
and full component reviews required. Full master scope remains active.

## Task-review Important1 fix

Review155700Z identified that swallowed extraction/serialization failures were
not visible in trace. New3regressions RED3failed0.75s because creation_effect
attempts were absent. Added per-effect call tracing inside unchanged best-effort
catch: parent audit/save can succeed while child is BLOCKED with exception.
Current full planned5file309passed5.73s; usage clarifies parent/child semantics.
Status160129Z gives details; same reviewer re-review pending. Source wrapper and
auditor unchanged. Pre-fix broad tree-suite process72087 is not fix acceptance.
Process72087 subsequently completed:2280passed246.83s. Since collection preceded
the Important1 delta and files changed during execution, this is broad diagnostic
evidence only, not a clean post-fix run. Current scoped309passed is authoritative
for the change. Fresh source CLI at16:04UTC again VERIFIED2/no blockers, exit0.
