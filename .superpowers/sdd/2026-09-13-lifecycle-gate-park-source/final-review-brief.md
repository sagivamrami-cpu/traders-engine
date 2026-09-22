# Final review brief — lifecycle gate, parking and retry

Review the complete six-file component:

1. `trading_system/tree_replay/_vendor/lifecycle_gate.py`
2. `tests/tree_replay/test_lifecycle_gate.py`
3. `docs/architecture/LIFECYCLE-GATE-PARK-SOURCE-USAGE.md`
4. `trading_system/tree_spec/lifecycle_gate_park_source.py`
5. `tools/check_lifecycle_gate_park_source_parity.py`
6. `tests/tree_spec/test_lifecycle_gate_park_source.py`

Read the plan, contract, source intake, both accepted task statuses and full
review chain. Return separate spec/quality verdicts. Confirm source fidelity of
the unusual matched-trade `to_group` park field; do not recommend a policy
correction that diverges from pinned source. Check all output claims retain
offline/no-delivery/no-fill/no-economic/no-training limits. Verify independent
source proof and real child dependencies; no rerun of controller-reported
suites is needed.
