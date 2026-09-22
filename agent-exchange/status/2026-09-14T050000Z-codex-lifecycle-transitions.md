# Codex final acceptance — tracker lifecycle transitions source component

Plan: `docs/superpowers/plans/2026-09-14-tracker-lifecycle-transitions-source.md`.

Status: **ACCEPTED_BY_CODEX**.

The accepted offline component recovers the pinned tracker’s selected
transition/message helper set: conservative ambiguity handling,
published-protection results, progress ladder state/messages, fill/target/
cancel formatting and terminal state stamping. Only `_mark_terminal` adapts
the source wall clock to supplied `source.now_epoch()`.

The static source proof pins chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`; it requires the actual
lifecycle-primitives proof and its lifecycle-bars, desk-success and
lifecycle-voice projections. Immutable child identity, malformed child reports
and unexpected CLI serialization errors fail closed.

Final evidence:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_transitions.py tests/tree_spec/test_lifecycle_transitions_source.py tests/tree_spec/test_lifecycle_primitives_source.py
73 passed in 48.51s
python tools/check_lifecycle_transitions_source_parity.py --source-root <retained-root>
VERIFIED; blockers=[]
```

Task and final combined reviews are PASS. Both readiness flags remain false.
This is not the closed-bar/live resolver body, causal feed path, persistence,
delivery, execution/fill/economic outcomes, replay, dataset or model work.
