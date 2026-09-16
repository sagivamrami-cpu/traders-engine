# Lifecycle outcome/shelf source usage

`LifecycleOutcomeShelf` is an offline projection of the retained tracker
helpers `OUTCOMES`, `EXPIRE_H`, `EXPIRE_BY_STYLE`, `_outcome`, `has_open`,
`_expire_h`, `SHELF`, `SHELF_MAX_H`, `REVIVAL_COOLDOWN_S`, `_shelve`, and
`_atomic_json`.

Instantiate it with a supplied source object. It uses only these logical
artifact names:

- `chart-desk/out/trade_outcomes.jsonl` for parent creation and JSONL append.
- `chart-desk/out/shelved_trades.json` for shelf existence/text and atomic
  whole-image replacement.

The source object supplies `now_epoch()` for the two source wall-clock reads.
It supplies `outcomes_mkdir()` and `open_outcomes()` for the outcome artifact;
it supplies `shelf_exists()` and `shelf_text()` for the shelf artifact; and it
supplies `atomic_mkdir()`, `atomic_mkstemp()`, `atomic_fdopen()`,
`atomic_fsync()`, `atomic_replace()`, and `atomic_unlink()` for the source
atomic-write sequence. The inner unlink is best effort; a write failure still
propagates. `event_ts=0` intentionally uses the operation time, matching the
source truthiness branch.

`has_open` delegates to the accepted `TrackerAdmission` implementation. A
PENDING candidate is not exposure; malformed or unreadable state fails closed.
The shelf helper preserves `revived_from_ts` when present, rather than
restarting its original age.

This component records raw tracker facts only. It does not read market data,
revive shelves, send a message, access a broker, infer a fill, calculate P&L,
create a label, construct a replay/dataset, train a model, or establish any
readiness claim.

Acceptance evidence is recorded in
`agent-exchange/status/2026-09-14T060000Z-codex-lifecycle-outcome-shelf.md`.
The retained-source auditor requires the accepted tracker-admission and
lifecycle-gate proofs, pins their identities/projections, and fails closed on
every inconsistent, malformed or unserializable report. Both readiness flags
remain false.
