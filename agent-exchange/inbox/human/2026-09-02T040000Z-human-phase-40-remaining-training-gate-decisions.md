# Agent Exchange Request

Target:
Human

Sender:
Codex

Created at:
2026-09-02T04:00:00Z

Status:
NEEDS_HUMAN_APPROVAL

Objective:
Collect the remaining human decisions required before Codex may build the
first real GC 30m dataset and start baseline model training.

## Current Verified State

The readiness checker currently returns:

- status: `BLOCKED`
- training_start_allowed: `false`
- blocking_reviews: `[]`
- remaining required gates:
  - `SESSION_CALENDAR`
  - `MISSING_BAR_POLICY`
  - `ROLL_POLICY`
  - `DATASET_IDENTITY`
  - `ORDER_FLOW_SOURCE_DECISION`
  - `LABEL_CONTRACT`
  - `SPLIT_AND_EMBARGO_POLICY`
  - `DATASET_CONSTRUCTION_AUTHORIZATION`
  - `REAL_DATASET_NOT_BUILT`

## Decisions Requested

### D2-final: Session Calendar Implementation

Codex recommendation:

Approve implementation of `cme-globex-metals-research-v1` as the v1 GC
research session calendar.

Required implementation boundaries:

- Use CME Group public references as the authoritative source family.
- Encode normal Globex metals hours, daily maintenance break, holidays,
  special hours, DST behavior, and any required overlays.
- Use the already licensed historical GC observations only as reconciliation
  evidence, not as the schedule authority.
- Create a dated overlay/reconciliation table with source attribution.
- Do not query Databento `status` schema in v1 unless the human separately
  approves the query scope and cost.
- Record a v1 skip decision for Databento `status` schema if this path is
  approved.

Meaning if approved:
Codex can implement and test the GC session calendar, then attempt to satisfy
`SESSION_CALENDAR` without vendor API calls.

### D4-final: Missing Bar Policy

Codex recommendation:

Approve fail-closed row handling:

- OHLCV gaps: exclude affected 30m rows from all training variants.
- Order-flow `volume`, `delta`, `trades` gaps: exclude affected rows from
  the order-flow training variant.
- Do not create a v1 `order_flow_optional` fallback variant.
- Never forward-fill price, volume, delta, trades, labels, or execution truth.
- Emit row-exclusion counts by reason and split in the dataset manifest.

Meaning if approved:
Codex can implement deterministic missing-bar exclusion after the session
calendar exists.

### D5-final: Roll Policy and Contract Identity

Codex recommendation:

Approve a research-only first dataset using the already supplied Databento GC
historical archive identity, while keeping execution truth explicitly blocked.

Operationally:

- Do not use a continuous/stiched GC series as executable truth.
- Treat the current GC archive as the first research dataset source identity.
- Keep live/execution contract mapping out of v1.
- Label/fill truth must remain simulator-only until a later contract-specific
  execution study exists.
- Dataset manifests and model cards must carry
  `contract_identity_status: UNDECLARED_PENDING_RESEARCH`.

Meaning if approved:
Codex can unblock research dataset construction without pretending the result is
directly executable in a broker.

### D6-final: Order-Flow Source Decision

Codex recommendation:

Approve the local Databento GC order-flow archive as a v1 research feature
source, limited to:

- selected member: `gc/GCext_of_1m.parquet`
- allowed columns: `volume`, `delta`, `trades`, `minute`
- forbidden columns/features: `cvd`, cumulative delta, precomputed cumulative
  state, cross-fold cumulative carry
- required exclusion: drop the 2017 damaged aggressor-side window from all
  order-flow training rows

Meaning if approved:
Codex may build order-flow features from `volume`, `delta`, and `trades` only.

### D7-final: Label Contract

Codex recommendation:

Approve outcome-contract labels for the first baseline, not HHLL labels.

Baseline label:

- At each 30m decision bar, evaluate a future-only long/short outcome contract.
- Positive class means target reached before stop.
- Negative class means stop reached before target or target not reached before
  expiry.
- Same-bar target-and-stop ambiguity is excluded from training.
- HHLL files remain auxiliary/reference-only and must not be the primary label.

Codex proposed starter contract for v1 baseline:

- direction candidates: long and short scored separately, then one binary
  training target per configured direction
- risk unit `R`: `ATR(14)` on 30m bars, computed only from closed OHLCV bars
  available at the decision bar
- target distance: `1.0 * R`
- stop distance: `1.0 * R`
- max horizon: `8` bars of 30m, equal to 4 hours
- entry availability: next bar open after the decision bar is closed
- cost/fill policy: zero-cost research baseline, explicitly not executable
  production truth

Meaning if approved:
Codex can implement the real GC label builder and keep production execution
claims blocked.

### D8-final: Split and Embargo Policy

Codex recommendation:

Approve chronological walk-forward only:

- no random split
- train/validation/test ordered by time
- purge labels whose future horizon overlaps validation/test windows
- embargo size: at least the max label horizon, initially `8` bars
- scalers, imputers, encoders, normalizers, and feature transforms fit only
  inside the training window for each fold, then apply forward to validation
  and test windows
- apply the same 2017 damaged-window exclusion to every dataset variant

Meaning if approved:
Codex can build deterministic split manifests and prevent label leakage.

### D9-final: Dataset Construction Authorization

Codex recommendation:

Approve dataset construction only after a future readiness run shows every
pretraining gate satisfied, including `SESSION_CALENDAR`, `MISSING_BAR_POLICY`,
`ROLL_POLICY`, `DATASET_IDENTITY`, `ORDER_FLOW_SOURCE_DECISION`,
`LABEL_CONTRACT`, and `SPLIT_AND_EMBARGO_POLICY`.

The D9 decision record must bind to the assembled dataset-identity manifest and
its deterministic hash. It authorizes one identified dataset build, not a broad
category of future datasets.

Dataset construction must use this tested mask implementation as the sole
permitted v1 order-flow exclusion mechanism:

`trading_system.research.gc_order_flow_row_mask_cumulative_policy.apply_gc_order_flow_training_mask`

Meaning if approved:
Codex may proceed only after the readiness checker reports no remaining
pretraining gates and the exact dataset identity manifest hash is recorded.

## Explicit Non-Approvals

Approving this packet does not approve:

- options features
- macro features
- XAUUSD/GLD proxy mapping
- CVD or cumulative-delta features
- production model promotion
- live trading
- broker execution
- capital allocation

## Suggested Human Response

Reply in chat with:

```text
D2-final approved/rejected/modify: ...
D4-final approved/rejected/modify: ...
D5-final approved/rejected/modify: ...
D6-final approved/rejected/modify: ...
D7-final approved/rejected/modify: ...
D8-final approved/rejected/modify: ...
D9-final approved/rejected/modify: ...
```

This inbox item is not itself an approval record. After the human response,
Codex must create explicit decision records under `agent-exchange/decisions/`
and re-run readiness validation.
