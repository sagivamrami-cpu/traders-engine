# Lifecycle OPEN minimum-success source intake

Pinned source: `chartdesk/tracker.py::_check_live_locked`, lines 2690–2704 at
chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`.

## Source contract

This branch consumes a caller-supplied OPEN trade, post-fill `(low, high)`,
current spot, source quote record, membership of the already-observed
forming-bar-extremes map, and the provisional bar `minimum_message` from
accepted `LifecycleOpenPostfillEvidence`.

1. Compute the published protective touch from the supplied range.
2. Only when no bar minimum message exists, protection is untouched, the
   symbol has no forming-bar extremes, the raw quote `lp` equals supplied
   spot, its age is within `FORCE_BAR_AGE_S`, and quote time is not before the
   fill time, observe the accepted exact-venue quote minimum message.
3. When a minimum message exists, derive accepted progress steps over the
   directional best extreme. If steps exist and protection was untouched,
   persist the last progress step. Always write source minimum points, append
   the message and append exactly one raw `minimum_success` outcome fact.

The offline projection adapts source wall time to one supplied source clock;
it does not acquire the raw quote, bars or forming-bar map itself. It returns
only `(messages, changed, minimum_message)` so the caller can pass the actual
message onward to ambiguity and ordinary-resolution components.

## Boundaries

This slice ends before ambiguity resolution. It neither resolves protection,
targets, ordinary progress, terminal state, zone return, persistence, gate or
delivery. A raw `minimum_success` tracker fact is not a fill/P&L/economic
label, replay row, dataset row, training target or model signal.
