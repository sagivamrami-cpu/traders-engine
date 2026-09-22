# Original independent claim verifier

Private source projection: `trading_system.tree_replay._vendor.claim_verifier`.
Authority and exact substitutions are in INDEPENDENT-CLAIM-VERIFIER-CONTRACT.md.
This component supplies the original checker, not the full tracker gate or a
historical feed provider. It performs no network, delivery, trade-state or outbox
operation. The source checkout is inspected, never executed by extraction/audit.

Construct `ClaimVerifier(source)` with these explicit local ports:

```python
class Ports:
    def __init__(self, clock, frame_source, json_source):
        self.clock = clock
        self.frame_source = frame_source
        self.json_source = json_source
    def now_utc(self):
        return self.clock.now
    def now_epoch(self):
        return self.clock.now.timestamp()
    def fetch_corrected(self, symbol, timeframe, days):
        return self.frame_source.read(symbol, timeframe, days)
    def fetch_json(self, url, *, timeout):
        return self.json_source.read(url, timeout=timeout)
```

The frame_source/json_source above are caller-supplied offline evidence readers,
not provided public adapters. They must not access live APIs. The URL is request
identity, including original symbol,15m,lookback-derived milliseconds,limit1000
and timeout15. now_utc must be aware UTC; both ports refer to one operation clock.
No system-time default is used. Real causal readers and their traces remain work.

`check_message(text, trade)` returns original Verdict(ok, reason, claim, stale),
whose truthiness is ok. It routes minimum-movement, target, fill and stop messages
through their original calculations; other messages pass as no factual claim.
It catches exceptions into a failed verdict. Direct target/fill/stop methods
retain narrower original exception boundaries and may raise on malformed inputs.

Important limits and preserved differences:

- The caller must already match the message to the correct trade. This checker
  is not the tracker text-to-trade matcher, park/retry, delivery receipt or gate.
- BINANCE reads the independently supplied venue response first, runs the real
  OHLC decoder, and falls back to supplied corrected local bars on None/failure.
  Other symbols use local15m/3 directly. Only original unverified veto is kept;
  successful reads and source tags do not prove historical coverage or quality.
- Its independent fill locator has one-bar send slack and target extrema include
  the fill bar. This intentionally differs from resolver geometry. Neither is
  economic proof of an executable intrabar trade. No resolver helper is reused.
- Target claim_ts and stop resolved_ts-before-claim_ts cap the frame by opening
  timestamps. This alone cannot certify the historical OHLC of the containing
  bar; late publication/partial-bar semantics require the later causal provider.
- Missing data, tape not yet reaching a claim, and an actual contradiction have
  distinct original verdicts. The45min fill grace is not a generic freshness rule.
  Internal _covers accepts some missing/error cases by design; public methods
  still check missing/empty frames. Raw predicates are not coverage certification.
- Minimum messages call the actual DeskSuccess identity proof using the same
  supplied clock. A valid movement proof is not economic profit or model target.

No input trade is intentionally mutated by verification. Source tolerances,
numeric behavior and message parsing are unchanged. Use audit CLI with an
explicit retained source root; its VERIFIED result certifies projection fidelity
only and leaves ready_for_replay/ready_for_training false.

Remaining: causal verifier/lifecycle feeds, full revalidation and effects,
stateful resolver/caller, other producer paths, economic outcomes/dataset/model.
Component acceptance lives in agent-exchange/status, not in this usage note.
