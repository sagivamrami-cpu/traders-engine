# Task2 brief

## Global constraints

- Approved featurecheckout; main inline criticalpath, independent review
  sidecars. No nestedagents/commits/cleanup/unrelatedchanges.
- chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9;
  optionswall.pyc7d27ca396c162f6997b2a72bbd035ed6477e05b. Source read/parse only.
- Original numerical/exception/order semantics, no newthresholds/defaultIO/
  livefeeds/GCspotmapping. No labels/dataacquisition/model/liveapproval.
- Source ports list_reports(), read_report(id), read_tv_csv(filename), now_utc();
  raw text/operationclock only. Actual json/pandas and source helpers required.


## Task2: Independent full source auditor

Create trading_system/tree_spec/optionswall_source.py,
tools/check_optionswall_source_parity.py,
tests/tree_spec/test_optionswall_source.py.
Interface audit_optionswall_source(parentroot) -> verificationreport.

- [ ] Write normalmissingauditorRED and actualpinnedfixture:
  ```python
  r=api().audit_optionswall_source(SOURCE)
  assert r['source_subset_verified'] and r['blockers']==[]
  assert not r['ready_for_replay'] and not r['ready_for_training']
  ```
  Candidateclock/age/anchor/sourcefilter/ratio/expiry/firstwall/catches/import/
  signature/constructor drift; sourceblob/HEAD/root/baseline/orderedinventory/
  pathglobals/substitutioncounts/duplicates/missing/syntax allblock.
- [ ] `python -B -m pytest tests/tree_spec/test_optionswall_source.py -q --tb=short -p no:cacheprovider` RED.
  Then independentliteralconstants/import/signature inventories, exact2global
  originalAST checks, completeorderedmodulecomparison and literalpin/root/
  baseline/blob gates. Preserve recognizedinputerrors as blockers.
  CLI required--source-root JSON0/2/unrelatedcwd/importguard; readinessfalse.
- [ ] GREEN `python -B -m pytest tests/tree_replay/test_optionswall.py tests/tree_spec/test_optionswall_source.py tests/tree_replay/test_pattern_readers.py -q --tb=short -p no:cacheprovider`;
  CLIexplicit retainedparent. Candidate-only ratio/currentprice or staleage
  mutation must be caught by runtimefixtures. Recordterminalresults/hashes.
- [ ] Package3files, independenttask/finalreviews, fixfindings, verify and record
  acceptance/usage/AGENTS/master/tracker. No physicaldataread/live/modelclaim.


