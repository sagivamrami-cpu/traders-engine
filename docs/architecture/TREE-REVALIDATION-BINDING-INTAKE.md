# Actual tree -> pending revalidation: remaining binding

Read-only intake, 2026-09-10; not implementation or acceptance. Depends on
the complete tree component's pending task/final gates. Full master C/D/E-I
requirements remain intact.

Current `_vendor/revalidation.py` retains the source `_tree_agrees` and
`revalidate_pending` bodies, but `_tree_agrees` still calls
`self.source.tree_walk(symbol)`. The existing tests explicitly supply a
boundary reply. They do not demonstrate the actual tree drives aged pending
revalidation. `_vendor/tree_walk.py` now implements the actual reader but has
not yet closed its source-audit and review gates.

The next connection must return an actual `TreeReader(...).walk(symbol)` from
that port. Do not import TreeReader inside revalidation.py: tree_core's actual
calendar helpers already import revalidation. Compose outside these modules
and leave their accepted source bodies and public fixed-T adapters unchanged.
Construction must be inert; no eager fetch, calendar load or clock.

Source semantics to preserve (revalidation.py:92-134):

- `still_valid` runs first. Its veto ends pending revalidation immediately.
- The default age clock is read only afterwards; explicit `now` avoids it.
- Missing/invalid send time allows but is unverified. Age below two hours
  skips the tree; age exactly two hours consults it.
- An opposite tree direction takes precedence even when that same Walk has
  a stop reason. A matching stopped/unavailable tree allows but is unverified.
- None/exception paths keep their distinct messages. Only the exact clean
  tree approval preserves prior verified status. This is not an economic fill.
- The original call passes no variant. It uses house; do not silently infer
  strict from unrelated metadata on the pending trade.

Raw inputs needed by the composed readers exceed the current admission context.
`CausalAdmissionContext` currently binds matrix/raw frames, quotes, tracker,
logs and supplied lock operations. It does not yet implement the tree's raw
calendar/options/deep-file operations or complete historical operation schedule.
Do not claim that wrapping this context alone completes causal replay.

An intermediate raw-port composition can reuse actual BasisOperation for shape
qualification (including its lazy splice clock), the complete TreeReader for
tree decisions, and existing real matrix/frame readers. Forwarding boundaries
must preserve read order, exceptions, actual timestamps and identity, not cache
one computed Walk or return a provider-final success flag.

Required integration proof after implementation: actual rising/falling raw
multiframe tapes lead to matching/opposing aged decisions; raw news/data/map
failures stay unverified with the original reason; an opposing direction still
wins over a later stop; young pending makes no tree reads; exactly-two-hour
boundary does. Real still_valid numerical inputs/shadow effects must remain in
the path. Source audits for both components remain mandatory, but two green
component audits alone are not proof of the new binding or historical causality.
