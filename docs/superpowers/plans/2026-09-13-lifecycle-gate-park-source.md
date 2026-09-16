# Lifecycle gate, parking and retry source implementation plan

**Goal:** Recover the actual source decision that validates lifecycle claims,
parks claims the tape cannot yet judge, retries them, and persists only the
source-permitted journal effects.

**Architecture:** A private `LifecycleGate(source)` composes accepted
`ClaimVerifier(source)` and `OutboxJournal(source)`.  It shares the journal's
`LifecycleIdentity` instance so the actual process-local receipt cache is not
reset at each gate pass.  A source auditor compares the whole projected module
and invokes the real verifier, journal and identity auditors.

**Spec:** `docs/architecture/LIFECYCLE-GATE-PARK-SOURCE-CONTRACT.md`

## Global constraints

- Pin chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`,
  `chartdesk/tracker.py` blob `b616b34022e436545d8c1daf85eced51614fd74e`.
- Read/parse source only. Never import source, call a broker, send a message,
  use a real queue, or make a model/dataset/economic claim.
- Preserve source order, exception boundaries and clocks. Raw ports expose
  evidence/effects; they may not return pre-decided gate, verifier, queue,
  receipt or parked-state results.
- Any successful source audit still reports replay/training readiness false.

## Task 1 — Source gate and parking behavior

Create `trading_system/tree_replay/_vendor/lifecycle_gate.py`,
`tests/tree_replay/test_lifecycle_gate.py`, and
`docs/architecture/LIFECYCLE-GATE-PARK-SOURCE-USAGE.md`.

- [x] Read every selected source function plus both accepted child contracts;
  record source signatures, selected order and substitution counts before code.
- [x] Write a normal missing-module RED test suite using one raw in-memory
  source tape. It must drive actual matching, receipt cache, independent
  verifier, journal and parked JSON bytes; no fake `gate`/`verdict`/queue
  provider is permitted.
- [x] First literal test: an unmatched ordinary message is admitted unchanged,
  unparked, and persisted via the real journal; the method returns the original
  message list. Calculate the expected journal event ID externally.
- [x] Build the AST-projected runtime with `LifecycleGate(source)` creating
  one verifier and one journal, then assigning `threads = journal.threads`.
  Keep source method arguments/annotations/decorators, adding only `self`.
- [x] Prove ambiguity (with and without receipt), unknown message, target
  verifier route, ordinary verifier route, contradiction, stale park, success
  demotion, exact unpark and multi-message ordering.
- [x] Prove `_persist_gated_lifecycle` ordering: empty returns empty without
  effects; accepted messages enqueue actual context; duplicate accepted+blocked
  text and `STALE:` diagnostics do not add blocked journal effects; non-stale
  blocks enqueue then resolve an actual `blocked_lifecycle` entry; return is
  original `msgs`, not `send`.
- [x] Prove park first-write retention, malformed/absent input boundaries,
  full-line keys, exact-text removal, atomic writer sequence/failure cleanup,
  strict expiry, silent missing trade, stale retention, successful release with
  original born time, contradiction/expiry loss note and courtesy-note failure.
- [x] GREEN the focused runtime suite with the accepted claim-verifier,
  lifecycle-identity and outbox tests. Request independent task review; address
  findings with focused regression and fresh verification.

## Task 2 — Independent source proof

Create `trading_system/tree_spec/lifecycle_gate_park_source.py`,
`tools/check_lifecycle_gate_park_source_parity.py`, and
`tests/tree_spec/test_lifecycle_gate_park_source.py`.

- [x] Write normal missing-auditor RED, including direct inherited graph and
  readiness assertions. Include source mutation tests for all pins, order,
  signatures, decorators, substitutions, constructor sharing, decision order,
  stale/contradiction distinction, persistence skips, park first-write,
  expiry boundary, raw atomic sequence and child-audit drift/errors.
- [x] Implement literal source extraction/projection and full runtime AST
  comparison. It must audit actual claim-verifier, outbox-journal and
  lifecycle-identity dependencies—not accepted boolean placeholders.
- [x] Implement explicit-root JSON CLI with exit 0 only on verified and 2 for
  every blocker. Cover unrelated cwd and inert import guards.
- [x] GREEN runtime, source-audit and all child suites; run the retained-source
  CLI; get an independent task review and then a separate combined final review.
- [x] On final acceptance, update the usage document, master tracker and
  `AGENTS.md` with narrow scope/evidence; retain the master plan as active.

## Explicitly deferred

The next source closure is original caller ordering, bar/live resolver binding,
watch/process checkpoint semantics and causal artifact scheduling. Full replay,
other branches, simulation, historical labels, datasets, model training,
promotion, live delivery and broker execution remain outside this component.
