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

## Task1: Original policy and real dependency composition

Create trading_system/tree_replay/_vendor/revalidation.py,
tests/tree_replay/test_revalidation.py and
docs/architecture/REVALIDATION-SOURCE-USAGE.md.
Consumes exact source/ports in spec and actual source readers. Produces
Revalidation(source).still_valid(t), .revalidate_pending(t,*,now=None),
._tree_agrees(symbol,direction), ._shadow(symbol,name,fired,detail),
calendar_event_ts(ev), calendar_high_impact_in_window(events,now_ts,window_s),
_bias_against(nets,short), with original return values.

- [x] Write missingmoduleRED tests, starting with literal calendar/bias cases:
  ```python
  def api():
      name='trading_system.tree_replay._vendor.revalidation'
      assert importlib.util.find_spec(name) is not None, 'revalidation missing'
      return importlib.import_module(name)
  assert api().calendar_event_ts({'dateline': True, 'date': '2026-01-01T00:00:00Z'}) == 1767225600.
  assert api().calendar_event_ts({'dateline': -3}) == -3.
  assert api()._bias_against({'4h':43.,'1h':-2.},True) is False
  assert api()._bias_against({'4h':25.,'1h':0.},True) is True
  ```
  Numeric precedence,0/bool/string fallthrough, ISO offsets/invalid/missing,
  first-input event identity, inclusive window, outside-window missingimpact,
  inside missingimpact raises, leading space impact not normalized, highprefix,
  negativewindow/raw NaN semantics. No filesystem/calendarAPI for fixturedata.
- [x] Add real composition fixtures: frames with volume, OHLC and UTC index;
  read_symbol builds actual admission_matrix.read_frame views for bothTFs;
  fetch_corrected returns per(symbol,TF,lookback) frames/correction and records
  order; daily rows drive real StretchReader/ranges; real EmaReader/PVSRA/structure.
  Controlled tree_walk responses remain boundary-only, never fulltree evidence.
  In-memory writer captures actual JSON lines/close; explicit clocks and faults.
  Test clean long and short, real flippedbias versus alreadyagainst/unread/flat
  send, netthreshold25 and conflictingTF, missinghigher, missingstretch and core
  error. Actual same-side extension veto, opposite-side extension allowed.
  Veto skips later requests/shadows. Missing direction outside try raises.
- [x] Add age boundaries0/20/justover20/120/justover120 in15mequivalents,
  4h90min normal, oldestframe governs, emptyskip, allmissing, exception resets,
  correctionsignored, futurelast rawnegative. Verify perTF timestamp calls.
  Fired EMA/session/zero-risk/structure/vector/news shadows do not veto. Real
  red/green PVSRA last12 with outside13th excluded; JSONmissing/invalid and
  missingimpact shadowunavailable; all six shadow families emitted in order.
  Shadow ensure/open/time/write/close exceptions are caught without extra veto.
- [x] Add pending age7199/7200seconds, missing/invalidts, futurets clamped0,
  explicitnow no extraepochclock except shadows, no tree on initialveto,
  opposingdirection precedence overstopped, None/error/stopped/walkcleancases.
  Compare unchanged source reasons and verified flags. Use behavioral assertions
  and literal numeric oracles, not tests of mocks or generated expectedvalues.
- [x] Run normalRED:
  `python -B -m pytest tests/tree_replay/test_revalidation.py -q --tb=short -p no:cacheprovider`.
- [x] Inertly extract exact source nodes/constants. Copy calendar/purebias;
  compose actual source readers, apply exactly the spec substitutions. Use
  tracker_admission_source._selected/_replace_exact and admission_source's
  counted AST replacement for15_shadow name loads. No original import/execution.
  ```python
  class Revalidation:
      def __init__(self, source):
          self.source = source
          self.admission = TrackerAdmission(source)
          self.stretch = StretchReader(source)
          self.ema = EmaReader(source)
  ```
- [x] Run GREEN focused and existing dependencies:
  `python -B -m pytest tests/tree_replay/test_revalidation.py tests/tree_replay/test_ema_windows.py tests/tree_replay/test_stretch.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_admission_calculations.py -q --tb=short -p no:cacheprovider`.
  Record exact terminal results, no blanket coverage claim.
- [x] Document all rawports, requestidentities, source catches and clockreads,
  actual scope/unknownstates; package3files and independent spec/quality review.

## Task2: Complete projection and dependency audit

Create trading_system/tree_spec/revalidation_source.py,
tools/check_revalidation_source_parity.py and
tests/tree_spec/test_revalidation_source.py.
Consumes current runtime, literal source pins and actual inheritedauditors.
Produces audit_revalidation_source(parentroot) and required --source-root CLI.

- [x] Write missingauditorRED tests:
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
- [x] Run RED then implement full ordered projection, literalpinnedidentity,
  exact1 substitutions and15shadow count. Inherit actual audit functions:
  audit_tracker_admission_source, audit_stretch_source, audit_ema_windows_source,
  audit_admission_source, audit_watch_io_source, audit_lifecycle_primitives_source;
  tools.check_reversal_source_parity.check_source_parity(parent/'chart-desk')
  for real defaultPVSRA closure. Preserve every dependency blocker/error.
  CLI emits JSON/VERIFIED0/BLOCKED2 with readinessfalse. No runtime/source imports.
- [x] Test CLI unrelatedcwd and missingroot; freshprocess importguard forbids
  chartdesk/floor/tree_replay. Current component runtime/audit and directly
  consumed dependency tests run once on unchanged code, terminalresult recorded.
  Candidate-only mutation probes must catch a wrong veto and a news-window bug.
- [x] Package3files; independent task and wholecomponent final reviews, inspect
  actual diffs/results and rerun applicable changed checks before acceptance.
- [x] Update status/master/AGENTS/tracker, record unresolved tree_walk/provider
  boundary and exact next originalcaller/lifecycle work, no fullreplay/modelclaim.

## Full-goal continuation

Actual full tree.walk and all producers, causal lifecyclefeed ownership and
operationtime evidence, resolver/gate/park/receipt/outbox/caller, simulator,
data coverage and manifests, correctdataset, models and untouched evaluation
remain binding. Human gates remain before productiondata/promotion/liveactions.
