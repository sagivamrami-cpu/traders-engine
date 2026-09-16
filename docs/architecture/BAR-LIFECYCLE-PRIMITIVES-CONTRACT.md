# Original position geometry and directional-success source primitives

Approved master C/D/E continuation, before full advisory resolver reconstruction.
Keep source position geometry and desk movement proof separate from the approved
fixed-stop/full-TP1 economic simulator. This component introduces no new rules,
historical feed evidence, market labels, public readiness or live functionality.

## Source authority and scope

All chart-desk at68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9:

- tracker.py blob b616b34022e436545d8c1daf85eced51614fd74e: complete _fill_on_tape,
  _position_extremes, position_bars, _open_extremes and _entry_band only.
- desk_success.py blob d2b2fdb2889841f587338e56041ffdc8df6c298c: VERSION/FLOOR,
  minimum, reached, observe, observe_bars, classification, stop_note. Exclude
  audited_classification (depends on scripts.week_report, separate reporting).
- voice.py blob46fc6912ed8914b54209f9c08c12de9f48a19059: entire pure module.
- Reuse existing accepted pricing.entry_zone and basis_symbols.canonical_symbol;
  inheritance must be audited, not assumed from names. Original admission audit
  already checks these source projections; new audit invokes it as a dependency.

Retained parent is the explicit current source-review directory in source intake.
No source module is imported, compiled or executed during extraction/audit.

## Runtime projection

Private _vendor/lifecycle_bars.py holds all five complete original functions with
original signatures/order/error boundaries. Imports pandas as pd and inside
_entry_band redirects tradeplan.entry_zone to accepted pricing.entry_zone only.
No caller validation, sorting, timestamp backdating, closed-target filtering or
economic fill rule is added. Inputs are caller-supplied frames and source trade
rows; raw helper success does not establish causal data correctness.

Private _vendor/lifecycle_voice.py is complete original pure module, unchanged
except its module-level provenance docstring if supplied. No external delivery.
Private _vendor/desk_success.py keeps VERSION/FLOOR and minimum as module symbols,
with canonical_symbol import redirected to basis_symbols. Convert reached/observe/
observe_bars/classification/stop_note to DeskSuccess(source) methods. Calls between
those functions become self methods. Original time.time calls use source.now_epoch;
original tracker.pd.Timestamp.now(tz="UTC") uses pd.Timestamp(source.now_utc()).
now_utc is an explicitly supplied aware UTC datetime port, not a float roundtrip.
observe_bars imports lifecycle_bars as tracker and uses that actual implementation;
voice imports lifecycle_voice. Other body/constants/branches remain unchanged.

Source owns clocks only: now_epoch() -> float, now_utc() -> aware UTC datetime.
Neither defaults to wall time. Caller must provide both from the same operation
clock. Do not change accepted CausalAdmissionContext APIs in this component; full
resolver binding will implement these ports with traced operations explicitly.
This private source projection is not a new public time/data validation boundary.

## Required behavior

- Pending touch is strictly after send; direction/entry band and exception-to-None
  are unchanged. Existing OPEN with filled_ts and include_fill_bar modes retain
  their distinct window selection. Do not replace original comparison boundaries.
- Fill bar contributes adverse extremes but not favourable extremes when included.
  With no paying bar favourable extreme is original entry, not a future target.
- Movement proof binds version/trade_id/trade_ts/exact symbol/floor/source and
  source time/resolved horizon. Defaulting via truthiness (as_of or clock) and
  source numeric tolerances remain unchanged. It is not a probability or net_R.
- Observe mutates minimum_success only after source proof validates. Unsupported
  symbol, missing trade ID, nonOPEN row, insufficient movement, final target below
  the floor or future/invalid proof cannot fabricate success. Source messages use
  exact original identity-first units because downstream gates parse the text.
- observe_bars uses actual position_bars(include_fill_barTrue); excludes fillbar
  and any bar at/after first original-stop touch; excludes future index stamps.
  First paying threshold crossing is discovered from source tape, but observed_ts
  and detected_ts are the operation clock, not an invented intrabar crossing time.
- Classification remains source movement status; historical audited reporting is
  excluded. Existing sticky proof can coexist with later STOPPED economics, and
  caller-provided measurement is not itself historical certification.

## Audit and verification

Independent literal pins, ordered symbol projection, exact allowed substitutions
and counts, complete module AST comparison including imports/classes/signatures.
Check full voice module and inherited pricing/canonical projection. No manifest
can redefine the audit authority. CLI requires retained root, no source execution,
VERIFIEDexit0/BLOCKEDexit2 with false replay/training readiness.

Tests must run normal missing-module RED before implementation. Use real pandas
frames, original entry band, actual ReplayClock-backed test clock ports and exact
hand-derived expectations. Exercise long/short, before/on/after send and fill,
empty/missing/sparse windows, firstbar adverse/favourable asymmetry, proof identity
and chronological boundaries, stop-before-threshold/threshold-before-stop,
samebar stop/threshold, final-target cap, future rows, sticky proof and units.
Audit mutations must catch changing strict/inclusive boundaries, clocks, identity
checks, caller source tags, units, extra code and inherited dependency drift.

Task and combined independent reviews precede acceptance. Still required after
this component: causal lifecycle feed binding, still_valid/aged tree revalidation,
independent verifier/receipt/park/outbox/shadow/shelf/outcome effects, full check/
live/manage/closeout caller, watch lock/arbitration and remaining producer paths.
Economic simulator/coverage/dataset/models/evaluation remain in the full master.
