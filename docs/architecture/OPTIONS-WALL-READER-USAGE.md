# Options context from raw offline artifacts

Private API: trading_system.tree_replay._vendor.optionswall.OptionsWallReader.
Construct with a source implementing list_reports(), read_report(report_id),
read_tv_csv(filename), now_utc(). First returns logical report IDs; next two
return raw text; clock returns an aware UTC datetime/pandas timestamp.

status(symbol,_current_spot=None,*,now=None) returns original OptionsStatus
with precise reason and optional Walls. load(symbol,spot) calls actual status
and returns only Walls or None. No default source, disk access or process clock.
Component accepted after source audit and independent task/final reviews:
agent-exchange/status/2026-09-09T220947Z-codex-options-reader.md.

The reader sorts report IDs and reads only the lexically latest; it never
silently falls back to an older usable report. Actual json.loads and pandas
CSV parsing remain. Reports must carry an aware data_asof, exact realtime
permission and original age bounds. CSV anchors are filtered at market_asof,
not current time; optional src is matched exactly to the underlying symbol.
The first valid input-order expiry uses the New York market date. Report order,
first-wall selection and original exception scopes are unchanged.

Mapping is historical underlying anchor / report ETF spot. Changing the current
spot does not move the walls. Source accepts finite zero/negative underlying
anchor values; these raw results are not a new endorsement of input quality.
Walls are approximate context, not executable targets. Only original GLD/XAU,
QQQ/NAS and IBIT/BTC mappings exist; GC futures are not aliased to OANDA spot.

These interfaces do not prove artifact availability at an historical instant.
The later causal provider must establish identity, provenance and publication
at each operation. No report download, vendor permission, market labels, model
training, broker execution or live promotion is enabled. Raw source catches
and reasons are evidence for later features, not guaranteed measured negatives.
