# Agent Exchange Request

Target: Human team — Sagiv for trading rules; Roee/Yuval for source access and broker-contract evidence

Sender: Codex

Created at: 2026-09-14T18:30:00Z

Status: ACTIONABLE

Objective: Supply the minimum decisions and source references required to turn the documented dynamic-management tree into an executable research contract without inventing trading rules.

Scope: J1/J2 of master-plan section 10א only. The fixed original-stop/full-TP1 policy remains the initial control. This request does not ask for live execution, capital allocation, raw-data retention or model promotion.

Required inputs:

1. **Meaning of the thesis state.** For each of HELD, BROKEN and UNVERIFIED, provide:
   - the observations that determine it;
   - relevant timeframe and when the observation is usable;
   - permitted action: HOLD, reduce by a stated fraction, full exit, protect, or no action;
   - behavior when a required observation is unavailable;
   - one LONG and one SHORT example where the result is materially different.

2. **Explicit management triggers.** Define the decision facts for:
   - early exit / soft invalidation before original stop;
   - weakening or exhaustion;
   - reclaim failure and conversion from reversal to continuation;
   - time exit, session close and news window;
   - entry inside an entry zone: initial edge, middle, far edge; and how a missed or partial fill changes the plan;
   - re-entry and ladder/add conditions, including whether the existing `confirmed break + planned before entry` restriction is still desired.

3. **Action priority.** Confirm or amend this proposed ordered scheduler:
   `reconcile fills → emergency → existing protective stop/invalidation → mandatory exit → protect actual remaining quantity → reallocate future remaining quantity → add only if protected and pre-authorized → hold`.
   State how target fills and missing management data enter that order. A performed fill must remain a fact even if the later thesis check fails.

4. **Profile and allocation rules.** State the authoritative allocation for each profile (reaction, balanced, continuation, reversal), including the rule that converts an intended allocation to effective legs when account size or broker lot step is too small. Confirm whether the $1,000 report deliberately uses a different policy from the main catalogue.

5. **Source versions.** Provide a Git bundle, accessible checkout, or commit-containing remote reference for both:
   - `chart-desk` `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` — approved baseline;
   - `chart-desk` `e79c3f854637fcce7b0f9de2efe239c27c259ab6` — revision cited by the management HTML.
   The current local checkout is at `7785534f1afb75d9a154b8118ad088cee9488b42` and lacks both objects.

6. **Future execution contract, when available.** Exact venue:symbol, broker volume minimum/step, price side for entry/exit, stop/freeze constraints, commission/spread/slippage treatment, allowed order types, pending expiry and maximum holding horizon. If not decided, identify it as open rather than supplying example values.

Contracts:

- Every rule must name inputs, unit, timeframe, data availability time, action and fallback.
- “Depends on context” is a valid strategy principle but not an executable rule until the context and allowed action are stated.
- A rule may be marked `LEARNED_CANDIDATE`; then it must not be used as a hard runtime branch before J4/J5 data and validation exist.
- Examples are decision examples, not claims about a live trade or requests for broker activity.

Non-negotiables:

- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation

Deliverables:

- A concise decision record or annotated spreadsheet/document with the six input groups above.
- Source access sufficient for `git show` of both requested commits, or an explicit decision to adopt a different pinned source with rationale.

Verification commands:

```powershell
git -C C:\Users\roeea\sagiv-repos\chart-desk show --no-patch 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9
git -C C:\Users\roeea\sagiv-repos\chart-desk show --no-patch e79c3f854637fcce7b0f9de2efe239c27c259ab6
```

Out of scope:

- Approving any fixed numerical management parameter absent an explicit owner decision.
- Adding broker code, sending orders, retraining a model, or changing the accepted alert engine.
- Treating terminal trade P&L as the label of every management action.

Notes:

The evidence and current-code mapping is in `docs/architecture/MANAGEMENT-SOURCE-MAPPING-INTAKE.md`. The broad architecture and pending J1–J7 work are in master-plan section 10א and the implementation tracker.
