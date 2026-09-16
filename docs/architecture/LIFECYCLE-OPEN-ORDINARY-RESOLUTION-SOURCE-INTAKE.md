# Lifecycle OPEN ordinary-resolution source intake

Pinned source: `chartdesk/tracker.py::_check_live_locked`, lines 2721–2750 at
chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`.

## Source contract

This slice begins only after the preceding OPEN ambiguity branch has returned
without change. It consumes one caller-supplied OPEN trade, its post-fill
`(low, high)` window and the already-observed `minimum_message` (or `None`).
It must preserve this physical order:

1. Derive whether TP1 is now touched. Suppress progress if protection was
   already touched, minimum success was observed, TP1 is now touched, or TP1
   was already hit.
2. Otherwise use the accepted shared progress ladder on the directional best
   extreme. If it emits messages, write `progress_ts` from the supplied source
   clock and mark changed.
3. Walk unhit targets in ordinal order. For every touched target, append the
   `TPn` tag, write `progress_ts`, append the accepted target message and
   append exactly one raw outcome fact with `result=tpn`.
4. Recompute protection *after* target mutation. If all targets are hit, mark
   `DONE`. Otherwise, if protection is touched, resolve the accepted protective
   message/result/state, mark terminal and append its raw outcome fact.

The source's apparently unusual empty-target behavior (`len(hit) >=
len(targets)`) is retained exactly: it marks the record `DONE`.

## Boundary and ownership

The caller owns causal post-fill evidence and must invoke the accepted
`LifecycleOpenProtection` first. If that conservative ambiguity projection
changes the trade, this ordinary projection is not called. `minimum_message`
is evidence from the accepted post-fill collector; this slice uses it only to
suppress progress and does not write its minimum-success outcome.

The immediately following source `else` (lines 2751–2759) is deliberately
out of scope. It is a live-spot zone-return state machine that depends on
`_excursion`, entry revalidation and the source's spot path. It will be
recovered in a separately pinned slice, rather than being approximated from a
bar range here.

This is not bar/quote acquisition, a full resolver, persistence, gate,
delivery, economic P&L, simulation, replay, dataset creation, training, model
promotion or live-trading authorization.
