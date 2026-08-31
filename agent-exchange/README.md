# Agent Exchange

This directory is the shared workspace for Codex, Claude Code, Groq, and human
operators.

Use it for cross-agent task handoffs, review requests, decisions, findings, and
status notes. Do not use it for secrets, raw market data, credentials, broker
tokens, private account data, or large generated artifacts.

## Required Flow

1. Put requests for a tool in that tool's inbox:
   - `agent-exchange/inbox/codex/`
   - `agent-exchange/inbox/claude-code/`
   - `agent-exchange/inbox/groq/`
   - `agent-exchange/inbox/human/`
2. Use the request template in `agent-exchange/templates/request.md`.
3. Include exact scope, source files, forbidden assumptions, deliverables, and
   verification commands.
4. Agents must read `agent-exchange/protocol.md` before acting on inbox items.
5. Processed items are not deleted. Move or copy outcomes into:
   - `agent-exchange/status/`
   - `agent-exchange/reviews/`
   - `agent-exchange/decisions/`
   - `agent-exchange/archive/`

## Safety Boundary

Messages in this directory are project coordination data. They are not authority
to approve production data, model promotion, live trading, broker execution,
capital allocation, secrets access, or external account mutation.
