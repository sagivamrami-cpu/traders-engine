# Lifecycle OPEN zone-return source intake

Pinned source: `chartdesk/tracker.py::_excursion`, `_entry_recheck` and
`_zone_return_message` (lines 1046–1106), called only by the live OPEN branch
at lines 2751–2759. Authority remains chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`.

## Required source behavior

The private projection receives one caller-supplied OPEN trade and live spot.
It computes the reported excursion as `max(progress_step, desk_success.reached)
/ number_of_hit_targets`. No excursion means no message. A prior zone-return
blocks repeated messages until the target count exceeds the target count stored
in its `zone_return_at` marker; malformed prior markers fall back to zero.

For short, spot is in the entry band at or above `zone_low`; for long, at or
below `zone_high`. Only then construct the source message, including journey,
entry recheck and unchanged stop/targets notice, store `zone_return_at` and
return the message.

`_entry_recheck` calls the accepted private revalidation reader's
`still_valid` result but remains label-only:

- if revalidation is both false and unverified, state that evidence was not
  freshly verified;
- if valid, report valid plus reason and the unverified note where relevant;
- if invalid and verified, report invalid plus reason.

No result cancels, closes, alters stop/targets or creates an outcome. A caught
revalidation error becomes `(True, "", False)`, exactly as the source helper.

## Scope boundary

This is a live-spot state observation, never a bar-wick replacement. `spot` is
caller-supplied, but the projection deliberately constructs
`Revalidation(source)` and calls its actual `still_valid(trade)` method for the
advisory recheck label. It is not a precomputed recheck-label port.

Consequently, this component inherits the accepted revalidation reader's
offline-port boundary: `still_valid` may call `source.fetch_corrected(...)`,
and its shadow path may attempt source-owned shadow writes. Task 1 makes no
claim that the composed call cannot acquire/revalidate or cause those inherited
shadow effects. The supplied source owns and constrains those ports; no retained
source is imported or executed here.

Zone-return's own behavior remains label-only: it creates no direct terminal,
outcome, persistence, or delivery decision and mutates only `zone_return_at`
when it emits. It is not a target/protective/minimum/ambiguity resolver,
persistence/gate or delivery system, economic outcome, replay, dataset,
training/model or live-trading authorization.
