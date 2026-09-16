# Tracker lifecycle transitions — source intake

## Authority and boundary

This is the next source closure after the accepted caller commit seam. Authority
is the retained chart-desk tracker at commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, blob
`b616b34022e436545d8c1daf85eced51614fd74e`, read and parsed as text only.

Both source resolver bodies call a common set of transition/message helpers.
They determine conservative ambiguity handling, published-stop resolution,
progress ladder state, fill/target/cancel text, terminal bookkeeping and the
operation-time terminal stamp. These helpers do not fetch bars or quotes,
choose a trade, save state, journal, deliver a message, simulate an order or
create an economic outcome.

## Selected source set

The first transition component must project this source-order set:

```text
_tp_management_line, _UNVERIFIED_NOTE, _fill_caveat, _il_clock, _journey,
_ambiguous_touch, _resolve_ambiguous, _ambiguous_result,
_resolve_protective, _protective_result, _mark_terminal, PROGRESS_PCT,
_progress_pct, _progress_steps, _progress_messages, _protective, _fill_line,
_target_line, _no_score, _cancel_line
```

`_mark_terminal` is the only selected state clock effect: source `time.time()`
becomes supplied `source.now_epoch()`. Source `desk_success.stop_note` becomes
an accepted `DeskSuccess(source)` instance, while source `basis`, `voice` and
entry-zone geometry are satisfied by accepted `basis_symbols`, `lifecycle_voice`
and `lifecycle_bars._entry_band` components. Internal selected helper calls are
bound to one `LifecycleTransitions(source)` instance.

## Preserved semantics

- A bar range that touches both protection and an unhit target is explicitly
  ambiguous and resolves on the protective side, not as a target win.
- The protective price is the published `t['stop']`; TP1 does not silently
  replace it with entry. Break-even/trailing result names remain source facts.
- The progress ladder is source percentage-by-symbol, starts after previously
  reported `progress_step`, and caps strictly below TP1. It emits movement
  notices, not realised economic profit, and mutates only ladder fields.
- Fill/target/cancel/terminal messages retain original text construction and
  source formatting dependencies. `to_group` stays source state data.
- Terminal mutation sets only source `state` and operation-time `resolved_ts`.

## Deferred helpers and loops

`_zone_return_message`, `_entry_recheck`, `_excursion`, quote fallback,
corrected-bar coverage/staleness, open-slot arbitration, revalidation, outcome
write/shelf persistence, parked replay context, and both resolver loops remain
outside this component. They need separate causal feed and state evidence.

No accepted transition helper is a fill, execution, economic label, delivery,
historical replay, dataset or model readiness claim.
