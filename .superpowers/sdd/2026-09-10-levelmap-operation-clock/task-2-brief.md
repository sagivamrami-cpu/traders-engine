# Task2 review requirements

## Global constraints


- Existingapprovedfeaturecheckout, maininlinecriticalpath, independentreview
  sidecars. No nestedagents/commits/cleanup/unrelatedchanges.
- chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9; levelmap.py
  01fc9fe098aa7a5991ce62c3a83e870e4f0d5a2e, basis.pyf3396f3a9fefd71f0f71422001a5521af0a05cd2.
- Source read/parseonly; no live/data/labels/models. No newthresholds or final
  level/broker-verdict providers. Existingfixed-Tlevelmappublic APIs unchanged.
- Raw fetch_corrected(symbol,timeframe,lookback) and now_utc() only. Actual
  basispredicate and accepted ranges/EMA/sessions/quarters/backdays required.


## Task2: Whole operationgraph source proof

Create trading_system/tree_spec/levelmap_operation_source.py,
tools/check_levelmap_operation_source_parity.py,
tests/tree_spec/test_levelmap_operation_source.py.
Interface audit_levelmap_operation_source(parentroot) -> report.

- [ ] Missing-auditorRED and literalverified/no-readiness fixture:
  ```python
  r=api().audit_levelmap_operation_source(SOURCE)
  assert r['source_subset_verified'] and r['blockers']==[]
  assert not r['ready_for_replay'] and not r['ready_for_training']
  ```
  Mutate bothruntimes/earlyclock/sessionboundaries/helperbinding/brokershape/
  constructor/forwarders/imports/signature; sourceidentity/blob/order/duplicate/
  count/missing/syntax and actual reuseddependencies mustblock. Dependency
  falseempty/error/trueblocked propagation, CLI unrelatedcwd/importguard.
- [ ] RED `python -B -m pytest tests/tree_spec/test_levelmap_operation_source.py -q --tb=short -p no:cacheprovider`.
  Then independentliteralpins/imports/signatures/constructors/forwarders,
  sourceorderedselection andexactsubstitutions, fullorderedcandidatecomparison.
  Actual tools.check_levelmap_source_parity.check_source_parity(parent/'chart-desk')
  mandatory with allblockers preserved. Required --source-root CLI JSON0/2.
- [ ] GREEN `python -B -m pytest tests/tree_replay/test_levelmap_operation.py tests/tree_spec/test_levelmap_operation_source.py tests/tree_replay/test_levelmap.py tests/tree_replay/test_levelmap_source.py tests/tree_replay/test_correction_source.py -q --tb=short -p no:cacheprovider`;
  standaloneCLIexplicitparent. Candidate-only clockordering/brokerpredicate
  mutations mustfailruntimefixtures; recordterminalresults/hashes.
- [ ] Package3files, task/finalreviews, resolvefindings and acceptance record;
  updateusage/AGENTS/master/tracker. Keep allremainingmasterwork explicitlyopen.


Spec: docs/architecture/LEVELMAP-OPERATION-CLOCK-CONTRACT.md
