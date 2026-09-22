# Human Decision

Approver: Roee

Created at: 2026-09-21T23:03:18Z

Scope: Approve an online Databento metadata and cost preflight for the Sagiv
September 16 Order Flow research window only.

Decision: APPROVED.

Policy:

- Use `GC.v.0` with Databento `GLBX.MDP3` and `continuous` symbol input.
- The request window is 2026-09-16 17:45:00Z to 20:15:00Z.
- The preflight may call Databento metadata, symbology and cost-estimate
  endpoints only. It must not download market data or place a purchase.
- CME GC remains cross-market Order Flow context only. It is not an XAUUSD
  price, execution, fill, stop, target or economic-outcome source.
- This decision does not authorize a data purchase, dataset construction,
  training, live trading or broker execution.

Evidence: Roee explicitly approved `GC.v.0` and then approved the bounded
metadata-and-cost preflight in the active Codex session on 2026-09-22.
