# Original pending-plan revalidation over offline ports

Private API: trading_system.tree_replay._vendor.revalidation.Revalidation(source).
Source authority, exact adaptations and remaining boundaries are in
REVALIDATION-SOURCE-CONTRACT.md. Component accepted after independent task/final
reviews and539combinedpassing tests; status213925Z-codex-revalidation records
exact scope. Source audit is tools/check_revalidation_source_parity.py with
required --source-root (parent of retained source checkouts). It does not grant
causal replay or training readiness.

```python
checks = Revalidation(source)
ok, reason, verified = checks.still_valid(pending_trade)
ok, reason, verified = checks.revalidate_pending(pending_trade, now=epoch_seconds)
```

This does not fill, execute, modify the trade, publish an alert or generate a
profit/loss label. It reproduces the source's thesis recheck. `ok=True` does not
mean verified; callers must keep the third value and the original reasons.

The reader composes real TrackerAdmission higher-bias, StretchReader, EmaReader,
admission_matrix structure, default non-auction PVSRA and source session logic.
It consumes the existing read_symbol, fetch_corrected, broker_shape_ok and
deep_exists/deep_bytes ports plus these explicit offline operations:

| Port | Returned evidence / operation |
| --- | --- |
| now_epoch() | Captured per-operation epoch seconds |
| now_timestamp(tz=...) | Captured timestamp expressed in requested timezone |
| now_utc() | Captured aware UTC datetime |
| tree_walk(symbol) | Original Walk-like reply, None or captured exception; full walk binding is not implemented here |
| ensure_shadow_parent(parents=True, exist_ok=True) | Replay-only parent creation operation |
| shadow_open('a', encoding='utf-8') | Text-writer context manager for logical chart-desk/out/revalidation_shadow.jsonl |
| calendar_exists(path) | Captured existence for news-desk/data/ff_calendar.json |
| calendar_text(path) | Captured raw JSON text for that same identity |

No default live/filesystem providers are supplied. Input presence/identity,
observation/publication times, process timezone and caught failures require
separate causal trace/provider evidence. Unknown is not an empty successful
reply. Raw source catches do not certify missing evidence as safe.

The higher bias veto requires a real flip from a send bias favoring the trade;
flat/unread/already-opposing send bias yields distinct labels. A same-direction
extended daily range vetoes. Missing stretch marks unverified; daily fetch
errors are already caught inside StretchReader and reach this reader as absent
stretch, not necessarily as a propagated core exception.

Freshness separately fetches15m/1h/4h with lookback3 and compares each to its own
bar duration in15m-equivalent minutes. Values over120 block/unverified; over20
or unknown allow/unverified. Exact thresholds are inclusive on the allowed
side. Empty frames are skipped; an exception resets age to unknown. This is
the original policy, not a guarantee of complete feed coverage.

EMA/session/stop-distance/structure/vector/news are shadow observations, not
new vetoes. They serialize actual JSON lines with operation timestamps. Writer
failures remain source best-effort. A news event uses a30minute inclusive window;
missing/invalid calendar is reported, not asserted clear. Numeric nonzero
dateline takes precedence except bool; ISO date is the fallback. Raw offset-free
ISO dates use the host timezone, which is NOT approved historical interpretation.
Impact leading whitespace and nonfinite inputs retain raw source semantics.

For pending age below2hours, no tree check is requested. At/above2hours, opposite
direction blocks; unavailable/stopped tree allows but is unverified. Invalid
or missing send time also allows/unverified after still_valid. Default operation
clock is read only after that check; explicit now avoids that extra clock read.

Run tests/tree_replay/test_revalidation.py for current synthetic behavior.
Full tree_walk, causal providers, resolver/caller/effects, economic simulation,
dataset and model work remain separate required parts of the master plan.
