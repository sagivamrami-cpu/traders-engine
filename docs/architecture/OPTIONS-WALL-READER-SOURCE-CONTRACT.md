# Original options positioning reader: offline raw artifacts

Architectural continuation of approved master C/D source-faithful replay.
Source: chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9,
chartdesk/optionswall.py blobc7d27ca396c162f6997b2a72bbd035ed6477e05b.
Main read all211lines. No new strategy, live feed or data purchase. Existing
approved feature checkout, inline implementation with independent reviews;
no commits/cleanup/unrelated edits. Source read/parse only, never execute it.

## Design and boundaries

Use the actual source Walls/OptionsStatus and timestamp/finite/expiry helpers.
OptionsWallReader(source) owns _anchor, status and load with original arguments
plus self; methods retain source order. Constructor only stores self.source.
Pure classes/functions/constants preserve complete source bodies/annotations.
Only physical IO and operation time are supplied; final mapped Walls are not
provider inputs. This follows already approved readers rather than introducing
a second set of trading thresholds or fitting on a replacement signal.

Ports:
- list_reports()->iterable[str]: original report glob results as logical IDs;
  actual status still sorts them and reads only lexically last.
- read_report(report_id)->str: raw UTF-8-decoded report JSON text.
- read_tv_csv(filename)->str: raw CSV text for original TV_FILE_OF filename.
- now_utc()->aware datetime or pd.Timestamp: operation time, not process clock.

Provider must supply only artifacts visible at each read. These private raw
ports are not themselves causal certification or a historical artifact store.
No fallback to physical files, network, local clock or finalproviderverdict.

## Exact projection

Runtime trading_system/tree_replay/_vendor/optionswall.py keeps original
imports except glob, pathlib.Path and .workspace.repo; adds from io import
StringIO. Removes only source REPORTS and TV_DIR physical-path assignments.
All other top-level nonimport nodes retained sourceorder, with _anchor/status/
load moved into OptionsWallReader at end and self added first. Original complete
signatures/decorators and ordered inventory must be verified independently.

Exact one-occurrence replacements in each selected function:
- _anchor: TV_DIR / TV_FILE_OF[symbol] -> TV_FILE_OF[symbol];
  pd.read_csv(path) -> pd.read_csv(StringIO(self.source.read_tv_csv(path))).
- status: glob.glob(REPORTS) -> self.source.list_reports();
  Path(files[-1]).read_text(encoding='utf-8') -> self.source.read_report(files[-1]);
  pd.Timestamp.now(tz='UTC') -> pd.Timestamp(self.source.now_utc());
  _anchor(symbol,market_asof) -> self._anchor(symbol,market_asof).
- load: status(symbol,spot) -> self.status(symbol,spot).

No other behavior changes. Physical globals are checked against literal original
AST before removal. Original exception scopes remain; list_reports failures or
structurally invalid decoded JSON are not broadly swallowed when source did not
swallow them. Read report/CSV parsing remains actual json/pandas, not supplied
parsed objects. Source JSON permissiveness is preserved, not a new data policy.

## Observable source behavior

Unsupported symbol returns before any port use. No GC->XAU alias. Empty reports,
invalid latestreport, missing/degraded matchingETF, missing/naive market_asof,
permission not exactly realtime_permission, age outside[-2,45]minutes, badspot/
unsynchronisedanchor, no liveexpiry or missingOIwalls preserve original reason.
Never fall back to an older report on malformed/stale latest. First undegraded
ETF in original symbols order. now is read only after timestamp/permission pass;
explicit now bypasses port and naive explicit now is localized UTC per source.

Anchor actual CSV: coercebad timestamps, only <=market_asof, optional exact src
match (no srccolumn means no filter), sort bytime and choose last; closefinite
and gap<=75minutes inclusive. Latest invalid price does not fallback to earlier
validrow. Underlyinganchorzero/negativefinite accepted bysource; do not silently
tighten rules. Ratio=historicalanchor/reportETFspot, never _current_spot.
Supported identities GLD/XAUUSD, QQQ/NAS100USD and IBIT/BTCUSDT literal mappings.

Expiry day uses America/New_York at market_asof, first inputorder expiry >=day,
not nearest expiry sort. First call/put wall only; bothmustfinite, zero allowed.
Optional flip/positive/negative/maxpain finiteorNone, zero semantics unchanged.
Walls are approximate ETF context, never executable targets or measured edge.
load uses actual status and returns walls, including None on unavailability.

## Evidence and acceptance

Runtime tests first normalmissingmoduleRED, hand-written raw JSON/CSV fixtures,
literal mappedprices/ratio/timestamps/reasons, actual parsers/requestorder and
clock. Full independently pinned ordered AST audit, signature/import/path-global
and substitution count checks; candidate/sourceidentity mutations failclosed.
CLI --source-root explicitparentroot, JSON VERIFIED0/BLOCKED2; freshprocess
forbids chartdesk/floor/tree_replay imports; readinessflags alwaysfalse.
No internal vendor numericaldependencies in this reader; standard pandas/json
are runtime requirements, not claimed historical vendor approval.
Independent task/final reviews required. Source-faithful raw behavior not full
tree/admission/replay/economics/dataset/model proof. Next fulltree/builder/map
operation ordering and causalartifact/provider binding remain mandatory.
