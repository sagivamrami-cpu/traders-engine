# Full-tree causal provider — approved design and implementation plan

Created at: 2026-09-15T06:02:39Z

Status: REVIEW_REQUESTED

## Decision and scope

The authenticated human approved Option 1: a separate supplied-evidence,
source-faithful full-tree causal provider. The approval covers architecture and
implementation planning, not a claim that runtime implementation is complete.
The binding decision record is
`agent-exchange/decisions/2026-09-15T060239Z-human-full-tree-causal-provider-design.md`.

## Artifacts produced

- Design: `docs/superpowers/specs/2026-09-15-full-tree-causal-provider-design.md`
- Implementation plan: `docs/superpowers/plans/2026-09-15-full-tree-causal-provider.md`

## What the planned component will prove

It will run actual accepted `TreeReader` and, in explicit pending-plan mode,
actual `TreeRevalidation`, using only ordered, point-in-time supplied evidence.
It preserves repeated source reads, independent clocks, raw-port failure timing,
house/strict variant identity, and checkpoint/resume commitments. Public outputs
are observation records only; no raw data, fills, P&L, labels, dataset rows or
model output are introduced.

## Review requested

Review the design and plan for: source-port completeness, timing semantics,
operation ordering, private/public data separation, exact variant boundaries,
revalidation behavior, resume safety and test coverage. Review findings must be
recorded before the component is accepted.

## Explicit boundaries

No runtime code was added by this status update. This does not authorize or
complete data-vendor approval, raw-data retention, economic simulation,
dataset construction, model training/promotion, broker execution, capital
allocation or live deployment. Existing outer-admission review gates remain
independent and unresolved.
