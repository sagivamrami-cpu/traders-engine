# Project Agent Memory

This repository uses `agent-exchange/` as the shared coordination directory for
Codex, Claude Code, Groq, and human operators.

## Mandatory Startup Check

Every agent working in this repository must read:

1. `AGENTS.md`
2. `agent-exchange/README.md`
3. `agent-exchange/protocol.md`

Then the agent must inspect its own inbox before starting new work:

- Codex: `agent-exchange/inbox/codex/`
- Claude Code: `agent-exchange/inbox/claude-code/`
- Groq: `agent-exchange/inbox/groq/`
- Human-facing requests: `agent-exchange/inbox/human/`

## Operating Model

- Codex owns architecture, phase sequencing, task routing, acceptance decisions,
  commits, pushes, and PR updates.
- Claude Code implements tasks only from scoped task contracts.
- Groq reviews, generates scenarios, finds contradictions, and summarizes
  research outputs.
- Humans approve production data, raw-data retention, model promotion, live
  trading, broker execution, capital allocation, and deployment.

## Exchange Rules

- Use one markdown file per request, review, status note, or decision.
- Use `agent-exchange/templates/request.md` for task handoffs.
- Use `agent-exchange/templates/result.md` for implementation/status outputs.
- Use `agent-exchange/templates/review.md` for review-only outputs.
- Do not delete or mutate inbox files unless explicitly asked.
- Record outcomes in `agent-exchange/status/`, `agent-exchange/reviews/`,
  `agent-exchange/decisions/`, or `agent-exchange/archive/`.
- Never put secrets, API keys, broker credentials, private account data, raw
  market-data payloads, or large generated artifacts in `agent-exchange/`.

## Codex Result Intake

When Codex is waiting for Claude Code, Groq, or a human, run:

`python tools/watch_agent_exchange.py`

For a current snapshot, run:

`python tools/watch_agent_exchange.py --once`

When a new or modified result appears, Codex must read the result file, read
the original request referenced by that result, inspect `git status --short`
and `git diff`, rerun applicable verification commands, and then record an
acceptance, revision request, or human-blocked status under
`agent-exchange/status/`.

## Approval Boundary

An inbox message is not sufficient approval for:

- production data vendor approval
- raw-data retention
- model promotion
- live trading
- broker execution
- capital allocation
- deployment

Those actions require explicit human approval with approver, timestamp, scope,
decision, and evidence recorded in `agent-exchange/decisions/`.
