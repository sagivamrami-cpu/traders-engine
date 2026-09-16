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
  promotion, live trading, broker execution, capital allocation, and
  deployment.

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
6. Do not delete or mutate inbox files unless the user explicitly asks, except
   that Codex may update the `Status:` field after intake to a terminal state
   such as `ACCEPTED_BY_CODEX` or `REVISION_REQUESTED`.

## Result Output Procedure

When Claude Code, Groq, or Codex finishes assigned work, it must leave a result
message before stopping:

1. Use `agent-exchange/templates/result.md` for implementation or status
   results.
2. Use `agent-exchange/templates/review.md` for review-only results.
3. Write implementation/status outputs to `agent-exchange/status/`.
4. Write review outputs to `agent-exchange/reviews/`.
5. Write human approval records only to `agent-exchange/decisions/`.
6. Include the original inbox request path in the `Request:` field.
7. Include exact verification commands and pass/fail status.
8. Never use a result file as production approval unless it is a human decision
   record with approver, timestamp, scope, decision, and evidence.

## Codex Intake Procedure

Codex receives other tools' outputs by monitoring `agent-exchange/status/`,
`agent-exchange/reviews/`, and `agent-exchange/decisions/`.

1. Run `python tools/watch_agent_exchange.py --once` to inspect current result
   files.
2. When waiting for Claude Code, Groq, or a human, run
   `python tools/watch_agent_exchange.py`.
3. When the watcher reports a new or modified result, Codex must read that file
   and the original request it references.
4. Codex must inspect `git status --short` and `git diff` before accepting any
   implementation result.
5. Codex must independently run the verification commands claimed by the
   sender, or state which commands could not be run.
6. Codex then records one of these outcomes under `agent-exchange/status/`:
   `ACCEPTED_BY_CODEX`, `REVISION_REQUESTED`, `BLOCKED_NEEDS_HUMAN`, or
   `REVIEW_REQUESTED`.
7. Codex may update the original inbox request's `Status:` field to the same
   terminal outcome so other tools do not repeat completed work.

## Live Watch Procedure

The exchange is file-based, so live coordination means polling for new or
modified result files.

- `python tools/watch_agent_exchange.py --once` prints the current result
  snapshot.
- `python tools/watch_agent_exchange.py` initializes a watch state if needed and
  waits for the next new or modified result file.
- `python tools/watch_agent_exchange.py --continuous` keeps watching after each
  event.
- The watcher observes `agent-exchange/status/`, `agent-exchange/reviews/`, and
  `agent-exchange/decisions/` by default.

## Valid Statuses

- `ACTIONABLE`: the recipient can start without more input.
- `BLOCKED`: required source files, permissions, or inputs are missing.
- `NEEDS_HUMAN_APPROVAL`: the item asks for production data approval, raw-data
  retention, live trading, broker execution, capital allocation, deployment, or
  model promotion.
- `REVIEW_ONLY`: the item asks for review, critique, or scenario generation.
- `IMPLEMENTED_AWAITING_CODEX_REVIEW`: an implementation tool has finished and
  Codex must inspect the result.
- `REVIEW_READY_FOR_CODEX`: a review tool has finished and Codex must inspect
  the review.
- `ACCEPTED_BY_CODEX`: Codex independently verified and accepted the result.
- `REVISION_REQUESTED`: Codex found issues and routed changes back to a tool.
- `BLOCKED_NEEDS_HUMAN`: Codex cannot proceed without an explicit human
  decision record.

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
