# Tracker lifecycle caller — offline usage and limits

`TrackerLifecycleCaller` is the accepted source-faithful **commit seam** for
the end of the tracker closed-bar and live resolver passes. It is not the
resolver itself.

```python
caller = TrackerLifecycleCaller(causal_source)

def closed_kernel(state):
    # Future source-projected bar resolver mutates `state` from raw evidence.
    return messages, changed

messages = caller.check(closed_kernel)
```

For a live pass, use `caller.check_live(live_kernel)`. The source context owns
the shared, reentrant lock policy. If that lock raises `LockBusy`, the public
call returns `[]` without loading, resolving, gating or saving. The original
broad exception boundary also returns `[]` if the supplied live kernel itself
raises `LockBusy`; this is retained source behavior, not a delivery result.

For either kernel, the state is loaded once. Empty state returns immediately.
The kernel must return exactly `list[tuple[str, bool]], bool`. If `changed` is
false, the raw messages are returned and no gate/save effect occurs. If true,
the sequence is exactly:

```text
resolve/mutate state → lifecycle gate/journal persistence → tracker save
```

The gate returns lifecycle tuples, not proof of transport delivery. The caller
does not run `replay_parked`; a future outer source pass must offer released
claims through the correct source context.

## Verification

```powershell
python -m pytest tests/tree_replay/test_lifecycle_caller.py tests/tree_spec/test_tracker_lifecycle_caller_source.py tests/tree_spec/test_lifecycle_gate_park_source.py tests/tree_spec/test_tracker_lock_source.py -q
python tools/check_tracker_lifecycle_caller_source_parity.py --source-root C:/path/to/retained-parent
```

The current accepted proof is 70 tests passing and a retained-source CLI
`VERIFIED` result. The auditor pins chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`, parses rather than imports source,
and invokes real lifecycle-gate/park and tracker-lock child proofs. It always
reports replay and training readiness false.

## What remains outside this component

No corrected-bar or quote mutation logic, fill/stop/target/progress behavior,
outcome write, parked replay context, transport, causal scheduler/checkpoint,
historical replay, economic execution simulation, labels, dataset, model,
promotion or live action is enabled by this component.
