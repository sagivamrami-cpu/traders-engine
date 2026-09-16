# Codex final acceptance — lifecycle live-evidence source component

Plan: `docs/superpowers/plans/2026-09-14-lifecycle-live-evidence-source.md`.

Status: **ACCEPTED_BY_CODEX**.

The accepted offline component recovers only the source tracker facts needed
before a later live resolver may assess evidence: fresh quoted prices and
whether timestamped historical bars can describe a post-fill fact for an OPEN
trade. It preserves the pinned source's selected physical order:
`QUOTE_MAX_AGE_S`, `_live_prices`, `_historical_replay_safe`,
`FORCE_BAR_AGE_S`.

The source auditor pins chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`; it parses rather than executes
the retained source and fails closed for identity, projection or JSON-report
inconsistency. Task and final reviews passed; the final documentation finding
was repaired and independently re-reviewed.

Final evidence:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_live_evidence.py tests/tree_spec/test_lifecycle_live_evidence_source.py
34 passed in 8.59s
python -B tools/check_lifecycle_live_evidence_source_parity.py --source-root <retained-root>
VERIFIED; blockers=[]; ready_for_replay=false; ready_for_training=false
```

This is not corrected-bar acquisition, a fallback resolver, a state transition,
fill/exit calculation, outcome/economic label, replay, dataset, training,
model or live-trading artifact. Both readiness flags remain false.
