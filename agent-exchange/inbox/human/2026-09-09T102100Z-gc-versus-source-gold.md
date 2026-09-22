# Agent Exchange Request

Target:
Roee and Sagiv

Sender:
Codex

Created at:
2026-09-09

Status:
ACTIONABLE

Objective:
Resolve the exact gold instrument/rule variant before real-data replay, without
silently applying OANDA spot rules to the approved GC dataset.

Scope:
The first-symbol decision of2026-08-31 approves GC and forbids labelling it XAUUSD
without an approved proxy study. The2026-09-08 design selects pinned repositories
and explicitly does not approve futures/CFD equivalence. Current source gold
pricing/feed/shape contracts use OANDA:XAUUSD. Engineering continues on synthetic
as-of dependencies; this is not a blocker to all local implementation.

Required inputs:
agent-exchange/decisions/2026-08-31T175802Z-human-first-symbol-gc.md
agent-exchange/decisions/2026-09-08T180046Z-user-economic-target-and-baseline.md
docs/architecture/HISTORICAL-LEVELMAP-SOURCE-CONTRACT.md

Deliverables:
Identify whether a pinned Sagiv-approved GC rule variant already exists (provide
the code/config), or whether replay should instead use source-matching XAUUSD
data. A new adaptation/proxy decision must specify its exact scope and evidence;
this request itself approves neither mapping nor new data acquisition/retention.

Verification commands:
No market action requested. Codex will inspect supplied rule/source evidence and
record any explicit human decision under agent-exchange/decisions before use.

Out of scope:
Automatic relabelling, invented GC stop bands, live trading, broker execution,
deployment or new raw-data approval. User was asked asynchronously in chat.
