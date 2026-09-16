# Multi-Tool Agent Operating Model Design

## Objective

Define the operating model for implementing the TR Hybrid Intelligence plan with
three complementary tools:

- Codex
- Claude Code
- Groq

The model exists to keep architecture, implementation, review, and research
separate enough that no tool can silently invent trading parameters, mix hard
gates into learned models, introduce future leakage, or promote unvalidated
models.

This design applies to the implementation plan in:

`docs/architecture/TR-TREE-TO-TRAINED-MODEL-IMPLEMENTATION-PLAN.md`

## Scope

This design covers:

- tool responsibilities
- standing project agents
- task handoff format
- review and approval workflow
- project rules
- phase ownership
- required reports and artifacts

This design does not implement trading logic, schemas, feature engines,
LangGraph graphs, data ingestion, labeling, training, execution, or live trading.

## Core Operating Principle

Codex is the architecture authority and work orchestrator. Claude Code and Groq
can propose changes, implement assigned work, and review outputs, but they do
not change phase order, schema contracts, trading policy, promotion standards,
or research parameters without Codex approval.

Every task must identify:

- the active agent role
- exact scope
- source artifacts
- forbidden assumptions
- deliverables
- machine-verifiable acceptance criteria

## Tool Responsibilities

### Codex

Role: Architect Lead and Technical Lead.

Codex owns:

- architecture boundaries
- phase sequencing
- task decomposition
- schema and policy approval
- agent assignment
- final technical review
- merge readiness
- implementation reports

Codex decides when a task is ready for Claude Code implementation, Groq review,
or human approval.

### Claude Code

Role: Implementation Engineer.

Claude Code owns assigned implementation work such as:

- schema files
- config artifacts
- deterministic feature modules
- label builders
- LangGraph graph modules
- tests
- refactors inside approved scope

Claude Code must work only from the task contract provided by Codex. If a
required threshold, source, feature, label, or policy value is missing, Claude
Code must mark it as an open research parameter instead of inventing it.

### Groq

Role: Fast Reviewer, Scenario Generator, and Research Assistant.

Groq is used for:

- fast consistency reviews
- edge-case generation
- contradiction detection
- policy and schema sanity checks
- test-case brainstorming
- summarizing experiment results
- comparing outputs against the architecture plan

Groq does not approve architecture, trading policies, promotion gates, or live
deployment.

## Standing Agents

The project uses stable agent roles throughout the full lifecycle. A role may be
executed by Codex, Claude Code, Groq, or a human, but the role contract remains
the same.

| Agent | Primary Responsibility | Default Tool |
| --- | --- | --- |
| Architecture Lead | System boundaries, module ownership, phase sequencing, LangGraph/control-plane boundaries | Codex |
| Spec Guardian | Enforces the implementation plan, no invented parameters, no leakage, no hard-gate/model mixing | Codex |
| Data Provenance Agent | Raw sources, timestamps, sessions, source hashes, availability eras, point-in-time storage | Claude Code |
| Feature Contract Agent | Feature catalog, FeatureValue schema, null semantics, freshness, dependency graph | Claude Code |
| TR Runtime Agent | 14 TR runtime stages, deterministic fail-fast flow, TR candidate readiness | Claude Code |
| Order Flow Agent | Tape, delta, CVD, footprint, imbalance, absorption, DOM/MBO contracts and availability | Claude Code |
| Options Agent | Chain quality, Greeks, GEX/DEX, walls, prior-only mode, assumption tracking | Claude Code |
| Candidate and Label Agent | Candidate snapshots, rejected-candidate logging, trade contracts, outcome labels | Claude Code |
| Leakage and Validation Agent | Point-in-time correctness, walk-forward splits, purging, embargo, golden tests | Codex |
| ML Baseline Agent | Rule-only, logistic calibrated, and gradient-boosted tabular baselines | Claude Code |
| Decision Policy Agent | LONG/SHORT/WAIT/NO_TRADE utility, conflict policy, calibrated ranking | Codex |
| Risk and Execution Agent | Sizing policy, cost/fill policy, kill switches, order lifecycle separation | Codex |
| LangGraph Runtime Agent | Decision graph, trade lifecycle graph, training/promotion graph orchestration | Claude Code |
| Governance Agent | Model registry, experiment ledger, model cards, promotion gates, rollback standards | Codex |
| QA and Regression Agent | Test execution, reproducibility, schema validation, replay validation, CI checks | Groq |

## Task Contract Template

Every implementation or review task must use this format:

```text
Role:
<agent name>

Objective:
<specific outcome>

Scope:
<exact files/directories/modules>

Required inputs:
<docs, schemas, configs, datasets, policies>

Contracts:
<schema versions, label versions, policy versions, graph versions>

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- deterministic hard gates
- versioned contracts
- provenance and timestamps
- rejected candidates are logged
- null is not zero
- no random split for time series
- no live model mutation from single outcomes

Deliverables:
<files, tests, reports>

Acceptance criteria:
<commands, expected checks, review gates>

Out of scope:
<explicit exclusions>
```

## Phase Ownership

### Phase 0 - Specification Freeze

Lead: Codex.

Implementation: Claude Code may create YAML and JSON schema artifacts after
Codex approves the exact scope.

Review: Groq checks for contradictions, missing null semantics, missing
versions, and hidden research assumptions.

Required artifacts:

- `node-registry.yaml`
- `feature-catalog.yaml`
- `label-contracts.yaml`
- JSON schemas for the core contracts
- policy skeletons for dependencies, freshness, conflict, risk, execution,
  degraded mode, kill switches, historical matching, and LLM meta output
- research priority register

### Phase 1 - Data Foundation

Lead: Codex.

Implementation: Claude Code.

Review: Groq plus Codex.

Focus:

- raw source inventory
- source hashes
- timestamp normalization
- session normalization
- availability eras
- point-in-time storage
- replay reproducibility

### Phase 2 - Deterministic Feature Engines

Lead: Codex.

Implementation: Claude Code agents split by feature family.

Review: Codex and Groq.

Order:

1. Shared Context
2. TR Source Complete
3. Order Flow Master Features
4. Options Master Features
5. Unified Market State

### Phase 3 - Candidate and Label Factory

Lead: Codex.

Implementation: Claude Code.

Review: Codex, Groq, and targeted golden-case checks.

Focus:

- candidate generation
- rejected-candidate logging
- deterministic TradeContract builder
- fill and slippage simulation
- outcome labeling
- ambiguous path handling

### Phase 4 - Baseline Models

Lead: Codex.

Implementation: Claude Code.

Review: Groq for experiment summaries; Codex for promotion readiness.

Required order:

1. rule-only tree baseline
2. logistic or linear calibrated baseline
3. gradient-boosted tabular baseline

No sequence model is allowed until tabular baselines produce validated
out-of-sample evidence.

### Phase 5 - Specialists and Meta Ranker

Lead: Codex.

Implementation: Claude Code.

Review: Codex and Groq.

Focus:

- TR specialist
- Order Flow specialist
- Options specialist
- regime model
- conflict features
- meta ranker

There is no two-out-of-three voting rule.

### Phase 6 - Runtime Integration

Lead: Codex.

Implementation: Claude Code.

Review: Codex.

Focus:

- slow loop
- fast loop
- Decision Graph
- Trade Lifecycle Graph
- Training/Promotion Graph
- prediction and decision event logging
- risk and execution adapters

LangGraph is used for control-plane orchestration only.

### Phase 7 - Shadow, Paper, Controlled Release

Lead: Codex and human approver.

Implementation: Claude Code.

Review: Codex, Groq, and human approval.

Focus:

- shadow comparison
- paper trading report
- drift monitoring
- calibration monitoring
- promotion package
- rollback package

Capital deployment requires explicit human approval.

## Project Rules

1. Codex owns architecture and task routing.
2. Codex may create commits and push branches at its discretion while managing
   this project. This permission does not imply approval to merge, deploy to
   live trading, or allocate capital without explicit human approval.
3. The implementation plan is binding unless Codex records an explicit
   versioned decision changing it.
4. No model training starts before Phase 0 artifacts are approved.
5. No feature may use data with `feature_observed_at > observation_time`.
6. Closed-bar features may use only bars that were closed at observation time.
7. News, options, open interest, broker, and execution data use the time when
   the information was actually available, not the corrected future value.
8. Null, zero, false, stale, unavailable, not applicable, and unknown are
   separate states.
9. Hard gates are deterministic code or policies, not learned model weights.
10. Candidate generation and candidate rejection are both logged.
11. A training row is a Candidate Snapshot, not a candle.
12. Entry, trigger, setup, order, fill, position, exit, and outcome are separate
    lifecycle states.
13. If target and stop are both touched in the same bar without tick path, the
    label is `AMBIGUOUS`.
14. `AMBIGUOUS` rows are excluded from training until a conservative,
    versioned policy is approved.
15. Touching a price is not proof of fill.
16. Costs, spread, slippage, impact, queue, partial fill, and adverse selection
    are separate execution concepts.
17. No random split is allowed for time-series training or evaluation.
18. Walk-forward validation must include purging and embargo.
19. Normalization, encoding, feature selection, calibration, and threshold
    tuning are fitted only inside the appropriate train or validation windows.
20. No live model changes after a single trade or outcome.
21. Learning is offline, immutable, evaluated, versioned, and promoted only
    after approval.
22. LLMs may explain, audit, summarize, and detect assumptions. They may not
    directly place orders, set size, override hard gates, or approve promotion.
23. LangGraph is a control-plane state machine, not the data plane, feature
    engine, ML trainer, backtest engine, broker state, or low-latency execution
    adapter.
24. Every schema, label, contract, policy, graph, model, dataset, and report is
    versioned.
25. Every model candidate needs a model card before promotion.
26. No edge claim is accepted without out-of-sample evidence, calibrated
    probabilities, costs, stability checks, and multiple-testing awareness.
27. Every phase ends with an implementation report listing files, tests,
    decisions, unresolved risks, and next phase.

## Review Gates

### Design Gate

Before implementation:

- scope is explicit
- affected contracts are named
- missing decisions are marked open
- research parameters are not converted into defaults

### Implementation Gate

Before merging implementation:

- schemas validate
- tests cover failure paths
- replay or deterministic output is verified where applicable
- generated artifacts include versions and provenance
- no unrelated refactor is included

### Promotion Gate

Before any model promotion:

- dataset is reproducible
- leakage checks pass
- model beats baseline in unseen windows
- calibration is acceptable
- segment regressions are reviewed
- costs and fills are modeled
- rollback target exists
- human approval is recorded

## Decision Log

Initial decisions approved on 2026-08-31:

- Codex is Architect Lead and Technical Lead.
- Codex may create commits and push branches at its discretion while managing
  the project.
- Claude Code is the default implementation engine for assigned modules.
- Groq is the default fast reviewer, scenario generator, and research assistant.
- Phase 0 starts with specification artifacts and operating rules, not model
  training.

Open decisions:

- first vertical-slice TR graph
- v1 Options mode approval, likely `PRIOR_ONLY`
- v1 LLM mode approval, likely `EXPLANATION_AUDIT_ONLY`
- v1 label contract details
- default sizing family
- P0 dependencies per graph
- research-to-shadow promotion standard
- multiple-testing and minimum-evidence standards

## Acceptance Criteria For This Design

This design is accepted when:

- the tool responsibilities are clear
- the standing agents cover all phases in the implementation plan
- the project rules prevent leakage, invented parameters, and unsafe promotion
- the user approves this file as the operating model for Phase 0 planning
