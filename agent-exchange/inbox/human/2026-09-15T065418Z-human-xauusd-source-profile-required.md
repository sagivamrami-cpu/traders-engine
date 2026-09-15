# Human Input Request — XAUUSD historical source profile

Target: Roee, Yuval, Sagiv

Sender: Codex

Created at: 2026-09-15T06:54:18Z

Status:
ACTIONABLE

## Response received — 2026-09-15

The user approved project data access/retention, requested Codex recommendations
on source/provenance, and required information from all branches. Decision:
`agent-exchange/decisions/2026-09-15T073543Z-human-xauusd-access-and-full-information-requirement.md`.

Codex found local XAUUSD data with incomplete coverage and source-semantic issues:
`agent-exchange/reviews/2026-09-15T073543Z-codex-xauusd-source-profile-findings.md`.
The original questionnaire below is retained for context. Technical timestamps,
provenance, provider capabilities and revision policies will be investigated by
Codex; these are not all questions the humans must answer before any progress.
Immediate human inputs narrow to existing OANDA access/export availability and
Sagiv's intended executed Order Flow market/feed. General access permission is
already given and must not be requested again.

## Context

Option A (source-faithful XAUUSD) is approved in
`agent-exchange/decisions/2026-09-15T065418Z-human-full-tree-historical-identity-option-a.md`.
The tree-capture layer is ready, but it intentionally has no vendor or archive
reader.  To create one without inventing market facts, the source profile below
must be supplied.

## Required answer

Roee/Yuval, provide or select:

1. provider/source name and exact historical symbol representing XAUUSD;
2. whether this is the original OANDA source or a formally approved XAUUSD
   source variant;
3. the available date range and supported timeframes/data types (OHLCV,
   tick/quote, volume, order flow, options, news as applicable);
4. UTC timestamp semantics: bar close, publication/availability time, daily
   boundary, trading sessions, holidays and any gaps;
5. correction/revision behavior and how a point-in-time historical view is
   obtained or declared unavailable;
6. a non-secret provenance mechanism: source file/query identifier plus a
   SHA-256 digest for each supplied artifact;
7. confirmation that access and retention of this XAUUSD source are approved,
   or the person who must approve them.

Sagiv, confirm:

8. the source-dependent tree rules that must be **unavailable** when this
   source does not provide their required evidence (for example, a particular
   order-flow/options/news or session input).  Do not substitute an estimate.

## Non-negotiables

- Do not upload credentials, raw market data or account data to agent-exchange.
- No substitute GC series, price adjustment or inferred source mapping.
- Missing capability is recorded explicitly; the original branch determines
  whether the source tree stops. Complete-information dataset eligibility is
  assessed separately under the user's new coverage requirement.
- The later decision above records project access/retention permission. Vendor
  selection, entitlements and coverage still need evidence; no purchase or live
  use is implied.

## Deliverable after the answer

Codex will publish the exact adapter contract and its causal test matrix, then
implementation can begin with caller-supplied, digest-bound historical
evidence.
