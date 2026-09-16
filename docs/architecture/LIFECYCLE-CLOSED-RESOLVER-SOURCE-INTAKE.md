# Lifecycle closed-bar resolver source intake

Authority is the retained `chart-desk` repository at commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`; `chartdesk/tracker.py` must have
blob `b616b34022e436545d8c1daf85eced51614fd74e`.  The source is read as text
only.  This intake covers `tracker.py::check()` lines 1113-1342: the entire
per-record closed 15-minute bar lifecycle, before its gated persistence/save.

For each nonterminal record the source reads a corrected three-day 15-minute
frame.  It skips only that record if fetching fails, correction is unverified,
correction is `tv_stale`, or no bar is strictly later than the plan timestamp.
It derives `since`, its aggregate `hi`/`lo`, and separately derives the
position-only `(hi_f, lo_f)` with `_open_extremes(since, trade)`.  If no
position window is found, source uses exact entry for both extrema.  This
separation is mandatory: post-send extremes may fill a PENDING plan, but may
not pay an OPEN position before its fill.

The accepted closed-PENDING component owns expiry, zone touch, open-slot
conflict, pass-clock revalidation, fresh fill timestamps and same-window
entry/stop ambiguity.  A successful fill falls through in the same pass to
OPEN processing.  For OPEN records the source uses post-fill extrema and this
order:

1. derive protective touch and observe closed-bar minimum success;
2. record minimum success and its source progress state when present;
3. resolve protective/target ambiguity conservatively and continue that record;
4. otherwise resolve progress, unhit targets in ordinal order, then all-target
   completion or ordinary protective touch;
5. do not run the live-only zone-return branch.

The bounded resolver returns only `(messages, changed)` over caller-supplied
mutable state.  It does not call lifecycle gate/persistence/save/delivery,
does not create economic labels, and must return false replay/training
readiness in every audit report.  It is neither a historical replay engine nor
a dataset/model component.
