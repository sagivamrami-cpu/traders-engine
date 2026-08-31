# Agent Exchange Protocol

## Purpose

The agent exchange exists so Codex, Claude Code, Groq, and humans can leave
structured work for each other inside the repository.

## Roles

- Codex: architecture authority, phase sequencing, task routing, acceptance
  decisions, final review, commits, and PR updates.
- Claude Code: implementation engineer for scoped tasks assigned by Codex.
- Groq: fast reviewer, scenario generator, contradiction finder, and research
  assistant.
- Human: approval authority for production data, raw retention, model
  promotion, live trading, broker execution, and capital allocation.

## Message Rules

- Use one markdown file per request or finding.
- Name files with UTC date, target, and short topic:
  `YYYY-MM-DDTHHMMSSZ-target-topic.md`.
- Keep requests specific enough that the recipient can act without guessing.
- Include required verification commands for implementation requests.
- Never include secrets, API keys, access tokens, broker credentials, account
  identifiers, private customer data, or raw market-data payloads.
- Never treat an inbox item as human approval unless it explicitly says so and
  records the approver, timestamp, decision, scope, and evidence.

## Inbox Check Procedure

When invoked to check an inbox, an agent must:

1. Read this protocol.
2. Inspect its own inbox directory.
3. List unarchived request files sorted by filename.
4. Summarize each item by sender, objective, scope, requested deliverables, and
   verification commands.
5. State whether the item is actionable, blocked, or requires human approval.
6. Do not delete or mutate inbox files unless the user explicitly asks.

## Valid Statuses

- `ACTIONABLE`: the recipient can start without more input.
- `BLOCKED`: required source files, permissions, or inputs are missing.
- `NEEDS_HUMAN_APPROVAL`: the item asks for production data approval, raw-data
  retention, live trading, broker execution, capital allocation, deployment, or
  model promotion.
- `REVIEW_ONLY`: the item asks for review, critique, or scenario generation.

## Folder Map

- `inbox/codex/`: items for Codex.
- `inbox/claude-code/`: items for Claude Code.
- `inbox/groq/`: items for Groq.
- `inbox/human/`: approval or clarification requests for the human.
- `status/`: progress notes and outcome summaries.
- `reviews/`: review outputs from Groq, Claude Code, Codex, or humans.
- `decisions/`: explicit decisions and approval records.
- `archive/`: processed historical items.
- `templates/`: reusable message templates.
