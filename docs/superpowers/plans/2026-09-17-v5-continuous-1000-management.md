# V5 Continuous $1,000 Management Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a causal continuous-account replay of V4 management on a $1,000 account, preserving 0.05-lot legs, repeated additions, TP3/runner accounting and four preregistered management variants.

**Architecture:** Create a new ignored private experiment directory that consumes only the frozen V4 message/M5 streams and policy, while leaving V4 and its verified snapshot immutable. Split the replay into a deterministic stream merger, a continuous account/risk ledger, an isolated management worker, a matrix runner, independent verification and a Hebrew report. The worker sees observations only through JSONL stdin; the outer runner owns source loading, locks and artifact writes.

**Tech Stack:** Python 3.13 standard library, existing V4 Python research helpers, JSON/CSV, `unittest`, Playwright for report verification.

**Spec:** `docs/superpowers/specs/2026-09-17-v5-continuous-1000-management-design.md`

## Global Constraints

- Never modify `raw-data/account-management-study/gold-v4-minlegs-2026-09-17/` or its verified snapshot.
- New private artifacts live under `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/`; private market/account data remains ignored and must not be committed.
- Execution identity is OANDA:XAUUSD, 100 ounces per lot; no GC price alias, Footprint, DOM, delta or CVD.
- Minimum nonzero leg is 0.05 lot/5 oz; initial basket minimum is 0.15 lot or 0.20 lot when TP3 has a separate leg.
- Primary risk is 10% core / 5% child / 20% portfolio; stress is 20% / 10% / 40%; no daily loss stop.
- Admission reserves $1/oz round-trip costs. Reports show $0, $0.50 and $1/oz without changing the admitted population.
- Primary leverage is 1:200 with 1:100 sensitivity and 20% minimum free-equity buffer.
- Primary ambiguity policy is stop-first; target-first is a labelled sensitivity only.
- Remaining positions at the final cutoff are marked separately from realized P&L.
- No live alert, Telegram, execution, fixed-TP1 control, training or production-readiness change.

---

### Task 1: Freeze sources and build one chronological stream

**Files:**
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/stream.py`
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/test_stream.py`
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/source-lock.json`
- Read only: `raw-data/account-management-study/gold-v4-minlegs-2026-09-17/*/input-stream.jsonl`
- Read only: `raw-data/account-management-study/gold-typed-v2-2026-09-17/policy.json`

**Interfaces:**
- Produces: `build_stream(v4_root: Path) -> tuple[list[dict], dict]`
- Produces: `packet_identity(packet: dict) -> tuple`
- Produces coverage fields `first`, `last`, `packet_count`, `message_count`, `bar_count`, `gaps`, `duplicate_count`.
- Consumers: Tasks 4–6.

- [ ] **Step 1: Write failing stream tests**

```python
class StreamTests(unittest.TestCase):
    def test_identical_daily_overlap_deduplicates(self):
        stream, coverage = build_stream(FIXTURE)
        self.assertEqual([p['time'] for p in stream], sorted(p['time'] for p in stream))
        self.assertEqual(coverage['duplicate_count'], 2)

    def test_conflicting_duplicate_fails(self):
        with self.assertRaisesRegex(ValueError, 'CONFLICTING_DUPLICATE'):
            build_stream(CONFLICT_FIXTURE)

    def test_open_never_contains_future_ohlc(self):
        stream, _ = build_stream(FIXTURE)
        for packet in stream:
            if packet['kind'] == 'OPEN':
                self.assertEqual(set(packet), {'kind', 'time', 'open'})
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/test_stream.py`

Expected: import/file failure because `stream.py` does not exist.

- [ ] **Step 3: Implement deterministic merge and coverage audit**

Use the packet identity:

```python
def packet_identity(packet):
    if packet['kind'] == 'MESSAGE':
        m = packet['message']
        return ('MESSAGE', packet['time'], m.get('alert_id'), m['kind'],
                m.get('published', m.get('plan', {}).get('published')))
    return (packet['kind'], packet['time'])
```

For a duplicate identity, compare canonical `json.dumps(packet,
sort_keys=True, separators=(',', ':'))`; fail on unequal bytes. Preserve stable
source order for same-time packets and assert that every close is exactly five
minutes after its matching open. Record all intervals larger than five minutes.

- [ ] **Step 4: Lock source hashes before any replay output**

`source-lock.json` must contain SHA-256 for every daily input stream, V4 worker,
V4 result, policy, design spec, this plan, the verified V4 manifest, plus the
exact stream coverage. Refuse to overwrite an existing lock.

- [ ] **Step 5: Run Task 1 tests**

Run: `python raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/test_stream.py`

Expected: all tests pass.

- [ ] **Step 6: Record private milestone hash**

Write `task1-verification.json` with test command, exit code, source-lock hash
and stream hash. Do not commit private files.

---

### Task 2: Continuous account, sizing, costs and margin

**Files:**
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/account.py`
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/test_account.py`

**Interfaces:**
- Produces: `RiskRegime(name, core_pct, child_pct, portfolio_pct)`
- Produces: `AccountConfig(initial_cash, unit_ounces, cost_reserve_per_ounce, leverage, free_equity_pct)`
- Produces: `ContinuousAccount.mark(price: float) -> dict`,
  `max_quantity(role: str, entry: float, stop: float, min_units: int,
  idea_id: str) -> SizeDecision`, `open_lot(position: dict) -> dict`,
  `close_lot(position_id: str, price: float, ounces: int, reason: str) -> dict`,
  `move_stop(position_id: str, stop: float, evidence_id: str) -> dict`, and
  `snapshot(mark_price: float) -> dict`.
- `max_quantity` returns integer 5-oz units and a structured rejection reason.
- Consumers: management worker in Task 3 and verifier in Task 5.

- [ ] **Step 1: Write failing account tests**

```python
def test_primary_cap_rejects_minimum_basket():
    a = account(equity=1000, core_pct=.10)
    result = a.max_quantity(entry=4400, stop=4390, role='core', min_units=3)
    self.assertEqual(result.reason, 'MINIMUM_EXCEEDS_CORE_RISK')

def test_minimum_core_quantity_is_three_units():
    a = account(equity=1000, core_pct=.20)
    result = a.max_quantity(entry=4400, stop=4390, role='core', min_units=3)
    self.assertEqual(result.ounces, 15)

def test_cost_reserve_is_inside_admission_risk():
    a = account(equity=1000, core_pct=.20, cost=1)
    self.assertEqual(a.risk(4400, 4390, ounces=15), 165)

def test_realized_gap_loss_can_exceed_admission_cap():
    a = account(equity=1000, core_pct=.10)
    a.force_fixture_position(entry=4400, stop=4395, ounces=15)
    event = a.close_lot(price=4380, ounces=15, reason='GAP_STOP')
    self.assertEqual(event['gross_pnl'], -300)

def test_margin_buffer_rejects_100_to_1_but_allows_200_to_1():
    self.assertFalse(account(leverage=100).margin_allows(4400, 20))
    self.assertTrue(account(leverage=200).margin_allows(4400, 20))
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/test_account.py`

Expected: import/file failure because `account.py` does not exist.

- [ ] **Step 3: Implement exact account equations**

```python
price_risk = abs(entry - stop) * ounces
reserved_cost = config.cost_reserve_per_ounce * ounces
admission_risk = price_risk + reserved_cost
equity = config.initial_cash + realized_gross + unrealized_gross
required_margin = abs(mark_price * total_open_ounces) / config.leverage
free_equity = equity - required_margin
```

The candidate quantity is the largest integer unit count fitting the relevant
core/child cap, remaining portfolio risk and margin buffer, then rejected if it
is below `min_units`. Core allocations must keep each nonzero V4 leg at one or
more units. Profits never replenish cumulative idea losses used by the V4
shared-idea child gate, while current-equity percentage budgets update normally.

- [ ] **Step 4: Implement event-level reconciliation**

Every mutation emits balance, realized gross, cost at all three cost columns,
unrealized, equity, used margin, free equity, total risk to stops and open
ounces. Stops may only move in the protective direction. Emit
`MARGIN_MODEL_BREACH` and block new exposure if margin exceeds equity; do not
invent a liquidation fill.

- [ ] **Step 5: Run Task 2 tests**

Run: `python raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/test_account.py`

Expected: all tests pass.

- [ ] **Step 6: Record private milestone hash**

Write `task2-verification.json` containing account source/test hashes and the
passing command output.

---

### Task 3: C0/P1/R1/U1 management state machine

**Files:**
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/worker.py`
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/test_management.py`
- Read only: `raw-data/account-management-study/snapshots/gold-v4-minlegs-pre-v5-verified-2026-09-17/worker.py`

**Interfaces:**
- Worker JSONL INIT: `variant`, `risk_regime`, `leverage`, `targets_first`,
  `policy`, `account_config`.
- Observation packets: unchanged `MESSAGE`, `OPEN`, `CLOSE` forms.
- Output per packet: `events`, `chain`, `account`.
- Final output: `summary`, `targets`, `runners`, `children`, `account_curve`,
  `rejections`, `coverage_state`, `chain`.
- Consumers: Tasks 4–6.

- [ ] **Step 1: Write failing management tests**

Use the existing test packet helpers (`plan`, `message`, `op`, `cl`) copied into
the new test file and the subprocess `run_case` helper below:

```python
def actions(result, name):
    return [event for event in result['events'] if event['action'] == name]

def test_target_reached_emits_after_early_leg_is_already_zero(self):
    result = run_case(early40_then_tp1_packets(), variant='C0')
    self.assertEqual(len(actions(result, 'EARLY40_PARTIAL')), 1)
    self.assertEqual(actions(result, 'TARGET_REACHED')[0]['target'], 1)
    self.assertFalse(actions(result, 'TP1'))

def test_tp3_never_closes_runner_automatically(self):
    result = run_case(tp3_packets(), variant='C0')
    event = actions(result, 'TARGET_REACHED')[-1]
    self.assertEqual(event['target'], 3)
    self.assertGreater(result['summary'][0]['core_open_quantity'], 0)

def test_c0_and_p1_protection_split(self):
    c0 = run_case(closed40_packets(), variant='C0')
    p1 = run_case(closed40_packets(), variant='P1')
    self.assertTrue(actions(c0, 'CLOSED40_BE'))
    self.assertFalse(actions(p1, 'CLOSED40_BE'))
    self.assertEqual(p1['summary'][0]['stop'], 90)

def test_r1_recovery_contract(self):
    accepted = run_case(protected_exit_then_retest_packets(), variant='R1')
    loss = run_case(original_loss_then_retest_packets(), variant='R1')
    expired = run_case(expired_protected_exit_packets(), variant='R1')
    self.assertEqual(len(actions(accepted, 'RECOVERY_ENTRY')), 1)
    self.assertFalse(actions(loss, 'RECOVERY_ENTRY'))
    self.assertFalse(actions(expired, 'RECOVERY_ENTRY'))

def test_u1_requires_fresh_structure_for_repeated_child(self):
    stale = run_case(child_stop_then_retest_without_structure(), variant='U1')
    fresh = run_case(child_stop_then_new_structure_and_retest(), variant='U1')
    self.assertEqual(len(actions(stale, 'CHILD_ENTRY')), 1)
    self.assertEqual(len(actions(fresh, 'CHILD_ENTRY')), 2)
    second = actions(fresh, 'CHILD_ENTRY')[1]
    self.assertGreater(second['structure_confirmation_time'],
                       actions(fresh, 'CHILD_EXIT')[0]['time'])

def test_single_child_unit_holds_at_one_r(self):
    result = run_case(single_unit_child_reaches_one_r(), variant='U1')
    self.assertTrue(actions(result, 'CHILD_ONE_R_HOLD'))
    self.assertFalse(actions(result, 'CHILD_PARTIAL'))
    self.assertEqual(result['summary'][0]['child_open_quantity'], 5)

def test_safety_and_direction_contracts(self):
    result = run_case(short_with_child_stop_packets(), variant='U1')
    self.assertGreater(result['summary'][0]['core_open_quantity'], 0)
    self.assertFalse(actions(result, 'STOP_WIDENED'))
    self.assertTrue(all(e['price'] < 100 for e in actions(result, 'CHILD_ENTRY')))

def test_ambiguity_and_runner_closed_bar_mfe(self):
    result = run_case(same_bar_stop_tp3_then_future_spike(),
                      variant='C0', targets_first=False)
    self.assertTrue(actions(result, 'AMBIGUITY'))
    self.assertFalse(actions(result, 'TP3_PARTIAL'))
    self.assertLess(result['runners'][0]['best_time'],
                    future_spike_close_time())
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/test_management.py`

Expected: worker variants and target-state assertions fail.

- [ ] **Step 3: Port V4 control without importing mutable V4 state**

Copy the accepted V4 state-transition logic into the new isolated worker while
binding all quantity/risk/margin operations to `ContinuousAccount`. Preserve
V4 route mapping, group identity, pending invalidation, original entry/targets,
early partial, core structural trailing and retest child control.

- [ ] **Step 4: Implement target state independent of inventory**

```python
if touch(target) and not state['target_reached'][index]:
    state['target_reached'][index] = self.clock
    self.emit(state, 'TARGET_REACHED', target=index + 1,
              target_price=target, ambiguity=stop_hit)
    if leg_quantity(state, index):
        self.close_target_leg(state, index, target)
```

Start runner MFE/giveback tracking only after the TP3 event and update it after
each newly closed bar. Store best price/time/value, exit/mark value and giveback.

- [ ] **Step 5: Implement P1 and R1**

P1 disables only `CLOSED40_BE`, retains the 0.05 early partial, and protects at
TP1 or a fully confirmed 2-left/2-right profile pivot. R1 keeps C0 protection,
allows one recovery only after BE/profitable structural exit, and requires the
new post-exit directional zone-retest candle specified in the design.

- [ ] **Step 6: Implement U1 child confirmation lineage**

Persist `structure_confirmation_time`. Every U1 child records the confirmation
and retest event IDs. Following a child stop, require
`structure_confirmation_time > child_exit_time`. Keep one active child per
idea and repeat cycles after fresh evidence.

- [ ] **Step 7: Run Task 3 tests**

Run: `python raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/test_management.py`

Expected: all management tests pass.

- [ ] **Step 8: Verify worker isolation**

Run probes that call `open()` and `socket.socket()` after worker initialization;
expect `WORKER_IO_DENIED`. Record worker/test hashes in
`task3-verification.json`.

---

### Task 4: Locked replay matrix and continuous results

**Files:**
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/run.py`
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/experiment.py`
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/experiment-lock.json`
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/results/*.json`

**Interfaces:**
- Produces `run(stream, variant, regime, leverage, targets_first) -> dict`.
- Produces `matrix-summary.json`, `continuous-event-ledger.jsonl`,
  `trade-summary.json`, `target-funnel.json`, `runner-summary.json`,
  `addition-summary.json`, `equity-curves.json`.
- Consumers: verifier and report.

- [ ] **Step 1: Write failing runner smoke test**

```python
def test_runner_passes_init_and_observations_by_stdin():
    result = run(FIXTURE, 'C0', 'primary', 200, False)
    self.assertEqual(result['initial_equity'], 1000)
    self.assertEqual(result['variant'], 'C0')
```

- [ ] **Step 2: Run smoke test and verify RED**

Run: `python -m unittest raw-data.account-management-study.gold-v5-continuous-1000-2026-09-17.test_runner`

Expected: runner module/test import failure. If hyphenated private paths prevent
module import, execute the test file directly and retain subprocess isolation.

- [ ] **Step 3: Implement runner and lock**

The locked main matrix is:

```python
variants = ['C0', 'P1', 'R1', 'U1']
regimes = ['primary', 'stress']
leverages = [200, 100]
main_order = 'stop_first'
```

Run target-first only for rows containing an ambiguity; do not duplicate every
unaffected row. Before results, write `experiment-lock.json` with all source,
worker, config and stream hashes plus the full matrix. Refuse overwrite.

- [ ] **Step 4: Run the complete continuous matrix**

Run: `python raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/experiment.py`

Expected: one deterministic terminal result for every locked row. Do not select
or tune a variant from partial output.

- [ ] **Step 5: Export normalized ledgers**

Each event record includes variant/regime/leverage, source packet index/time,
idea/alert/attempt/leg identity, action/reason, price/quantity/stop, target state,
gross and all cost P&L columns, account snapshot and causal evidence IDs.

- [ ] **Step 6: Record private milestone hash**

Write `task4-verification.json` with matrix row count, result hashes and process
exit status.

---

### Task 5: Independent accounting and causal verification

**Files:**
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/verify.py`
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/test_replay_guards.py`
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/verification.json`

**Interfaces:**
- Consumes all Task 4 ledgers and locks.
- Produces one PASS/FAIL record per matrix row plus global source/causality
  assertions.

- [ ] **Step 1: Write independent ledger reconstruction**

Reconstruct every core/child leg from ENTRY/EXIT/PARTIAL/STOP events without
calling worker methods. After each event assert inventory, weighted entries,
realized/floating gross P&L, all cost columns, current stops, margin and account
equity against the worker snapshot.

- [ ] **Step 2: Add minimum and risk assertions**

Assert every quantity is divisible by 5 oz; every initial basket has at least
15/20 oz as appropriate; child remainder is either zero or at least 5 oz; every
admitted entry fits its current-equity cap, $1/oz reserve, portfolio cap and
margin buffer. Gap loss may exceed the admission estimate and must be labelled.

- [ ] **Step 3: Add target/runner assertions**

Assert target times are monotonic; TP3 never zeroes runner merely because TP3
was touched; runner best time is not before TP3 or after exit/cutoff; giveback
equals best closed-bar value minus exit/mark value; channel milestones do not
appear in worker INIT or observation packets.

- [ ] **Step 4: Add prefix and changed-future tests**

For every variant/regime, select cut points before first entry, first target,
first recovery and first child. Rerun the prefix and assert exact earlier events.
Then mutate all later OHLC/message prices by +50,000 and assert the same prefix.

- [ ] **Step 5: Add compatibility and snapshot immutability checks**

Hash all 68 V4 source files and compare with the preserved manifest. Run C0 in
a dedicated compatibility fixture with V4's old fixed budgets/step and assert
event action/time/alert identity matches the frozen V4 control. Differences
caused solely by new target-state events must be filtered explicitly by action,
never by deleting unexplained rows.

- [ ] **Step 6: Run all verification**

Run:

```powershell
python raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/test_stream.py
python raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/test_account.py
python raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/test_management.py
python raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/test_replay_guards.py
python raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/verify.py
```

Expected: all tests pass and `verification.json` reports PASS for every locked
row, V4 immutability, accounting, risk, target/runner, prefix/future mutation,
hash chain and worker I/O denial.

- [ ] **Step 7: Record reviewed verification hashes**

Hash test sources, worker, locks, results and verification output after the
final passing run. Any later edit invalidates the verification and requires a
fresh run.

---

### Task 6: Hebrew decision tree, full trade journal and conclusions

**Files:**
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/report.py`
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/check_report.py`
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/V5-CONTINUOUS-1000-HE.html`
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/report-verification.json`
- Create: `docs/architecture/MANAGEMENT-V5-CONTINUOUS-1000-2026-09-17.md`
- Modify: `PROJECT_STATE.md`

**Interfaces:**
- Consumes only verified Task 4/5 artifacts.
- Produces visual tree, matrix comparison, continuous equity/drawdown timeline,
  full trade/target/runner/addition journal and CSV/JSON links.

- [ ] **Step 1: Generate report from verified artifacts**

The main headline must show C0/P1/R1/U1 under primary 10/5/20, 1:200,
stop-first and $1/oz. Present stress, gross, 1:100 and target-first only in
labelled sensitivity tables. Separate cash/realized, floating mark and final
liquidation sensitivity.

- [ ] **Step 2: Render the management tree**

Show admission, initial legs, +40 partial, C0/P1 protection split, R1 recovery,
TP1/TP2/TP3 target-state, post-TP3 runner, U1 addition/reconfirmation and every
risk/margin rejection branch. The tree must state that no result uses future
bar information.

- [ ] **Step 3: Include complete audit views**

Provide filters for variant, regime, date, alert, TP level, recovery, addition
and rejection. Each trade expands to ordered events with quantities in lots and
ounces, stops, risk %, margin, gross/cost P&L, runner MFE/giveback and evidence
IDs. Include all alerts, including no-entry records.

- [ ] **Step 4: Browser verification**

`check_report.py` must open the report in Chromium desktop and 390px mobile,
exercise filters/expanders, check every internal link, confirm all matrix rows
and trade counts match JSON, assert no horizontal document overflow, UTF-8
replacement characters or page errors, and save screenshots.

- [ ] **Step 5: Write architecture result note**

Document exact final results, whether delayed protection/recovery/add filters
improved or worsened each control, TP3 reconciliation, $1,000 feasibility,
drawdown/margin/cost limitations, in-sample status and next untouched-window
requirements. Do not recommend a live policy merely because it wins this window.

- [ ] **Step 6: Update project state and verify tracked docs**

Run:

```powershell
python raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/report.py
python raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/check_report.py
git diff --check -- PROJECT_STATE.md docs/architecture/MANAGEMENT-V5-CONTINUOUS-1000-2026-09-17.md
```

Expected: report verification PASS, no malformed UTF-8, no broken links and no
tracked-document whitespace errors.

- [ ] **Step 7: Commit only publishable documentation**

```powershell
git add PROJECT_STATE.md docs/architecture/MANAGEMENT-V5-CONTINUOUS-1000-2026-09-17.md
git commit -m "docs: record V5 continuous account replay"
```

Private scripts, source streams, account data, results and screenshots remain
under ignored `raw-data/` and must not be forced into Git.

---

### Task 7: Final cross-review and handoff

**Files:**
- Read all files created by Tasks 1–6.
- Create: `raw-data/account-management-study/gold-v5-continuous-1000-2026-09-17/final-review.json`

**Interfaces:**
- Produces final independent review disposition and exact rerun commands.

- [ ] **Step 1: Independent spec-conformance review**

Check every design requirement against a concrete test, result field and report
section. Reject completion for missing continuous carry, hidden day reset,
under-minimum legs, unlabelled stress results, TP3 inventory coupling, channel
outcome leakage or unverified V4 snapshot changes.

- [ ] **Step 2: Independent numerical review**

Recalculate one winning, one losing, one recovered, one TP3-runner and one
multi-child idea directly from the event ledger and source M5 packets. Confirm
gross/cost P&L, equity, risk, margin, target state and timestamps.

- [ ] **Step 3: Run final clean verification**

Run all Task 5 and Task 6 commands again without modifying inputs. Record exact
commands, Python/Playwright versions, wall time, exit codes and hashes in
`final-review.json`.

- [ ] **Step 4: Handoff**

Report the verified primary and sensitivity outcomes, link the HTML report,
state whether any variant merits an untouched-window test, and list remaining
feed/cost/margin limitations. Preserve V4 and V5 locks for reproducibility.
