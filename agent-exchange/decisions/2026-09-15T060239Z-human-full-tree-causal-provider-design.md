# Human Architecture Decision

Approver: User in the authenticated Codex conversation

Created at: 2026-09-15T06:02:39Z

Scope: Architecture and implementation planning for a separate historical
causal provider and replay runner for the already accepted complete tree.

Decision: APPROVED_OPTION_1

Evidence: In response to the Option 1 decision package, the user instructed:
"קבל החלטה, אם לדעתך זה טוב, זה מאושר". Codex selected Option 1 because the
complete tree has independent raw reads and clocks that do not belong in the
existing admission/watch context.

Approved direction:

- Build an isolated supplied-evidence provider for the complete tree.
- Run the source-faithful `TreeReader` and `TreeRevalidation` over that provider.
- Keep `full_tree:house` and `full_tree:strict` as explicit separate variants.
- Preserve point-in-time availability, operation order, repeated reads and
  unavailable/unknown distinctions.
- Commit only artifact identities and digests to replay records/checkpoints.

Excluded from this decision:

- data-vendor acquisition or raw-data retention
- economic simulation, labels, dataset construction or model fitting
- broker execution, capital allocation, deployment or live trading
- acceptance of the pending Outer Admission component

Required next artifacts:

- `docs/superpowers/specs/2026-09-15-full-tree-causal-provider-design.md`
- `docs/superpowers/plans/2026-09-15-full-tree-causal-provider.md`

