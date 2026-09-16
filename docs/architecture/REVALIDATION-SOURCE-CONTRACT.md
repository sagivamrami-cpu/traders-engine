# Original pending-plan revalidation over offline inputs

Continuation of approved master C/D, not a new strategy or changed safety rule.
Existing feature checkout; no commits, live calls, real-data acquisition or labels.
Source chart-desk commit68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9,
tracker.py b616b34022e436545d8c1daf85eced51614fd74e and
tradeplan.py d09e9be39ce8dadf1674029e0c03751c70502135.
Source is read/AST-parsed only, never imported/executed.

## Scope and architecture

Private _vendor/revalidation.py will retain the complete calendar_event_ts,
calendar_high_impact_in_window, _bias_against, _tree_agrees, revalidate_pending,
_shadow and still_valid bodies, with the exact boundary adaptations below.
No replacement by supplied final revalidation verdicts. Compose actual
TrackerAdmission._higher_bias, StretchReader.state, EmaReader.read_stack,
admission_matrix.read_structure, pvsra.pvsra and watch_sessions.current_session_at.
Constants/labels retained from tracker; voice is actual lifecycle_voice.

Class Revalidation(source) stores source, admission=TrackerAdmission(source),
stretch=StretchReader(source), ema=EmaReader(source). Methods in original order:
_tree_agrees, revalidate_pending, _shadow, still_valid. Original signatures gain
self only. Pure helpers remain module-level. Keep original argument/return
annotations, docstrings, try boundaries, data mutations, evaluation order and text.

Supplied source contract (no defaults or live loaders):
- Existing read_symbol, fetch_corrected, broker_shape_ok, deep_exists/deep_bytes
  ports, shared by actual composed readers; no precomputed Window/Stretch port.
- now_epoch()->float; now_timestamp(*,tz)->pd.Timestamp;
  now_utc()->aware UTC datetime. Actual per-operation reads, not a frozen pass T.
- tree_walk(symbol)->source Walk-like result or None; raises captured errors.
  This is an explicit UNBOUND dependency on full tree.walk, not a fake completed
  tree adapter. Complete walk/producers and causal port provenance are required
  before full replay certification. Tests can use controlled raw boundary replies.
- ensure_shadow_parent(*,parents,exist_ok), shadow_open(mode,encoding) returns a
  text-writer context manager for logical chart-desk/out/revalidation_shadow.jsonl.
  Preserve ensure/open/time/write/close sequence and swallowed source errors.
- calendar_exists(logical_path), calendar_text(logical_path); exact path
  news-desk/data/ff_calendar.json. Text parsed with actual json.loads. Absent,
  unknown, read failure and invalid evidence must remain distinct in future trace.

These private ports do not certify causal data, source provenance, filesystem
effects, historical process timezone, complete checkpoint or full tree behavior.
No advisory PENDING->OPEN outcome here is an economic fill or profit label.

## Exact projection

Imports: future annotations; json; pandas as pd; PurePosixPath; lifecycle_voice
as voice; admission_matrix; pvsra; watch_sessions; TrackerAdmission from
tracker_admission; StretchReader from stretch; EmaReader from ema_windows.
Constants in original tracker order: AGED_PENDING_RECHECK_H,
_BIAS_AGAINST_AS_SENT, _BIAS_AGAINST_FLAT_AT_SEND, _BIAS_AGAINST_UNREAD,
SOFT_STALE_MIN, HARD_STALE_MIN. Then pure calendar helpers in tradeplan order,
then _bias_against, then Revalidation. No SHADOW_LOG physical path copied.

_tree_agrees: remove `from . import tree`; tree.walk(symbol) becomes
self.source.tree_walk(symbol). All result precedence and caught errors remain.

revalidate_pending: still_valid(t)->self.still_valid(t),
time.time()->self.source.now_epoch(), _tree_agrees(t['symbol'],t['direction'])
->self._tree_agrees(...), each once.

_shadow: SHADOW_LOG.parent.mkdir(parents=True,exist_ok=True)->
self.source.ensure_shadow_parent(parents=True,exist_ok=True);
SHADOW_LOG.open('a',encoding='utf-8')->self.source.shadow_open('a',encoding='utf-8');
time.time()->self.source.now_epoch(), each once. Actual json.dumps ensure_ascii
False and newline, bool conversion, original best-effort catch retained.

still_valid: remove the eight source-local import statements for stretch,
basis, emawin, sessions, basis/matrix aliases, basis/tr aliases, workspace.repo
and tradeplan.calendar_high_impact_in_window. Retain original standard-library
local imports. Replace exactly once each:
- _higher_bias(symbol)->self.admission._higher_bias(symbol)
- stretch.state(symbol)->self.stretch.state(symbol)
- basis.fetch_corrected(symbol,tf,3)->self.source.fetch_corrected(symbol,tf,3)
- pd.Timestamp.now(tz=last.tz)->self.source.now_timestamp(tz=last.tz)
- emawin.read_stack(symbol,timeframes=('1h','15m'))->self.ema.read_stack(...)
- sessions.current_session()->watch_sessions.current_session_at(
  decision_time=self.source.now_timestamp(tz='UTC'))
- _b.fetch_corrected(symbol,'4h',400)->self.source.fetch_corrected(...)
- _mx.read_structure(_d4)->admission_matrix.read_structure(_d4)
- _b2.fetch_corrected(symbol,'15m',60)->self.source.fetch_corrected(...)
- _tr.pvsra(_d15)->pvsra.pvsra(_d15)
- _repo('news-desk')->PurePosixPath('news-desk')
- _cal.exists()->self.source.calendar_exists(_cal.as_posix())
- _dt.now(_tz.utc)->self.source.now_utc()
- _cal.read_text()->self.source.calendar_text(_cal.as_posix())
Replace the15 load-name occurrences of _shadow with self._shadow. All other
expressions, including the actual calendar function call/window30*60, unchanged.
Counts are literal source preconditions, not inferred from candidate code.

## Required behavior

Bias requires both higher frames via actual TrackerAdmission and summed
magnitude25 with no higher frame still favoring trade. Cancellation requires
stored send sum WITH trade; unread/flat/alreadyagainst sends get distinct labels.
Bias flip veto precedes stretch/freshness/shadows. A same-side extended stretch
veto precedes age/shadows; opposite extension does not veto. Missing stretch or
core exception leaves verifiedFalse and logs, then still evaluates age/shadows.
Invalid direction access outside core try remains an error.

Age: separate15m/1h/4h requests with lookback3, original order; ignore correction
flags; skip None/empty. Normalize minutes by bar_minutes/15. Oldest available
ratio governs; exception resets all age evidence toNone. >120 blocks/unverified,
>20 orNone allowed/unverified. Exact equality passes each threshold. Negative
age is not clamped. An available frame can supply age despite another missing.
This is source behavior, not sufficient historical coverage certification.

Shadows in order: EMA1h/15m, session, stop_distance, structure4h400,
opposing-vector15m60/last12, news. Fired shadows do not change admission/verified.
Missing calendar is logged, not asserted clear; invalid JSON/inside-window
missingimpact produces unavailable detail through original catch. Keep all
best-effort shadow side effects and operation clocks distinct from decisions.

Calendar: nonzero numeric dateline except bool takes precedence, including
negative/nonfinite raw values; otherwise ISO date parsed via fromisoformat.
Offset-free date inherits host timezone in raw source, NOT an approved replay
timezone. Do not silently choose UTC or normalize impact: strip only validates
nonempty, high test is lower().startswith('high') on original string. First
matching input-order row wins, boundary inclusive; missingimpact inside raises.

Pending: still_valid first; stop immediately if false; only then read default
clock. Missing/invalid send ts yields True with verifiedFalse, not a veto.
Age max0, under2hours no walk, exactly2hours walk. Opposing direction wins over
stopped_because. None/error/stopped tree is allowed but unverified; only exact
'העץ מאשר' keeps prior verified. Returned messages preserved.

## Evidence and acceptance

Task1 runtime tests must drive actual numerical dependencies using supplied
frames and calculated TFViews; test exact port sequence, shadow JSON output,
per-operation times, exception boundaries, labels and opposite/unknown paths.
Controlled tree_walk is explicitly only a boundary fixture. Include an actual
read_symbol adapter over frames; do not substitute entire still_valid/Stretch.
Pure _bias_against matrix supplements real dependency tests.

Task2 audit: literal pins/root/baseline; entire ordered runtime AST and exact
substitution counts; actual inherited tracker-admission, stretch, EMA-windows,
admission-calculations, watch-IO, lifecycle-primitives and default-PVSRA source
audits. Mutation of any consumed dependency blocks. No imports/execution of
source/runtime by auditor. Explicit CLI parentroot, JSON VERIFIED0/BLOCKED2,
always false replay/training readiness. Task/final reviews before acceptance.

Continue full tree.walk, causal lifecycle feeds, original resolver/caller/state
effects, other producers, simulator, approved historical data and models after
this component; this contract does not reduce the master scope.
