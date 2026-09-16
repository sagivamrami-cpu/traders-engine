# Full-Tree Evidence Capture — Usage Boundary

`FullTreeEvidenceCapture` is an offline recorder. It transforms values supplied
by a caller into a private `FullTreeEvidenceBundle` by running the local,
pinned tree reader once to discover its actual calls. It does not acquire data.

## Required caller contract

The caller supplies an object with:

```python
read(kind, arguments, *, decision_time) -> CapturedValue
```

For every call, it must provide the raw private value, SHA-256 digest,
`observed_at`, `available_at` and `covered_through`. The value has to match the
port's actual artifact kind. Missing values, a late value, malformed digest or
wrong value kind block capture. Do not substitute missing calendar/options data
with an empty response unless that empty response is itself verified source
evidence available at that time.

## Safe sequence

1. An approved, source-identified historical adapter supplies each requested
   value at the decision time.
2. Create `FullTreeEvidenceCapture` with exact `run_id`, `instrument`, pass ID,
   UTC decision time and either `full_tree:house` or `full_tree:strict`.
3. Call `capture_walk()` or, for a private pending plan, `capture_revalidation`.
4. Give the returned private bundle to `FullTreeCausalReplay` and compare its
   payload-free trace digest to the capture receipt.

The source `Walk`, `Plan` and revalidation tuple are discarded during capture;
they are not accepted as inputs and are not placed in the receipt.

## Non-goals and prohibitions

- No filesystem/network fallback, vendor API, data download or raw-data store.
- No implicit symbol mapping, time-zone rule, correction, availability delay or
  empty-data convention.
- No candidate admission, fill, P&L, success/failure label, training row or
  model result.
- No broker or live-trading behavior.

Before a real data adapter is connected, Roee/Yuval must provide its source pin,
digest semantics and private-retention boundary. Sagiv must decide only trading
rules that are actually required by later simulation/management work; this
capture component invents none.
