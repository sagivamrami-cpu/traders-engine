# Original complete tree walk and trade construction over raw ports

Architectural continuation of approved master C/D, not a strategy revision.
Authority: chart-desk commit 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9,
chartdesk/tree.py blob fdb439a39bbd35230e421c0319c6be0e2fbfbc1d.
Main read all 1496 original lines and the actual accepted dependency interfaces.
Read-only source findings: FULL-TREE-WALK-SOURCE-INTAKE.md.

## Scope and approach

Implement the entire original walk, First Vector detector, two geometry
consumers, and all their actual dependencies. Neither a provider-final Walk
nor a provider-final map/pattern/matrix/Plan is an implementation of the tree.
Existing public fixed-T adapters, admission wrappers and live alerts stay intact.
The original house/strict variants, missing-vs-negative facts, source thresholds,
mixed forming/completed rows and separate operation clocks remain unchanged.

Options considered: run original live modules (uncontrolled IO and global
state); rewrite rules as a new tree (changes the approved baseline); inertly
project original complete bodies and bind existing real local readers. Choose
the third, the already approved source-faithful architecture. No new human
strategy choice; original source quirks are visible, not silently repaired.

## Files and interfaces

1. `_vendor/tree_core.py`: every original tree non-import top-level node except
   the six reader functions listed below, preserving relative source order,
   including both FINAL_STAGE assignments, all constants, LevelsUnavailable,
   complete Walk dataclass/methods, and all pure helpers. Retain original
   future/dataclass/pandas imports, not the live module bundle. Change only
   `_news_stop`'s .tradeplan import to .revalidation (actual shared calendar
   parsers), and `_levels_ahead`'s .tradeplan import to .pricing.
2. `_vendor/tree_signals.py`: import-only actual dependency facade:
   `from .tr import emas, ema_cloud`, `from .pvsra import pvsra`,
   `from .tree_tr import vector_zones, daily_pivots`. No new numerical code.
3. `_vendor/tree_walk.py`: `TreeReader(source)` and original six functions as
   methods, source signatures/annotations/defaults unchanged except self:
   `_variant_levels`, `_trend_ladder`, `walk`, `first_vector_above_50`,
   `levels_to_trade`, `trade_from_walk`. Preserve full bodies, catches,
   docstring literal values, data calculations and return types.

Constructor stores raw source and creates actual BasisOperation, LevelmapOperation,
BrinksReader, ChecklistReader, WmReader, LiquidityReader and OptionsWallReader
over the same raw source; StretchReader gets the actual BasisOperation facade.
Construction must not fetch, read artifacts, call clocks or certify inputs.
Local names `basis`, `levelmap`, `brinks`, `checklists`, `wm`, `stretch` bind to
the corresponding instance after method docstrings where consumed. Matrix is
actual admission_matrix; tr is tree_signals; PSY is actual map_sessions.

Raw source contract: fetch_corrected(symbol,timeframe,lookback), now_utc(),
calendar_text(logical_path), list_reports(), read_report(logical_id), and
read_tv_csv(filename). Shape qualification is calculated by BasisOperation,
never supplied as a final bool. Calendar path is exactly
`news-desk/data/ff_calendar.json`; no calendar_exists added to this caller.
Optional-artifact failures keep original catches, not synthetic neutral values.

## Enumerated reader adaptations

- Convert six functions to methods and bound calls to them within those methods
  to self calls: walk's _trend_ladder/_variant_levels/first_vector_above_50;
  levels_to_trade and trade_from_walk's _variant_levels. No other helper rewrite.
- In walk, local optionswall import becomes `optionswall = self.optionswall`;
  liquidity import becomes `_liq = self.liquidity`. Actual reader calls remain.
- Replace .workspace import with PurePosixPath import and only `_repo("news-desk")`
  with `PurePosixPath("news-desk")`. Calendar read becomes
  `self.source.calendar_text(cal.as_posix())`. News clock replaces
  `_dt.now(_tz.utc).timestamp()` with `self.source.now_utc().timestamp()`.
  It stays BEFORE reading raw calendar text, as in the original.
- `sessions.current_session()` becomes actual
  `watch_sessions.current_session_at(decision_time=self.source.now_utc())`.
  There is a separate operation clock here; do not reuse the news clock.
- PSY provisional clock `_pd.Timestamp.now(tz="UTC")` becomes
  `_pd.Timestamp(self.source.now_utc())`, only inside its original available/
  window_end branch. Do not read it unconditionally.
- Both geometry functions' .tradeplan imports become .pricing imports;
  exact original Plan, MIN_RR, stop band and ladder calculations are reused.
- Imports of tree_core names must be explicit and independently audited;
  no wildcard import, executable original import or global monkeypatch.

## Behavior that must remain visible

Walk visits DATA, CONTEXT, LEVELS, SESSION, PATTERN, LOCATION, VECTOR, MTF,
TRAP, MEMORY, TRIGGER, TARGET. `passed` means visited, not all tests positive.
Complete means final stage with no stop reason; it is not a priced/admitted fill.
DATA fetches 15m/10 then 4h/60; stale/unverified checks inspect both corrections.
Frame shortage stops cleanly, source errors retain their original boundaries.
Do not convert all source [-2]/[-3] reads to closed-only [-1] observations.

Trend ladder uses actual 4h/1h/30m/15m/5m combination and selected ToolRead;
neutral/missing and contradictory ranges remain distinct. Options optional;
stretch missing is UNKNOWN, not CONSOLIDATING. Strict map adds all 13 pivots
to a successful base map; either failed universe read invalidates that variant.

News requires future coverage and inclusive +/-15min high-impact blackout;
unreadable/missing impact inside window blocks. Revalidation's +/-30min shadow
is a different consumer. Outside session is not a blanket veto. Patterns,
context, vector/SV, near-level and directional commitment may be absent or
negative without becoming invented hard gates. Preserve source MTF six-hour
vector density, not an invented full 4h->1h->15m decomposition.

TRAP judges completed evidence close, but stamps decision from the forming
last row on every path. Correct inversion follows vector side and edge;
SV needs unusual volume AND body/wick geometry. Real EQH/EQL pools and vector
zone memory stay different features; vector midpoints/touches reach the Walk.
No direction stops after MEMORY. TARGET requires distinct levels ahead.

Builder re-fetches 15m, recalculates current ATR and checks drift strictly
greater than .33ATR before re-building the map. It uses original nearest
invalidation, .35ATR cushion, intraday band, distinct targets/obstacles and
refusal. Within5ATR vector midpoints augment geometry. Preserve actual
source Plan, warnings/not_drawn/reasons, original refusal object w.refused,
trap-to-reversal kind, and stop-beyond-anchor postcondition in BOTH consumers.

## Proof and acceptance

Task1 tests use literal OHLCV and actual dependencies, not final-output mocks.
Require real full-walk examples, successful and refused builders, structured
source facts, original operation ordering, missing/error paths and strict/house.
Pure helper tests isolate threshold equality and wrong-direction risks. Exact
fixture values derive from source rules/hand arithmetic, not golden outputs
learned by running the implementation. Existing dependency suites stay green.

Task2 `audit_tree_walk_source(parentroot)` pins original commit/blob, full
ordered original inventory (including repeated assignments), imports, six
signatures, literal constructors/bindings and exact scoped substitution counts.
Compare complete core/signals/reader ASTs; retained originals are never executed.
Invoke actual operation-map, pattern, options, memory, stretch, admission,
revalidation/calendar/watch-session and EMA/cloud audits with their correct
root levels. Dependency failure/error/nonverified always blocks. Explicit-root
CLI JSON0/2, import guard, runtime/source/constructor/dependency mutations and
real behavior mutations required. Task/final independent reviews before use.

Raw-port composition is not causal publication/feed coverage, whole market-watch
arbitration/lifecycle, execution, economic data or training. After acceptance,
bind actual TreeReader into existing Revalidation.tree_walk port and continue
complete causal providers/caller/remaining producers and master E-I. No live,
data acquisition/retention, model promotion, broker or capital authority implied.
