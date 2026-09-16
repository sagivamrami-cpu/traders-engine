# Actual tree and matrix binding for pending revalidation

Architectural continuation of approved master C/D and the complete tree plan's
explicit next step. TREE-REVALIDATION-BINDING-INTAKE.md records the current gap.
No new strategy, simulated fill, economic label or causal-feed claim. Implement
only after TREE-WALK-READER component task/final acceptance.

## Design

Use a narrow raw-port composition outside the accepted source modules. Calling
the live original modules would introduce uncontrolled IO; accepting a supplied
final Walk would leave the gap unresolved. Compose the actual TreeReader,
Revalidation, BasisOperation and original matrix calculations instead. All raw
fetches/artifacts/clocks still reach the same supplied provider, in source order.
No global monkeypatch, caching, dynamic __getattr__ forwarding or defaults.

`_vendor/matrix_reader.py` provides MatrixReader(source), actual read_tf and
read_symbol bodies from chartdesk/matrix.py at commit
68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9, blob
28641487567c457b6922c2a63055659867bb4248. Add self to both signatures. Adapt only
basis.fetch_corrected -> self.source.fetch_corrected, LOOKBACK -> matrix.LOOKBACK,
read_symbol's read_tf call -> self.read_tf, and the complete TFView construction
-> matrix.read_frame(df, tf, note). The latter actual pure projection is already
audited by admission_source; do not copy numerical tool functions. Preserve
corr.show/corr.render semantics (including errors for malformed/None correction),
full delivered history, requested timeframe order and original exception behavior.

`tree_replay/tree_revalidation.py` provides TreeRevalidation(source), a binding
facade inheriting BasisOperation. Constructor calls super().__init__(source),
constructs MatrixReader(source), TreeReader(source), then Revalidation(self).
It must perform no reads, clocks or effects. Actual inherited broker_shape_ok
retains its lazy splice clock. No provider-final matrix or tree method is used.

The facade provides:

- read_symbol(symbol, tfs=('4h','1h','15m','5m')) -> actual MatrixReader.
- tree_walk(symbol) -> actual TreeReader.walk(symbol), default house, no strict
  inference from pending metadata and no trade_from_walk/Plan construction.
- still_valid(t) and revalidate_pending(t, *, now=None) -> actual Revalidation;
  return the original (ok, reason, verified), retaining all three values.
- now_epoch(), now_timestamp(*,tz), deep_exists(key), deep_bytes(key),
  calendar_exists(path), calendar_text(path),
  ensure_shadow_parent(*,parents,exist_ok), shadow_open(mode,encoding) explicitly
  forward to the raw provider. Inherited fetch_corrected and now_utc forward too.
  shadow_open returns the supplied context manager unchanged; do not enter/close
  it eagerly. TreeReader itself directly uses the raw provider's options ports.

The raw provider does not need read_symbol, tree_walk or broker_shape_ok.
Adversarial test methods with those names must never be consumed. It does need
all raw tree and revalidation ports, including correction objects and captured
shadow-writer operations. No default local filesystem or live data loader.

## Source and decision invariants

Accepted `_vendor/tree_*`, revalidation.py, pricing/matrix/basis implementations
remain unchanged. Do not introduce a circular tree/revalidation import.
Source still_valid runs before pending age, separate operation clocks retained.
Under two hours skips tree; exactly two hours consults tree. Opposite direction
wins even with a later tree stop. Stopped/unavailable tree allows/unverified,
not clean approval and not an economic loss. Clean same-side tree preserves the
prior verified flag; it cannot upgrade unavailable still_valid evidence.
No runtime lookup of manifests or source checkouts during revalidation.

## Proof

Raw synthetic multiframe tapes must run through real matrix, stretch, EMA,
shadow calendar, complete tree and pending revalidation. Hand-derived expected
directions/reasons/flags; do not inject a completed Walk or replace still_valid.
Test matching and opposing tree, young/exactly-two-hour boundary, genuine data/
calendar/map failures, earlier veto, and exception precedence. Include a source
whose final-read methods raise to prove they are unused. Retain raw ordered
fetch/clock/writer evidence and unchanged input trade. Missing observations
remain unverified and do not silently become economic failures.

Source audit `audit_tree_revalidation_source(parentroot)` independently pins
matrix source and its two signatures/bodies/adaptations; verifies the complete
ordered facade AST against a literal composition contract; invokes the actual
full audit_tree_walk_source graph, which includes revalidation/admission/basis.
Propagate graph blockers, nonverified empty reports and known input/StopIteration
failures. Always ready_for_replay=False and ready_for_training=False. Explicit
parent-root CLI returns JSON with 0 for verified, 2 for blocked, from unrelated
cwd; auditors do not import/execute original or runtime modules. Test source/
binding/dispatch/clock/signature mutations and real inherited drift.

## Limits and following work

Raw-port integration is not publication-time validation, original resolver/
market-watch arbitration, source-generated lifecycle, checkpoint completeness,
simulation or training. Current CausalAdmissionContext lacks some artifact and
operation-schedule ports; do not present this facade as a historical feed. Continue
that full caller/provider work, remaining producers and master E-I after acceptance.
GC versus OANDA variant and economic/data approvals remain separate human gates.
