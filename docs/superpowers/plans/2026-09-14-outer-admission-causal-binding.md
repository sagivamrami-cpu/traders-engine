# Outer Admission Causal Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Admit a source-selected level-reversal candidate into the offline
tracker only when the source outer-admission path is reproducibly satisfied by
causal supplied evidence.

**Architecture:** Add a bounded admission contract/adapter beside the existing
closed-bar replay runner. Reuse audited source helpers through explicit offline
ports; retain the actual producer `Plan` internally; append only detached
admission facts to the ledger. No runtime source import, delivery, broker or
economic behavior is permitted.

**Tech Stack:** Python 3, dataclasses, existing `tree_replay` causal contracts,
source-audited vendor projections, pytest.

**Spec:** `docs/superpowers/specs/2026-09-14-outer-admission-causal-binding-design.md`

## Global Constraints

- Pin and audit the approved chart-desk source commit/blob; no local HEAD
  substitution.
- Inputs are supplied, immutable and available at or before pass time.
- Retain source gate order and source-specific error behavior; do not invent
  thresholds, a quality veto or a universal missing-data rule.
- `ADMITTED_TRACKER` is not a fill or economic label.
- Keep `ready_for_replay` and `ready_for_training` false.
- Do not write raw market/log data, call network/broker/Telegram, or alter live
  alert behavior.

---

### Task 1: Define causal admission contracts

**Files:**
- Modify: `trading_system/tree_replay/causal_replay_contracts.py`
- Create: `trading_system/tree_replay/outer_admission_contracts.py`
- Test: `tests/tree_replay/test_outer_admission_contracts.py`

**Interfaces:**
- Consumes: `ReplayEvent`, `ReplayPassAnchor`, `TrackerActivationEvidence`.
- Produces: exact immutable `OuterAdmissionInputs` and
  `OuterAdmissionDecision` records with canonical evidence digests.

- [x] Write failing tests that reject future/missing/duplicate bindings, invalid
  source variant, raw economic fields and mutable/logically ambiguous inputs.
- [x] Run the new test file and confirm RED failures are caused by absent
  contracts.
- [x] Implement the smallest immutable contracts and canonical validation.
- [x] Add tests proving public serialization carries only commitments and
  diagnostics, never raw log/frame payloads.
- [x] Run focused tests GREEN.

### Task 2: Audit and expose the exact outer gate sequence

**Files:**
- Modify: `trading_system/tree_spec/causal_replay_source.py`
- Modify: `tools/check_causal_replay_source_parity.py`
- Test: `tests/tree_spec/test_causal_replay_source.py`
- Create: `tests/tree_spec/test_outer_admission_source.py`

**Interfaces:**
- Consumes: retained source root and pinned commit/blob identities.
- Produces: a static verified projection of reversal gate calls and required
  branch order, never imported by runtime replay.

- [x] Write mutation tests for omitted/reordered hunting, entry-clock,
  post-stop, occupied-slot, same-level, episode and tracker-record calls.
- [x] Confirm each mutation causes RED audit failure.
- [x] Extend the source audit to validate the full ordered reversal path and
  publication/record gate semantics against the pin.
- [x] Verify CLI output remains `VERIFIED` only for exact source and false for
  wrong root/commit/blob/order.

### Task 3: Implement offline outer-admission adapter and ports

**Files:**
- Create: `trading_system/tree_replay/outer_admission.py`
- Create: `trading_system/tree_replay/outer_admission_ports.py`
- Test: `tests/tree_replay/test_outer_admission.py`

**Interfaces:**
- Consumes: `OuterAdmissionInputs`, one actual source-selected `Plan`, shared
  `ReplayClock`, `CausalWatchStorage`, `CausalAdmissionContext`.
- Produces: `OuterAdmissionDecision` and at most a changed supplied tracker
  state via the existing offline `TrackerAdmission` port.

- [x] Write separate failing behavior tests for each source stop point and its
  trace ordering; assert later gates and tracker record are not called.
- [x] Write RED tests for source-enabled recording, disabled activation,
  duplicate geometry, corrupt state, no applicable stopped row, and log-tail
  evidence paths.
- [x] Implement a minimal private port adapter; it must expose only injected
  state/frames/quotes/log prefix/clock and never disk/network/live IO.
- [x] Implement the source-order orchestration with detached traces; preserve
  source optional-dependency catches as recorded diagnostics.
- [x] Prove successful `record` adds exactly one advisory tracker row and does
  not set broker/economic fields.
- [x] Run focused adapter tests GREEN.

### Task 4: Bind the adapter into closed-bar causal replay

**Files:**
- Modify: `trading_system/tree_replay/causal_replay.py`
- Modify: `trading_system/tree_replay/causal_replay_checkpoint.py`
- Modify: `trading_system/tree_replay/causal_replay_contracts.py`
- Test: `tests/tree_replay/test_causal_replay.py`
- Test: `tests/tree_replay/test_causal_replay_checkpoint.py`

**Interfaces:**
- Consumes: internally retained selected `Plan`, per-pass `OuterAdmissionInputs`
  and the shared causal providers.
- Produces: ledger records distinguishing observation, rejection, block and
  source-admitted tracker registration.

- [x] Write RED tests showing unbound/future admission evidence blocks before
  watch/tracker mutation, and disabled activation remains observe-only.
- [x] Write RED checkpoint tests that one-shot and resumed admitted/rejected
  passes have identical tracker state and ledger digest.
- [x] Thread the actual selected Plan without reconstructing it from public
  candidate data; call the adapter after source-approved lifecycle placement.
- [x] Extend ledger/checkpoint validation while preserving raw-payload-free
  serialization and all false readiness flags.
- [x] Run focused replay/checkpoint tests GREEN.

### Task 5: Verify boundary and record acceptance

**Files:**
- Create: `docs/architecture/OUTER-ADMISSION-CAUSAL-REPLAY-USAGE.md`
- Create: a timestamped acceptance record under `agent-exchange/status/`

- [x] Run source audit CLI against an explicit retained source root.
- [x] Run the complete focused contract/source/adapter/replay/checkpoint suite.
- [x] Add an integration test that fails if `TrackerAdmission.record` is called
  for a rejected, blocked or disabled pass **which stopped before the record
  gate**; preserve the distinct source-style post-attempt record-failure path.
- [x] Document exact scope, source pin, evidence inputs and exclusions.
- [ ] Obtain and process independent review before accepting the component.

## Required verification command

```powershell
python -B -m pytest tests/tree_replay/test_outer_admission_contracts.py tests/tree_replay/test_outer_admission.py tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_spec/test_outer_admission_source.py tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider
```

The command must pass only after implementation. Source parity must separately
report `VERIFIED` with both public readiness flags false.
