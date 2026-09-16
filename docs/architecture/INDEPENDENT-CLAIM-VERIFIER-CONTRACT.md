# Original independent price-claim verifier

Continuation of approved master C/D/E source-faithful lifecycle reconstruction.
Not an alternative execution policy or claim of historical certification. Read
MARKET-WATCH-ADMISSION-SOURCE-INTAKE.md complete-verifier section first.

## Authority and design

chart-desk commit68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9;
chartdesk/verify.py blob3329fdb71f8aebdf13a6fa823e8be0d85e1ced03.
Use all source constants/classes/functions, retaining decoder and message router.
Do not import or execute retained source. Private vendor is an inertly extracted
projection; runtime network transport is replaced by explicit local input ports.

Three possible approaches: reuse resolver helpers (rejected: erases independent
fill slack and extrema semantics); a fresh verification algorithm (rejected:
changes approved baseline); exact original verifier over offline ports (chosen).
Only the last advances approved fidelity. No source rule is repaired silently.

Private `_vendor.claim_verifier` module keeps TOL, Verdict, _tol, _covers,
_fill_index, _NOT_YET, _closed_past, _fill_unseen, _frame, _extreme in original
relative order. Imports: future annotations, re, dataclass, pandas as pd and
DeskSuccess from .desk_success. _fill_index redirects tradeplan.entry_zone to
pricing.entry_zone only. No lifecycle_bars import or shared fill helper.

`ClaimVerifier(source)` owns source and `movement = DeskSuccess(source)`.
Methods in original relative order: _bars, _binance_bars, target, _claim_clock,
fill, stop, check_message. Calls to these original functions become self calls;
pure functions stay module-level. No other method/body changes except below.

Ports (caller supplied, no defaults):

- now_utc() -> aware UTC datetime, same operation clock as now_epoch().
- now_epoch() -> float, used by the real DeskSuccess proof dependency.
- fetch_corrected(symbol, timeframe, days) -> (DataFrame or None, correction).
  This is a verifier-specific read, not a reuse of the resolver's frame. Preserve
  request symbol,15m,days (default3) and original unverified-only veto.
- fetch_json(url, *, timeout) -> decoded JSON value supplied offline. The URL
  is a request identity only; port MUST NOT perform network access. Preserve
  exact original Binance URL, start-time calculation,15m,limit1000 and timeout15.
  Errors can be raised to exercise original catch-toNone/fallback behavior.

In _binance_bars remove local json/urllib imports; replace exactly
`_json.load(_rq.urlopen(url, timeout=15))` with
`self.source.fetch_json(url, timeout=15)`. Preserve the entire try/except, URL,
row parser, OHLC columns and empty handling. Every pd.Timestamp.now(tz="UTC")
becomes pd.Timestamp(self.source.now_utc()); no epoch/datetime roundtrip.
_bars basis.fetch_corrected becomes self.source.fetch_corrected.
In check_message remove local reached import and redirect reached(trade) to
self.movement.reached(trade); no reimplementation of minimum proof validation.

## Fidelity and causal limits

The independent verifier includes the fill bar in target extrema; resolver
movement excludes it. _fill_index uses one-bar slack derived from the first two
index stamps, fallback900. Neither raw behavior proves an economic fill. The
separate algorithms must not be normalized to make them agree.

Venue-first is used for BINANCE. Any nonNone venue result wins, even empty;
only None falls back to corrected local bars. The decoder retains failure
boundaries and request contents. No correction flag or freshness gate is added.

Targets use claim_ts else now; stops prefer resolved_ts, then claim_ts, then
now. _frame includes opening stamps<=claim clock; containing-bar final OHLC
still requires explicit historical provider evidence. Unknown/missing coverage
is not established by _covers, whose None/empty/error behavior remains original.
fill's45min grace and _closed_past's stricter boundary remain distinct.

Verdict carries ok,reason,claim,stale and source __bool__. check_message dispatches
actual identity-first messages: minimum proof, target regex, fill, stop, otherwise
nofactualclaim. Exceptions become failed Verdict. It sends nothing, changes no
trade state and performs no park/outbox/receipt effects.

Raw source ports are not a public causal provider or a historical input schema.
No default feed, instrument alias, price substitute or success probability is
introduced. Target/stop source tolerance remains XAU0.5,NAS3,BTC15,fallback1.

## Verification and acceptance

Normal missingmoduleRED precedes runtime and auditor. Real pandas frames,
ReplayClock and supplied exact JSON responses exercise actual routing, decoder,
venue/local fallback, independent fill slack, claimclock/stopclock, tolerance,
stale versus contradiction, exception paths and real minimum proof. Inputs and
trade unchanged, no forbidden live calls. Test firstbar target acceptance as
source characterization, not endorsement of intrabar economic execution.

Independent audit uses literal commit/blob, exact selected order/signatures,
per-function substitutions with counts and wholemodule comparison. It invokes
lifecycle_primitives_source audit to cover real DeskSuccess/pricing closure.
Mutation tests reject clocks, extra imports, tolerance, routing, time comparisons,
decoder/request/fallback changes and dependency drift. CLI explicit retainedroot,
JSON VERIFIED0/BLOCKED2, always false replay/training readiness.

Task and combined independent reviews precede component acceptance. Afterwards
still required: causal verifier/lifecycle providers and availability traces,
still_valid/tree/shadow, gate/park/receipt/outbox/shelf/outcome effects, full
stateful resolver/caller and other producers; economic simulator/data/models.
