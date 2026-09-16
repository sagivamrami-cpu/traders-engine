# Pending-plan revalidation source implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans or superpowers:subagent-driven-development. Track checkbox steps.

**Goal:** Run the original pending-plan revalidation and its actual calculations offline.
**Architecture:** Complete original policy/JSON/calendar logic with captured-input
ports and composed existing source readers. Independent whole-module and
dependency audit. Full tree_walk remains an explicitly unbound producer boundary.
**Tech Stack:** Python/pandas/AST/pytest; in-memory text writers and logical paths.
**Spec:** docs/architecture/REVALIDATION-SOURCE-CONTRACT.md

## Global constraints

- Approved existing feature checkout; main inline criticalpath, independent
  review sidecars, no nestedagents. Preserve unrelated work; apply_patch only.
- chart-desk commit68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9,
  tracker.py b616b34022e436545d8c1daf85eced51614fd74e,
  tradeplan.py d09e9be39ce8dadf1674029e0c03751c70502135.
- No retainedsource execution, live calls, data acquisition, labels/models,
  commits/pushes/deployment/cleanup. Offline private ports are not causalfeeds.
- Keep actual source thresholds, fail-open states, labels and shadow-versus-veto
  distinction. No new trading strategy and no fullmaster scope reduction.
- Calendar naive timestamps inherit raw source host semantics; do not certify
  them for historical replay or introduce an unapproved timezone.
- Existing EMA/deep component must have final acceptance before this component
  is accepted; disjoint source/spec/tests work may proceed during its finalreview.

## Task2: Complete projection and dependency audit

Create trading_system/tree_spec/revalidation_source.py,
tools/check_revalidation_source_parity.py and
tests/tree_spec/test_revalidation_source.py.
Consumes current runtime, literal source pins and actual inheritedauditors.
Produces audit_revalidation_source(parentroot) and required --source-root CLI.

- [ ] Write missingauditorRED tests:
  ```python
  r=api().audit_revalidation_source(SOURCE)
  assert r['source_subset_verified'] and r['blockers']==[]
  assert not r['ready_for_replay'] and not r['ready_for_training']
  ```
  Mutate wholeimports/constants/order/constructor/calls, bias/sendgates,
  threshold equality, age normalization/emptyskip/catch/oldestselection,
 15shadowcalls, calendarwindow/date/impact/order, treeprecedence, pendingclock,
  signature and verified flags. Missing source/candidate, wrongroot/HEAD/baseline,
  blobdrift, duplicate/missingselectednodes and substitutioncount drift block.
  Mutate each actual consumed dependency, never replace auditorwithfaketrue.
- [ ] Run RED then implement full ordered projection, literalpinnedidentity,
  exact1 substitutions and15shadow count. Inherit actual audit functions:
  audit_tracker_admission_source, audit_stretch_source, audit_ema_windows_source,
  audit_admission_source, audit_watch_io_source, audit_lifecycle_primitives_source;
  tools.check_reversal_source_parity.check_source_parity(parent/'chart-desk')
  for real defaultPVSRA closure. Preserve every dependency blocker/error.
  CLI emits JSON/VERIFIED0/BLOCKED2 with readinessfalse. No runtime/source imports.
- [ ] Test CLI unrelatedcwd and missingroot; freshprocess importguard forbids
  chartdesk/floor/tree_replay. Current component runtime/audit and directly
  consumed dependency tests run once on unchanged code, terminalresult recorded.
  Candidate-only mutation probes must catch a wrong veto and a news-window bug.
- [ ] Package3files; independent task and wholecomponent final reviews, inspect
  actual diffs/results and rerun applicable changed checks before acceptance.
- [ ] Update status/master/AGENTS/tracker, record unresolved tree_walk/provider
  boundary and exact next originalcaller/lifecycle work, no fullreplay/modelclaim.

## Full-goal continuation

Actual full tree.walk and all producers, causal lifecyclefeed ownership and
operationtime evidence, resolver/gate/park/receipt/outbox/caller, simulator,
data coverage and manifests, correctdataset, models and untouched evaluation
remain binding. Human gates remain before productiondata/promotion/liveactions.

