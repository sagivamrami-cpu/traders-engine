# Outer-admission causal replay usage

## Purpose and boundary

This is an **opt-in, offline** extension of `ClosedBarCausalReplay` for the
supported `level_reversal:5m` path. When a source-selected plan has passed the
supplied source-style outer gates, it may create one **advisory tracker record**.
The corresponding replay outcome is `ADMITTED_TRACKER`.

`ADMITTED_TRACKER` means only that a causally bound replay reproduced the
limited tracker-registration decision. It is not an order, fill, trade,
profit/loss result, outcome label, dataset row, or model prediction. Public
`ready_for_replay` and `ready_for_training` remain `False`.

With no outer-input mapping, the accepted baseline is unchanged: a selected
candidate remains `OBSERVE_ONLY` and no new tracker row is registered.

## Required evidence and construction

The caller supplies one immutable `OuterAdmissionInputs` value per pass which
will use outer admission. The value commits to the exact private `Plan` selected
by the internal producer through `plan_digest`; replay never reconstructs that
plan from public candidate data.

```python
replay = ClosedBarCausalReplay(
    bundle,
    clock=clock,
    watch=watch,
    admission=admission,
    reversal_inputs=internal_inputs,
    outer_admission_inputs=outer_inputs,
    baseline=baseline,
)
```

For every enabled pass there must be exactly one eligible `ReplayEvent` whose
binding uses consumer `OUTER_ADMISSION_INPUT`. Its artifact ID is the pass ID,
its artifact digest is the canonical digest of that exact
`OuterAdmissionInputs` record, and it must be available by the anchor decision
time. Missing, future, duplicate, or substituted evidence blocks the pass
before watch or tracker mutation.

The binding holds a digest, not raw supplied payloads. The ledger preserves
commitment metadata, not raw logs, market frames, or other caller evidence.

## What the adapter reproduces

For an opted-in selected plan, the adapter verifies the plan commitment and
then follows the audited source-style order: entry-quality annotation,
tradeability/refusal, trading-window and market-clock checks, post-stop and
open-slot checks, active-reversal visibility, episode handling, and the
tracker-record guard/registration path. A later gate never runs after an
earlier stop point.

The decision stores only status, gate trace, safe annotations, and tracker
identity after a successful advisory registration. Entry-quality annotations
may say that causal rejection-tail evidence was considered, but do not expose
raw logs and do not invent a quality veto.

The active-reversal mapping is local to the currently supported single
producer. It preserves same-pass visibility required by this path; it does not
establish full multi-producer arbitration.

## Inspecting and resuming

The replay ledger stores the admission decision as detached diagnostics. A
successful new registration has outcome `ADMITTED_TRACKER`; a source gate
rejection has `REJECTED`; invalid or unavailable causal evidence has `BLOCKED`.

Checkpoint restore must receive the same caller-supplied
`outer_admission_inputs` mapping. Bundle bindings and canonical artifacts are
verified again as the replay resumes, so a changed mapping cannot silently be
substituted.

```python
resumed = ClosedBarCausalReplay.restore(
    checkpoint,
    bundle=bundle,
    clock=resume_clock,
    baseline=baseline,
    reversal_inputs=internal_inputs,
    outer_admission_inputs=outer_inputs,
)
```

## Verification

Use the retained source root, not an arbitrary checkout, for the static source
order audit:

```powershell
python -B tools/check_causal_replay_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
```

The focused suite covers contracts, source projection, adapter behavior, replay
binding, and checkpoint/resume consistency:

```powershell
python -B -m pytest tests/tree_replay/test_outer_admission_contracts.py tests/tree_replay/test_outer_admission_ports.py tests/tree_replay/test_outer_admission.py tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_spec/test_outer_admission_source.py tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider
```

The static source-audit JSON retains the legacy field
`unwired_outer_admission`. It means that the static auditor neither imports nor
executes an outer-admission runtime; it is not a claim that this opt-in adapter
is absent. The runtime binding is established separately by the required
`OUTER_ADMISSION_INPUT` event and covered by the replay tests above. Neither
the audit nor the runtime adapter changes the false readiness flags.

## Explicit exclusions

This component does not provide source execution, historical acquisition, full
producer arbitration, a broker/order path, fills, delivery, economics, costs,
labels, feature construction, dataset generation, training, calibration, model
promotion, or live trading. It grants no production-data, raw-data-retention,
broker-execution, capital-allocation, deployment, or live-trading approval.
