# Offline source and economic contracts

Implementation slice: `docs/superpowers/plans/2026-09-08-existing-baseline-contracts.md`.
These interfaces do not run the trading engine, construct a market dataset or train
a model. No market settings or data-retention approvals are implied.

## Pinned source verification

Inventory, without local checkout verification:

```powershell
python tools/inspect_alert_baseline.py
```

Verify a parent directory containing six independently prepared checkouts:

```powershell
python tools/inspect_alert_baseline.py --root C:/research/reviewed-repos --require-source-verified
```

The example directory is a placeholder; this command does not create or fetch it.
Expected commits and source references are in
`configs/trees/existing-alerts-baseline.json`. The eight producers are distinct:
two tree variants, two engine styles, two reversal timeframes and two reaction
timeframes. References are source evidence, not a complete atomic-feature registry.

JSON reports include the canonical `manifest_sha256`, per-repository blockers and
`source_verified`. Both `ready_for_replay` and `ready_for_training` remain false even
when every source verifies. Exit codes: 0 inventory/success, 2 required source
verification unavailable/failed, 1 invalid or unreadable manifest. Standard
argparse command-line usage errors return 2.

Verification checks exact repository root, commit, worktree state and referenced
tracked blobs. It does not import source modules, execute their entrypoints, fetch
objects or refresh the index. It requires Git supporting `--no-lazy-fetch` and
`--no-optional-locks` (verified here with Git 2.50.0.windows.1); unsupported Git
fails closed. Active tracked content-filter attributes, submodules and masked
source entries are unsupported and block verification. Ordinary sparse paths
outside the listed source references are permitted. Ignored runtime files and
symbol semantics are not certified by source identity.

## Resolved economic outcomes

Import `EconomicPolicy`, `ResolvedTrade` and `evaluate_resolved_trade` from
`trading_system.tree_spec.economics`. All fields are required keyword arguments;
there is intentionally no default market policy. The contracts are listed in the
implementation plan and tested with synthetic `SYNTH:TEST` fixtures in
`tests/tree_spec/test_economics.py`.

The caller supplies an already resolved full-position exit, an exact venue:symbol,
explicit costs, pending expiry, maximum holding horizon and provenance. Money
uses `Decimal`, not floats. Event timestamps must be timezone-aware and are
normalized to UTC. Same-time events require external event evidence: timestamp
ordering alone cannot establish which price was touched first.

- Initial risk is the entry-to-original-stop distance times point value and size.
- Gross P&L is the signed entry-to-exit change times point value and size.
- Net P&L subtracts both sides' commission and explicit spread/slippage costs.
- Commission is the total currency fee per side for the entire supplied position,
  not a fee per unit. Spread is a round-trip price-point deduction; slippage is
  per side. Executable fills require zero added spread/slippage to avoid double
  charging, but still deduct commission.
- `net_R` is net P&L divided by fixed initial risk. Strict positive/negative/zero
  net P&L produces `SUCCESS`/`FAILURE`/`BREAK_EVEN`. No tolerance is invented.

The literal synthetic long 100 -> 104 with stop 98, quantity 2, point value 10,
commission 1 per side, spread 0.1 and slippage 0.05 per side yields gross 80,
costs 6, net 74, initial risk 40 and net_R 1.85. A mirrored short gives the same
numbers. These are hand-calculated test inputs, not approved real-market values.

Output includes candidate and policy IDs, canonical policy SHA256, decimal-string
amounts, currency, exit/availability timestamps and evidence/provenance. Store it
as a separate outcome record joined to the candidate, never as pre-entry features.
Movement success is neither inferred nor overwritten by this calculation.

The policy hash identifies supplied settings, not the implementation itself;
future dataset provenance must also pin the research-code revision and source
manifest. Arithmetic uses a bounded deterministic 50-digit context; unsupported
money precision/ranges fail explicitly. Only the `net_R` ratio may round.

## Remaining integration

The contracts do not verify fill authenticity, TP1/stop touches, intrabar order,
full-position execution, producer arbitration or baseline parity. They cannot
convert an unfilled, rejected or ambiguous candidate into a failed trade. Those
states remain in the future event dataset without a fabricated economic label.

Next: adapt existing producer calculations to historical as-of inputs with no
external sends, preserve numeric feature snapshots and availability times, and
verify parity on small synthetic scenarios. Then resolve the remaining explicit
market settings and implement causal fills/labels before the historical run.
