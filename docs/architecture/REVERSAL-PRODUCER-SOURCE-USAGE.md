# Original reversal producer source sidecar

`trading_system.tree_replay._vendor.reversal_producer` preserves the complete
original `find` and `conflicts` from `chartdesk/level_reversal.py` at chart-desk
commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, blob
`7c0eee53d97a1ba9280626fdb2d20eba61b5aa1b`. It is an internal calculation
sidecar for the approved [producer contract](REVERSAL-PRODUCER-SOURCE-CONTRACT.md).
It does not validate public as-of inputs or establish external admission.

```python
from trading_system.tree_replay._vendor.reversal_producer import find_at
from trading_system.tree_replay._vendor.level_reversal import detect_frame

selected = find_at(
    "OANDA:XAUUSD",
    decision_time=validated_decision_time,
    source=validated_offline_source,
    map_source=validated_map_bridge,
    detector=detect_frame,
)
```

The names above denote already validated offline dependencies. The exact
signature is `find_at(symbol: str, *, decision_time, source, map_source, detector)`.
`source.fetch_corrected(symbol, timeframe, lookback_days)` returns the source
DataFrame/correction pair. `map_source.build(symbol)` returns actual ordered
levels and daily correction computed at the same decision time T. The detector
seam is internal instrumentation only: it must call the accepted real
`level_reversal.detect_frame`, preserving all arguments and results. Public
callers must not supply a detector, computed map, or source-choice flag.

After the original docstring, the only body changes are the bindings
`basis = source`, `levelmap = map_source`, `detect_frame = detector`, and
`now = _utc(decision_time)`. All remaining statements, annotations, guards,
exceptions and sort expressions are retained. Dependencies are imported from
the accepted detector and pricing sidecars; none of their formulas is copied.
The original docstrings are retained for parity, including their live/fresh
wording; this module does not itself perform live reads or prove freshness in
`conflicts`.

## Preserved source decisions

The map is built first. Empty levels, absent daily correction, or daily
`unverified` veto the producer before timeframe fetches. A daily correction's
source label is not independently vetoed here: verified proxy/replay/none
values can pass this particular guard. Map reconstruction retains its separate
family-specific correction and broker-shape requirements; this does not certify
proxy/replay data or relabel it as `tv_daily`.

The producer fetches `5m/10` then `15m/10`. Each fetch exception skips only
that timeframe. A missing or unverified bar correction, or its exact
`source == "none"`, skips detection. Both real detector calls use T and their
accepted `LIVE_MAX_AGE_S` value, 370 seconds inclusive. One microsecond older
is excluded. The detector retains its original normalization, closed-bar
filtering, vector calculations, per-episode deduplication and nearest eligible
level selection.

All returned fresh events participate, including a confirmation before the
newest nonsignal bar. The global newest confirmation wins; M5 wins an equal
confirmation time. Only that event and its own timeframe history are priced
through the original `build_plan`. A refused winner is returned, never replaced
by an older paying plan. Return is `None` or the original `(Reversal, Plan)`.
These are source objects, not public readiness or trade-admission results.

`conflicts(reversal, candidate)` is unchanged. It requires both plans, the
reversal's source `tradeable` property, equal symbols, nonempty directions and
different directions. It does not require the candidate's tradeability, check
timestamps, or run the outer market-watch admission sequence. The source Plan
may have `tradeable=True` when its pricing predicate passes. Any public wrapper
must expose admission/tradeability and replay/training readiness as false;
rewriting the source property here would break the approved contract.

## Audit and verification

```powershell
python -m pytest tests/tree_replay/test_reversal_producer_source.py -q --tb=short
python tools/check_reversal_producer_source_parity.py
python tools/check_reversal_producer_source_parity.py --source-root C:/path/to/pinned/chart-desk
```

Root precedence is the explicit argument, `TR_CHARTDESK_SOURCE_ROOT`, then the
retained checkout recorded in the tool. The audit reads source/vendor text and
AST only. Neither those modules nor the runtime clock wrappers execute during
auditing. It verifies exactly one baseline chart-desk commit, an independently
fixed source blob, the entire producer manifest, transformation preconditions,
and the complete ordered vendor module including exact import order. Extra
statements, reordered imports, changed guards or bindings fail verification.
Checkout newlines are normalized to Git LF for blob comparison.

Every invocation runs the full accepted `check_levelmap_source_parity` audit,
including range, pricing/detector, EMA and correction dependencies. Both subset
flags must be literal true, blockers empty, and both readiness flags literal
false. The accepted map manifest is independently sealed with canonical JSON
SHA256 `0cd26630c3274cdaf7c4959c87d8ac06be89652229ed24c541fd46c7cd76a5ab`:
UTF-8 `json.dumps(value, sort_keys=True, allow_nan=False)` with default separators.
JSON numeric zero cannot substitute for false. Missing/malformed inputs or
dependency import failures produce `BLOCKED` JSON and exit 2. Successful
verification returns `VERIFIED` and exit 0; readiness remains false.

Runtime calls do not automatically perform this source audit. Source formula
verification does not certify the controller's separate period/frame/map clock
wrappers or the subsequent public producer adapter. Those need their own tests
and review. Supplied maps in these low-level tests are permitted fixtures, not
a public data path or historical level-map certification.

The public adapter must distinguish event confirmation, observation cutoff,
publication and decision T. It must not backdate current maps to the event or
rewrite timestamps to force availability. Source checks alone do not establish
calendar coverage, feed provenance, instrument support, or partial-base-bar
handling. No GC/spot mapping is authorized.

Outer market-watch scoring/windows, calendar/tracker gates, episode state,
cross-producer arbitration, fills, outcome simulation, datasets and model work
remain open. This sidecar changes no live alert behavior and grants no data,
retention, fitting, deployment or trading approval. Independent controller
review and broad verification remain required for acceptance.
