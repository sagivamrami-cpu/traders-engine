# Operation-clock map binding: source intake, not implementation

Continuation after accepted patternreaders220345Z. Full original levelmap.py
selected functions and accepted levelmap_build.py were main-read, including
all body statements of build, _session_open_levels and _ema_levels.
Source chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9;
chartdesk/levelmap.py blob01fc9fe098aa7a5991ce62c3a83e870e4f0d5a2e.
Existing proof is tools/check_levelmap_source_parity.py, not a tree_spec module.

## Exact distinction

Accepted build_at uses a required fixed decision_time. Its source-specialization
replaces the complete optional-now expression in _session_open_levels with
pd.Timestamp(decision_time). This is correct for its documented fixed-T API,
not proof of original event-loop clock ordering. Preserve that public API.

Original build fetches daily1d400, computes weekly/monthly/ranges/backdays, then
calls _session_open_levels(symbol,missing). That helper fetches5m3 first, exits
on fetcherror/None/empty or corrNone/source-none, constructs datetimeindex, THEN
reads pd.Timestamp.now('UTC') if no explicit now. Original clock is therefore
not read if early validation returns. An explicit now still does not bypass
the fetch/correction gates. Clock exceptions and postfetch malformed input are
not broadly swallowed by this helper.

At operationclock it checks actual venue timezone/DST/weekdays/startinclusive/
endexclusive and exact opening-bar timestamp. Missingexactbar is omitted, not
nearestmatched. Duplicateexactbars use firstopen. Splicecorrection only admits
openingbar at/after tv_from; source-none blocks even exchange-nativeBTC here.
These differ from daily/psy broker_shape_ok rules and must not be unified.

Original build then prefers1h20 for PSY, falls back15m20 only according to
original loop/catches; accepts broker_shape_ok(...,7) and clips splicedframe to
tv_from before actual sessions.psy_levels. _ema_levels fetches1h240/4h240 with
actual tr.emas and2*n convergence. Quarters last. No pivotfamily added here.

## Dependency clock that must not be lost

basis.broker_shape_ok reads pd.Timestamp.now('UTC') only on the tv_spliced+tv_from
branch. Puretv_daily/mt5_broker and exchange-nativeBTC return before that read.
Accepted broker_shape_ok_at(corr,days,decision_time=...) is numerical proof with
a fixed suppliedtime; calling source.now_utc unconditionally before invoking it
would introduce extra reads. Future causalprovider must preserve this laziness.
Source function lines527-557; originalblob is independently pinned by the
accepted correction source contract. Existing _OfflineSource in levelmap.py
uses its fixeddecisiontime as designed; it is not the operationclock provider.

## Next implementation requirements

- Additive rawoperationclock binding; no global monkeypatch or changed fixed-T
  public semantics. Actual range/session/EMA/quarter/backday calculations remain.
- Prefer reusing accepted NamedLevel/SESSION_OPEN_LEVELS/_ema_levels and actual
  map_tr/sessions/quarters/backdays; do not receive provider-final maps or levels.
- Independently audit any new source projection and inherited originalgraph.
- Literal test crosses a session boundary DURING the5mfetch; session eligibility
  must use subsequentclock, while datafetch result remains its own observation.
- Test earlyreturn has no clock, explicitnowbypass, spliceseam/broker clocklazy,
  source-family gates, wholebuild order and unchanged fixed-T publictests.
- Bind original treewalk/build consumers to operationvariant only after separate
  component acceptance. Causalframe/publication/artifact coverage remains another
  obligation, not certified by rawport tests.

This is a read-only engineering intake. No runtimeinterface selected or changed,
no fulltree/dataset/model readiness claim. No human strategy decision is needed
to implement the original operationorder; realdata GC/spot decision is separate.
