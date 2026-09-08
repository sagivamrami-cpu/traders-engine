# TR Hybrid Intelligence — תוכנית מלאה להמרת עץ המערכת למערכת מודלים מאומנת

> מסמך יישום מחייב עבור מפתחים וכלי LLM. מטרתו לאפשר יישום עקבי של מערכת המסחר בלי לנחש הגדרות, לערבב בין חוקי בטיחות לבין למידה סטטיסטית, או להכניס מידע עתידי לדאטה.

## 0. מטא־נתונים

- **סטטוס:** Implementation Blueprint — לפני מימוש.
- **קהל יעד:** מהנדסי Data/ML/Backend, חוקרי Quant, אנשי Trading וכלי LLM שמיישמים את המערכת.
- **תחום:** המרת TR Hybrid Intelligence Tree למערכת היברידית הכוללת Feature Engines דטרמיניסטיים, מודלים הסתברותיים, Decision Policy, Risk ו־Execution.
- **החלטות סופיות:** `LONG`, `SHORT`, `WAIT`, `NO_TRADE`.
- **עיקרון־על:** העץ אינו נעלם. הוא נשאר חוזה החישוב, הבטיחות ומחזור החיים; המודלים לומדים רק את הקשרים ההסתברותיים בין Market State, Candidate Action ותוצאות עתידיות.
- **אזהרה:** אין לפרוס למסחר חי לפני השלמת Replay, Walk-forward, Shadow ו־Paper Trading ואישור Promotion מפורש.

---

## 1. מטרת המערכת

לבנות מערכת שמקבלת נתוני מסחר היסטוריים וחיים, מחשבת באופן דטרמיניסטי את מצב השוק לפי עץ TR Hybrid Intelligence, יוצרת מועמדי פעולה, ומפעילה מודלים מאומנים כדי להעריך לכל מועמד:

1. הסתברות שה־Target יגיע לפני ה־Stop.
2. הסתברות שה־Stop יגיע לפני ה־Target.
3. הסתברות שהמועמד יפוג ללא הכרעה.
4. תשואה נטו צפויה ב־R ולאחר עלויות.
5. `MAE`, `MFE` וזמן צפוי עד Outcome.
6. הסתברות ואיכות Fill כאשר יש נתוני ביצוע מתאימים.
7. אי־ודאות, איכות כיסוי והאם הקלט נמצא מחוץ להתפלגות האימון.

המערכת תשתמש בתחזיות כדי לדרג מועמדי `LONG` ו־`SHORT`, אך Hard Gates, מגבלות סיכון, Kill Switch, אימות נתונים ו־Execution Constraints יישארו דטרמיניסטיים.

### 1.1 מה המערכת אינה

- אינה מודל End-to-End שמקבל נרות ומוציא פקודת קנייה ללא הסבר.
- אינה מחליפה את העץ ברשת עצבית אחת.
- אינה מלמדת מודל לחקות את החלטות העץ בלבד.
- אינה מעדכנת משקלים חיים לאחר עסקה בודדת.
- אינה ממלאת ערכים חסרים ב־0 ללא משמעות סמנטית.
- אינה מכריחה הצבעה של שני מוחות מתוך שלושה.
- אינה מאפשרת למודל לעקוף Risk, Data Quality או Kill Switch.

---

## 2. הקונטקסט שהמיישם חייב להבין

### 2.1 שלושת המוחות

המערכת מכילה שלושה Producers עצמאיים:

1. **TR / Hybrid Brain** — Context, Cycle, Location, Structure, Behaviour, Vector, Pattern ו־Setup.
2. **Order Flow Brain** — Executed Flow, Delta, CVD, Footprint, Imbalance, Absorption, Exhaustion, DOM/MBO ו־Auction State.
3. **Options Brain** — Chain Integrity, Expirations, OI/Volume, Greeks, GEX/DEX/Vanna/Charm, Walls, Expected Move ו־Volatility Surface.

כל Producer רשאי:

- לייצר Candidate עצמאי.
- לאשר Candidate של Producer אחר.
- לסתור Candidate אחר.
- להיות `UNAVAILABLE` בלי לבטל את שאר המערכת.

אין כלל גלובלי של `2/3 vote`. סתירה היא Feature ומידע, לא שגיאה.

### 2.2 22 שכבות המערכת

המיישם חייב לשמר את כל השכבות הבאות כחוזה ארכיטקטוני:

| שכבה | תחום | תפקיד |
|---|---|---|
| L0 | Data & Provenance | איכות נתונים, מקור, זמן, סשן, freshness וגרסה |
| L1 | Market Context | מצב שוק כללי ו־Shared Context |
| L2 | Trend / MTF | מגמה, ממוצעים, מבנה רב־טיימפריימי |
| L3 | TR / Vector Intelligence | State של TR והיבריד |
| L4 | Location / Levels | מיקום, רמות, Premium/Discount |
| L5 | Session Intelligence | Phase, Daily Open, Brinks מול NY |
| L6 | Cycle Intelligence | Peak, L1/L2/L3, pushes, age, reset |
| L7 | Pattern Intelligence | W/M, V-Shape, Tattoo, RVC/GVC, Block ועוד |
| L8 | Vector Intelligence | Normal/Stopping/Shift, recovery ו־First Vector |
| L9 | Trap / Retest | Trap classification, retest, reclaim/rejection |
| L10 | Order Flow | Executed Flow, Delta/CVD, footprint ו־DOM/MBO |
| L11 | Options | Chain, Greeks, exposures, walls ו־expected move |
| L12 | Cross-Asset / Events | קורלציות, news/event phase ו־macro context |
| L13 | Unified Market State | Snapshot מאוחד, typed ו־versioned |
| L14 | Regime | Trend/Range/Expansion/Contraction/Event/Volatility |
| L15 | Historical Probability | הסתברות מותנית וכיסוי היסטורי |
| L16 | Candidate Generation | יצירת מועמדים מכל Producer |
| L17 | Conflict & Ranking | סתירות, confirmation, ranking והשוואת מועמדים |
| L18 | Timing / Trigger | Trigger, WAIT, expiry ו־entry timing |
| L19 | Risk / Execution | Stop, Target, costs, size, fill ו־order policy |
| L20 | Final Decision | LONG/SHORT/WAIT/NO_TRADE + Trade Contract |
| L21 | Feedback / Learning | outcome logging, replay, research ו־promotion |

### 2.3 14 שלבי TR Runtime

מסלול TR חייב להישמר לפי הסדר הבא:

1. `DATA`
2. `POSITION`
3. `SESSION`
4. `LOCATION`
5. `CYCLE`
6. `CONTEXT`
7. `PATTERN`
8. `VECTOR`
9. `TRAP`
10. `RETEST`
11. `TARGET_RISK`
12. `TRIGGER`
13. `SCALE_IN`
14. `INVALIDATION`

הסדר הוא Fail-fast Runtime של TR, ואינו מחליף את הסדר הסיבתי של עץ הידע:

```text
Context → Cycle → Location → Structure → Behaviour → Vector → Pattern → Setup
```

---

## 3. המיפוי המדויק: Tree → Features + Labels + Constraints

### 3.1 ארבעה סוגי צמתים

כל Node בעץ חייב להיות מסווג לאחד מארבעה סוגים. אין להתחיל Implementation לפני שכל Node קיבל סוג.

| סוג | משמעות | התנהגות במערכת |
|---|---|---|
| `FEATURE_ENGINE` | חישוב מצב שוק | מחזיר Feature typed עם provenance/confidence |
| `HARD_GATE` | תנאי בטיחות או תקינות | מחזיר PASS/BLOCK; אינו נלמד |
| `CANDIDATE_RULE` | מגדיר מתי נוצרת פעולה אפשרית | יוצר Candidate גם אם יידחה בהמשך |
| `OUTCOME_CONTRACT` | מגדיר Entry/Stop/Target/Expiry | מאפשר לחשב Labels ללא עמימות |

### 3.2 מה הופך ל־Features

Examples:

```text
SESSION     → session.phase, session.minutes_from_open
LOCATION    → level.type, distance_atr, premium_discount_percentile
CYCLE       → phase, age_bars, pushes, reset_probability
CONTEXT     → class, ema_stack, deviation, contraction
PATTERN     → type, completeness, quality, direction
VECTOR      → type, strength, recovery_pct, age, source_baseline
TRAP        → class, direction, confidence
RETEST      → state, quality, freshness, reclaim_strength
ORDER_FLOW  → delta, cvd_slope, absorption, imbalance, ofi
OPTIONS     → gamma_regime, walls, expected_move, skew, term_structure
REGIME      → class probabilities, volatility state, event state
RISK        → stop_distance, target_distance, rr, costs, liquidity
```

### 3.3 מה אינו הופך למשקל נלמד

הפריטים הבאים נשארים קוד וחוזים מפורשים:

- data missing/stale/invalid.
- venue/session closed לפי policy.
- position/exposure/max loss limits.
- mandatory Stop.
- kill switch.
- unsupported symbol/feed/timeframe.
- order size cap.
- expired candidate.
- invalid model/schema version.
- breach of deployment policy.

### 3.4 מהו Feature Weight

יש להבדיל בין:

- **Model Parameter** — פרמטר שנלמד באימון.
- **Feature Contribution** — התרומה האפקטיבית של Feature לתחזית ספציפית.
- **Brain Reliability Weight** — אמון דינמי ב־TR/OF/Options לפי Regime וכיסוי.
- **Sample Weight** — כמה דוגמה משפיעה על Loss בזמן אימון.
- **Task Loss Weight** — משקל יחסי בין Labels שונים ב־Multi-task loss.

אין לשמור טבלה ידנית כמו `Vector=20%, Retest=30%` כאמת גלובלית. במודל לא־לינארי התרומה תלויה ב־Context ובאינטראקציות.

---

## 4. יחידת הדאטה: Candidate Snapshot

### 4.1 גרנולריות

שורת אימון אחת אינה נר. שורה אחת היא:

```text
(observation_time, symbol, producer, graph_id, candidate_direction, contract_version)
```

אותו Snapshot יכול לייצר יותר משורה אחת:

```text
TR_LONG
TR_SHORT
OF_LONG
OF_SHORT
OPTIONS_LONG
OPTIONS_SHORT
```

מועמד שלא עבר Decision Threshold עדיין נשמר. אחרת תיווצר Selection Bias.

### 4.2 Candidate ID

```text
candidate_id = hash(
  symbol,
  observation_time_utc,
  producer,
  graph_id,
  direction,
  contract_version
)
```

### 4.3 Point-in-time correctness

כל Feature חייב לעמוד בכללים:

1. `feature_observed_at <= observation_time`.
2. Closed-bar Features משתמשים רק בנרות שנסגרו.
3. News/Options/OI משתמשים בזמן שבו המידע באמת פורסם/היה זמין.
4. אין Backfill שמכניס Snapshot מתוקן לעבר ללא גרסת תיקון מפורשת.
5. Normalization/encoding נלמדים רק מתקופת Train.
6. Null אינו 0.
7. `unknown`, `unavailable`, `not_applicable`, `stale` ו־`false` הם מצבים שונים.

---

## 5. חוזי הנתונים

### 5.1 FeatureValue

```json
{
  "name": "tr.vector.recovery_pct",
  "value": 0.48,
  "dtype": "float",
  "status": "VALID",
  "observed_at": "2026-08-30T12:42:00Z",
  "computed_at": "2026-08-30T12:42:01Z",
  "source": "market-feed-v2",
  "engine_version": "vector-engine-1.0.0",
  "confidence": 0.91
}
```

### 5.2 UnifiedMarketState

```json
{
  "snapshot_id": "...",
  "symbol": "GC",
  "observation_time": "2026-08-30T12:42:00Z",
  "schema_version": "ums-1.0.0",
  "data_quality": "VALID",
  "feature_values": {},
  "availability": {
    "tr": true,
    "order_flow": true,
    "options": false
  },
  "regime": {
    "primary": "EXPANSION",
    "probabilities": {
      "TREND": 0.31,
      "RANGE": 0.09,
      "EXPANSION": 0.56,
      "EVENT": 0.04
    }
  }
}
```

### 5.3 CandidateAction

```json
{
  "candidate_id": "...",
  "snapshot_id": "...",
  "producer": "TR",
  "graph_id": "tr-vshape-retest-long",
  "graph_version": "1.0.0",
  "direction": "LONG",
  "status": "ELIGIBLE",
  "created_at": "2026-08-30T12:42:00Z",
  "expires_at": "2026-08-30T13:02:00Z",
  "reasons": ["V_SHAPE_COMPLETE", "RETEST_CONFIRMED"]
}
```

### 5.4 TradeContract

```json
{
  "contract_version": "tr-contract-1.0.0",
  "entry_policy": "TRIGGER_CLOSE",
  "entry_price": 2410.0,
  "stop_policy": "STRUCTURE_INVALIDATION",
  "stop_price": 2400.0,
  "target_policy": "NEXT_NAMED_LEVEL",
  "target_price": 2432.0,
  "expiry_policy": "MAX_20_BARS",
  "max_holding_bars": 20,
  "commission": 2.4,
  "slippage_model_version": "slippage-1.0.0",
  "fill_policy_version": "fill-1.0.0"
}
```

### 5.5 OutcomeLabel

```json
{
  "candidate_id": "...",
  "label_version": "outcome-1.0.0",
  "outcome_class": "TARGET_FIRST",
  "target_before_stop": 1,
  "stop_before_target": 0,
  "expired": 0,
  "net_return_r": 2.05,
  "mae_r": -0.35,
  "mfe_r": 2.40,
  "time_to_outcome_bars": 11,
  "filled": true,
  "realized_slippage_ticks": 1,
  "label_quality": "HIGH"
}
```

### 5.6 Prediction

```json
{
  "candidate_id": "...",
  "model_id": "candidate-outcome-gbdt",
  "model_version": "0.3.0",
  "feature_schema_version": "ums-1.0.0",
  "p_target_first": 0.74,
  "p_stop_first": 0.21,
  "p_expired": 0.05,
  "expected_net_return_r": 0.82,
  "expected_mae_r": -0.46,
  "expected_mfe_r": 1.88,
  "uncertainty": 0.09,
  "coverage_status": "IN_DISTRIBUTION",
  "calibration_version": "cal-0.2.0"
}
```

### 5.7 FinalDecision

```json
{
  "decision": "LONG",
  "candidate_id": "...",
  "decision_policy_version": "policy-0.2.0",
  "hard_gates_passed": true,
  "expected_value_r": 0.82,
  "risk_size": 0.25,
  "reasons": [
    "POSITIVE_EXPECTED_VALUE",
    "CALIBRATED_CONFIDENCE",
    "RISK_WITHIN_LIMIT"
  ]
}
```

---

## 6. Feature Catalog מחייב

### 6.1 Data & Provenance

- venue, symbol, contract, asset class.
- OHLCV source and volume type.
- tick size, point value, timezone, UTC offset, DST.
- timeframe, closed-bar flag, missing-bar count.
- freshness, latency, correction status.
- feed/schema/engine versions.
- account and broker state availability.

### 6.2 Shared Context

- Session/Daily/Weekly/Anchored VWAP distance, slope, reclaim/rejection.
- POC, VAH, VAL, HVN/LVN, value migration and acceptance/rejection.
- level type, width, source, age, touches, reactions, liquidity and confluence.
- Daily Open side, distance, crosses, reclaim/rejection and time since open.
- Premium/Discount continuous percentile.
- DXY, ES/SPX, yields, gold, oil, yen, carry, BTC/alts correlation/beta/lead-lag כאשר רלוונטי.
- Event phase: none/scheduled/pre-event/window/shock/post/normalization.

### 6.3 TR / Hybrid

- Context: deviated/consolidating/contracted.
- EMA stack/slope/spacing and multi-timeframe alignment.
- Cycle: peak/L1/L2/L3, pushes, age, duration, reset, parent/child.
- Location and approach side.
- Structure and Behaviour.
- V-Shape displacement/return/speed/extreme/mean deviation.
- Speed of Tape continuous velocity/acceleration/deceleration.
- Peak Formation state.
- Vector: normal/stopping/shift; body/wick/volume/baseline.
- Vector recovery: untouched/continuous percentage/full.
- First Vector relative to 50/200/800.
- W/M, Tattoo, RVC/GVC, Block, Brinks and approved Graphs.
- Trap direction/classification.
- Retest state, freshness and quality.
- Eyes/Inventory and Market Memory.

### 6.4 Order Flow

- feed provenance and availability.
- tape rate, size bursts and acceleration.
- aggressor buy/sell classification confidence.
- delta by bar/price/session.
- CVD level/slope/divergence/reset policy.
- footprint bid×ask and delta per price.
- imbalance and stacked imbalance.
- absorption and exhaustion.
- failed auction and sweep.
- displayed DOM pull/stack separated from executed flow.
- MBO/iceberg evidence.
- spoofing/layering suspicion only, never certainty.
- OFI and microprice.
- TPO/profile/auction state.
- price/flow divergence.
- spread, depth, impact, queue and fill estimates.

### 6.5 Options

- chain integrity, stale/crossed quote rates and missing legs.
- expiry buckets: 0DTE/weekly/monthly/event.
- strike-relative OI and volume.
- put/call measures segmented by expiry/strike/moneyness.
- IV surface, skew, term structure and expected move.
- Delta/Gamma/Vanna/Charm by strike/expiry.
- GEX/DEX and explicit sign/inventory assumptions.
- gamma flip/zero-gamma estimate with uncertainty.
- call/put walls, pinning and wall migration.
- dealer-flow proxy provenance.
- spot distance and time to expiry.

### 6.6 Availability Masks

לכל משפחת Features יש ליצור:

```text
is_available
is_stale
quality_score
source_version
```

אין לאמן מודל אחד כאילו 16 שנות Price, Order Flow ו־Options מכילות אותה איכות.

---

## 7. Labels

### 7.1 Label ראשי לגרסה הראשונה

```text
outcome_class ∈ {TARGET_FIRST, STOP_FIRST, EXPIRED}
```

גרסה בינארית מותרת רק אם מדיניות Expiry מוגדרת:

```text
target_before_stop = 1 if TARGET_FIRST else 0
```

מומלץ לשמור את שלושת המצבים גם אם מודל הבסיס בינארי.

### 7.2 Labels משניים

- `net_return_r` לאחר commission/slippage/fill.
- `mae_r`.
- `mfe_r`.
- `time_to_outcome_bars`.
- `filled`.
- `realized_slippage_ticks`.
- `thesis_invalidated_before_outcome`.

### 7.3 כללי Labeling

1. Labels מחושבים רק אחרי הקפאת Snapshot ו־Trade Contract.
2. Entry/Stop/Target/Expiry חייבים להיות versioned.
3. אם באותו bar נוגעים גם ב־Stop וגם ב־Target ואין tick path, Label הוא `AMBIGUOUS`, לא הצלחה.
4. `AMBIGUOUS` אינו נכנס ל־Train עד שמוגדרת policy שמרנית ואחידה.
5. Fill של Limit Order אינו מובטח רק משום שהמחיר נגע בו.
6. עלויות ושינויי contract/tick/point value הם point-in-time.
7. Label builder חייב להיות deterministic ו־idempotent.

---

## 8. ארכיטקטורת המודלים

### 8.1 Baseline מחייב

יש להתחיל בשלושה Baselines לפני Deep Learning:

1. Rule-only tree baseline.
2. Logistic/linear calibrated baseline.
3. Gradient-boosted tabular baseline.

רק אם מודל Sequence מוכיח שיפור Out-of-sample ניתן להוסיף Transformer/RNN/Temporal model.

### 8.2 Action-conditional Candidate Model

המלצה לגרסה הראשונה:

```text
score = Model(UnifiedMarketState, CandidateAction, TradeContract)
```

אותו מודל יכול להעריך `LONG` ו־`SHORT` בנפרד:

```text
Model(state, action=LONG, long_contract)
Model(state, action=SHORT, short_contract)
```

המודל אינו בוחר כיוון לפני ההערכה. הוא מעריך את שני המועמדים ואז Decision Policy משווה ביניהם.

### 8.3 Specialist Models

לאחר Baseline:

```text
TR Specialist       → prediction_tr
Order Flow Specialist → prediction_of
Options Specialist  → prediction_options
Regime Model        → regime probabilities
Execution Model     → fill/slippage probabilities
Meta Ranker         → final candidate ranking
```

כל Specialist מקבל Availability Mask ונבחן בנפרד. אין להפוך Missing Brain להסתברות 0.

### 8.4 Meta Model Inputs

- specialist probabilities and expected returns.
- specialist calibration/reliability by regime.
- disagreement type and magnitude.
- data availability and quality.
- candidate/graph/producer identity.
- risk geometry and costs.
- regime probabilities.
- coverage/OOD indicators.

### 8.5 Decision Policy

```text
eligible_actions = actions where all hard gates pass

utility(action) =
    expected_net_return_r
  - lambda_risk * risk_penalty
  - lambda_uncertainty * uncertainty
  - lambda_cost * execution_cost

decision = argmax(utility(action))
```

אם אין Candidate שעובר threshold, calibration, coverage ו־minimum EV:

```text
NO_TRADE
```

אם Candidate תקף אך Trigger/Timing עדיין לא הושלם:

```text
WAIT
```

---

## 9. Loss Functions ועדכון משקלים

### 9.1 Classification

ל־`target_before_stop`:

```text
Binary Log Loss / Binary Cross Entropy
```

ל־`TARGET_FIRST/STOP_FIRST/EXPIRED`:

```text
Multiclass Cross Entropy
```

### 9.2 Regression

- `net_return_r`: Huber או Quantile Loss.
- `MAE/MFE`: Quantile Regression עדיף על נקודה יחידה.
- `time_to_outcome`: Survival/Time-to-event objective כאשר censoring קיים.
- candidate ranking: pairwise/listwise ranking objective.

### 9.3 Multi-task Loss

```text
total_loss =
    w_class * classification_loss
  + w_return * return_loss
  + w_mae * mae_loss
  + w_mfe * mfe_loss
  + w_time * time_loss
  + regularization
```

`w_*` הם Task Weights, לא Feature Weights. יש לתעד כיצד נבחרו ולא לכוונן אותם על Final Holdout.

### 9.4 אין Online Mutation

עסקה בודדת אינה משנה מודל Live. התהליך היחיד המותר:

```text
Outcome Event
→ Immutable log
→ Offline training dataset
→ Candidate model version
→ Walk-forward evaluation
→ Shadow comparison
→ Promotion Gate
→ Approved deployment
```

---

## 10. בניית הדאטה מ־16 שנות מסחר

### 10.1 שלבי Pipeline

1. Ingest raw sources ללא שינוי.
2. Normalize timestamps/symbols/contracts/sessions.
3. Validate quality and construct availability intervals.
4. Build point-in-time bars/ticks/chains.
5. Compute deterministic Features.
6. Persist Unified Market State.
7. Generate all eligible Candidates, כולל rejected candidates.
8. Freeze Trade Contract.
9. Simulate fill and future path.
10. Build Outcome Labels.
11. Create immutable dataset manifest.
12. Run leakage and reproducibility tests.

### 10.2 Dataset Manifest

כל Dataset חייב לכלול:

```json
{
  "dataset_id": "candidate-dataset-...",
  "created_at": "...",
  "raw_source_hashes": {},
  "feature_schema_version": "...",
  "label_version": "...",
  "contract_versions": [],
  "date_ranges": {},
  "symbols": [],
  "availability_summary": {},
  "row_count": 0,
  "excluded_rows": {},
  "code_commit": "..."
}
```

### 10.3 Availability Eras

יש לחלק את 16 השנים ל־Eras לפי זמינות בפועל, למשל:

- Price-only era.
- Price + reliable volume era.
- Tick/Order Flow era.
- Options-chain era.
- Full live-like era.

אין לאמן Full Brain Model על שנים שבהן Features חיוניים שוחזרו באופן ספקולטיבי.

### 10.4 Futures Rollover ו־Contract Metadata

אם מדובר בחוזים עתידיים:

- לשמור raw contract ו־continuous series בנפרד.
- לא להשתמש במחיר adjusted לקביעת Fill אמיתי.
- rollover policy חייבת להיות versioned.
- volume/open-interest based rollover משתמש רק במידע שהיה ידוע אז.
- tick size, point value ו־session changes הם point-in-time.

---

## 11. Validation ללא Leakage

### 11.1 Split

אסור Random Split רגיל. יש לבצע Walk-forward כרונולוגי:

```text
Train → Calibration → Validation → Test
```

החלונות נעים קדימה. Final Holdout נשמר סגור עד הקפאת המערכת.

### 11.2 Purging ו־Embargo

- דוגמאות שחלון ה־Outcome שלהן חופף לגבול Split יוסרו.
- Embargo יוגדר לפי maximum label horizon.
- Normalization, feature selection, calibration ו־threshold tuning יבוצעו רק בתוך Train/Validation המתאימים.

### 11.3 מדדי ML

- Log Loss.
- Brier Score.
- Calibration curve / ECE.
- PR-AUC ו־ROC-AUC לפי התאמה ל־class balance.
- confusion matrix לפי threshold.
- coverage and abstention rate.
- metrics by producer/graph/regime/symbol/era.

### 11.4 מדדי מסחר

- net expectancy in R.
- realized costs and slippage.
- drawdown.
- hit rate ביחס ל־RR.
- MAE/MFE distributions.
- turnover and exposure.
- tail loss and event-period performance.
- performance by regime and data-quality bucket.

אין לקדם מודל על בסיס Total PnL בלבד.

### 11.5 כיול

אם המודל מחזיר 70%, כ־70% מהדוגמאות הדומות צריכות להצליח Out-of-sample. Thresholds נקבעים על הסתברויות מכוילות ולא על raw score.

---

## 12. Runtime מלא

### 12.1 Slow Loop

- refresh shared context.
- compute multi-timeframe state.
- refresh options chain and events.
- update levels, profiles, cycles and market memory.
- update regime and model availability.

### 12.2 Fast Loop

1. validate feed freshness.
2. update closed/active bar state לפי policy.
3. update TR/OF fast Features.
4. update active Candidates.
5. score LONG and SHORT Candidates.
6. apply conflict/ranking.
7. apply Risk/Execution constraints.
8. emit `LONG/SHORT/WAIT/NO_TRADE`.
9. persist Prediction and Decision events.

### 12.3 Order Lifecycle

```text
CANDIDATE
→ SCORED
→ APPROVED
→ ORDER_INTENT
→ SUBMITTED
→ ACKNOWLEDGED
→ PARTIALLY_FILLED / FILLED / REJECTED / CANCELLED
→ POSITION_OPEN
→ MANAGED
→ EXITED
→ OUTCOME_RECORDED
```

Order אינו Fill. לאחר Fill יש לבצע Revalidation של thesis, risk ו־invalidation.

### 12.4 Active Position Monitoring

- structure/pattern/vector invalidation.
- adverse recovery and failed continuation.
- flow and regime change.
- event/kill-switch changes.
- time/expiry.
- position/account risk.
- scale-in eligibility with total exposure caps.

---

## 12A. LangGraph כמכונת המצבים של המערכת

### 12A.1 החלטת ארכיטקטורה

מותר ומומלץ להשתמש ב־LangGraph עבור **Control Plane / Workflow Orchestration** של המערכת. LangGraph אינו משמש כתחליף ל:

- חישובי Features וקטוריים/מספריים.
- אחסון Market Data.
- Training Loop של מודלי ML.
- Backtest engine.
- execution adapter בעל דרישות latency קשיחות.
- broker-native order state.

החלוקה המחייבת:

```text
Data Plane
  raw data → feature engines → feature store → model inference

Control Plane (LangGraph)
  state transitions → gates → candidate routing → scoring orchestration
  → decision → approval → execution intent → monitoring → audit
```

### 12A.2 שלוש מכונות מצבים שונות

אין לערבב בין:

1. **Decision Graph** — Data → Features → Candidates → Scores → Decision.
2. **Trade Lifecycle Graph** — Candidate → Order → Fill → Position → Exit.
3. **Training/Promotion Graph** — Dataset → Train → Evaluate → Shadow → Approve → Deploy.

יש לממש אותן כשלושה Graphs נפרדים עם schemas ברורים. ה־Decision Graph יכול להזניק את Trade Lifecycle Graph; Outcome Event יכול להזניק תהליך Research/Training, אך לא לשנות Live Model ישירות.

### 12A.3 Decision Graph מוצע

```text
START
  ↓
load_snapshot
  ↓
data_gate ──BLOCK──→ no_trade
  ↓ PASS
build_shared_context
  ↓
┌───────────────────────────────────────┐
│ tr_subgraph                           │
│ order_flow_subgraph    (parallel)     │
│ options_subgraph                     │
└───────────────────────────────────────┘
  ↓
unify_market_state
  ↓
classify_regime
  ↓
generate_candidates
  ↓
┌───────────────────────────────────────┐
│ score_long_candidates                 │
│ score_short_candidates   (parallel)   │
└───────────────────────────────────────┘
  ↓
resolve_conflicts_and_rank
  ↓
risk_gate ──BLOCK──→ no_trade
  ↓ PASS
timing_router
  ├── WAIT       → persist_decision → END
  ├── NO_TRADE   → persist_decision → END
  └── ACTIONABLE → build_trade_contract
                         ↓
                   approval_policy
                    ├── REVIEW → human_interrupt
                    └── PASS
                         ↓
                   emit_order_intent
                         ↓
                        END
```

### 12A.4 State Schema

Graph State חייב להכיל references ו־JSON-serializable summaries, לא DataFrames ענקיים או raw tick history.

```python
from typing import Literal, TypedDict

Decision = Literal["LONG", "SHORT", "WAIT", "NO_TRADE"]

class TradingGraphState(TypedDict, total=False):
    run_id: str
    symbol: str
    observation_time: str
    snapshot_id: str
    schema_version: str

    data_quality: dict
    shared_context_ref: str
    tr_state: dict
    order_flow_state: dict
    options_state: dict
    availability: dict
    unified_state_ref: str
    regime: dict

    candidates: list[dict]
    predictions: list[dict]
    conflicts: list[dict]
    ranked_candidates: list[dict]

    hard_gate_results: list[dict]
    decision: Decision
    decision_reasons: list[str]
    trade_contract: dict | None
    order_intent_id: str | None

    model_versions: dict
    engine_versions: dict
    errors: list[dict]
```

### 12A.5 Subgraphs

יש לממש Subgraph נפרד לכל מוח:

```text
TRSubgraph
OrderFlowSubgraph
OptionsSubgraph
```

חוזה משותף לכל Subgraph:

```text
Input:
  snapshot_id, observation_time, symbol, availability, engine_versions

Output:
  producer_state, candidates, quality, reasons, producer_version
```

כאשר Producer אינו זמין הוא מחזיר:

```json
{
  "status": "UNAVAILABLE",
  "candidates": [],
  "reasons": ["NO_HISTORICAL_CHAIN"]
}
```

אין לנתב ל־`NO_TRADE` אוטומטית אלא אם אותו Producer הוא Dependency מחייב של Graph ספציפי.

### 12A.6 Conditional Edges

Conditional Edges מתאימים ל:

- data quality pass/block/degraded.
- candidate exists/none.
- risk pass/block.
- timing actionable/wait/expired.
- decision long/short/wait/no-trade.
- approval required/not required.
- order ack/fill/reject/cancel.
- thesis valid/invalidated.

ה־Edge מנתב בלבד. חישוב מורכב חייב להתבצע ב־Node שניתן לבדוק, לתעד ולגרס.

### 12A.7 Reducers ו־Parallelism

TR, Order Flow ו־Options יכולים לרוץ במקביל כאשר כולם קוראים Snapshot immutable. עדכוני `candidates`, `predictions`, `hard_gate_results` ו־`errors` דורשים reducer שמאחד רשימות באופן דטרמיניסטי.

אחרי parallel fan-out יש לבצע fan-in אל `unify_market_state` או `resolve_conflicts_and_rank`. סדר התוצאות ייקבע לפי stable key ולא לפי זמן סיום Node.

### 12A.8 Persistence ו־Thread IDs

יש להשתמש ב־Checkpointer עבור workflows ארוכים, approvals ו־recovery. Thread ID חייב להיות domain-specific:

```text
decision:{symbol}:{observation_time}:{run_id}
trade:{account}:{position_id}
training:{dataset_id}:{experiment_id}
```

Checkpoint אינו System of Record יחיד. Prediction, Decision, Order ו־Outcome Events נשמרים גם ב־event store ייעודי.

### 12A.9 Idempotency

כל Node עם Side Effect חייב לקבל idempotency key:

- `persist_decision`: `decision_id`.
- `emit_order_intent`: `order_intent_id`.
- `submit_order`: broker client order id.
- `record_outcome`: `candidate_id + label_version`.
- `deploy_model`: `model_version + environment`.

Replay/Resume אסור שייצר הוראה כפולה.

### 12A.10 Human-in-the-loop

Interrupt מתאים ל:

- מעבר ראשון מ־Shadow ל־Paper.
- Promotion של Model Version.
- deployment עם Capital.
- חריגה מסיכון מאושר.
- action שדורש manual approval לפי policy.

אין להשתמש ב־LLM approval כתחליף לאישור אנושי כאשר policy מחייב Human.

### 12A.11 Latency Boundary

LangGraph מתאים ל־workflow stateful, durable ו־auditable. אין להכניס אותו למסלול per-tick אם Budget ה־latency אינו מאפשר serialization/checkpoint/scheduling overhead.

יישום מומלץ:

```text
Fast numeric service:
  ticks → incremental features → model score

LangGraph orchestration:
  bar close / candidate event / order event / position event
```

ה־Fast Service מפרסם Event או reference; LangGraph מנהל את המעבר העסקי. אם נדרש ultra-low-latency execution, routing/risk pre-trade הקריטי יפעל בתוך שירות דטרמיניסטי מקומי וידווח לגרף.

### 12A.12 Training Graph

LangGraph רשאי לארגן את תהליך האימון, אך Trainer עצמו נשאר קוד ML רגיל:

```text
START
→ validate_dataset_manifest
→ leakage_tests
→ train_baselines
→ train_candidate_models
→ calibrate
→ walk_forward_evaluate
→ compare_with_champion
→ produce_model_card
→ human_promotion_interrupt
→ register_candidate / reject
→ END
```

אין Edge מ־`record_outcome` ישירות ל־`update_live_weights`.

### 12A.13 Trade Lifecycle Graph

```text
CANDIDATE_APPROVED
→ ORDER_INTENT
→ SUBMITTING
→ ACKNOWLEDGED
├── REJECTED → CLOSED
├── CANCELLED → CLOSED
├── PARTIALLY_FILLED → REVALIDATE → MANAGE/CANCEL_REMAINDER
└── FILLED → REVALIDATE → POSITION_OPEN
                    ↓
               MONITORING
                ├── HOLD
                ├── SCALE_IN
                ├── REDUCE
                └── EXIT
                    ↓
              OUTCOME_RECORDED
                    ↓
                   END
```

Broker events הם מקור האמת למצב Order/Fill. LangGraph משקף ומנהל את ה־workflow, אך אינו מניח Fill על בסיס מחיר בלבד.

### 12A.14 Tests ספציפיים ל־LangGraph

- route tests לכל Conditional Edge.
- reducer determinism under parallel completion order.
- checkpoint/resume בלי side effect כפול.
- replay עם same versions מייצר same decision.
- unavailable subgraph אינו מוחק תוצאות אחרים.
- human interrupt resume approve/reject/edit.
- broker reject/partial-fill/cancel paths.
- model unavailable/timeout fallback.
- stale snapshot before order intent.
- schema/version mismatch routes to `NO_TRADE`.

### 12A.15 References

- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- Graph API: https://docs.langchain.com/oss/python/langgraph/graph-api
- Persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- Subgraphs: https://docs.langchain.com/oss/python/langgraph/use-subgraphs

### 12A.16 מסקנה מחייבת

LangGraph הוא מכונת המצבים והאורקסטרציה של המערכת, לא המודל המאומן. ה־Features והמודלים מופעלים בתוך Nodes או בשירותים חיצוניים; Edges מנהלים מעברים; Checkpoints מאפשרים resume/audit; Hard Gates נשארים פונקציות דטרמיניסטיות; Training ו־Promotion מנוהלים בגרף נפרד.

---

## 13. Model Registry ו־Governance

כל Model Version חייב לכלול:

- model id/version/type.
- training code commit.
- dataset manifest id.
- feature schema and label versions.
- hyperparameters and seed.
- training/validation/test ranges.
- metrics overall and by segment.
- calibration artifact.
- decision thresholds.
- supported symbols/timeframes/producers.
- known failure modes.
- approval status and approver.
- rollback target.

### 13.1 Promotion Gate

מודל מועמד עובר רק אם:

1. dataset reproducible.
2. no leakage checks pass.
3. performance exceeds rule baseline in multiple unseen windows.
4. calibration acceptable.
5. no catastrophic segment regression.
6. costs and fills modeled.
7. shadow behavior explainable.
8. rollback tested.
9. explicit human approval recorded.

### 13.2 Drift

לנטר:

- feature distribution drift.
- prediction drift.
- calibration drift.
- label/outcome drift.
- null and availability rates.
- dead gates and never-triggered Graphs.
- performance by regime/producer/era.

Drift אינו מפעיל אימון חי אוטומטי. הוא יוצר Research/Training Request.

---

## 14. מבנה ריפו מומלץ

```text
trading-system/
├── README.md
├── docs/
│   ├── architecture/
│   │   ├── tree-to-model-plan.md
│   │   ├── node-taxonomy.md
│   │   └── runtime-state-machine.md
│   ├── data/
│   │   ├── feature-catalog.md
│   │   ├── label-contracts.md
│   │   └── point-in-time-policy.md
│   └── governance/
│       ├── model-promotion.md
│       └── research-parameters.md
├── schemas/
│   ├── feature_value.schema.json
│   ├── unified_market_state.schema.json
│   ├── candidate_action.schema.json
│   ├── trade_contract.schema.json
│   ├── outcome_label.schema.json
│   ├── prediction.schema.json
│   └── final_decision.schema.json
├── src/
│   ├── ingestion/
│   ├── normalization/
│   ├── features/
│   │   ├── shared/
│   │   ├── tr/
│   │   ├── order_flow/
│   │   └── options/
│   ├── candidates/
│   ├── labeling/
│   ├── datasets/
│   ├── models/
│   ├── evaluation/
│   ├── decision_policy/
│   ├── risk/
│   ├── execution/
│   └── monitoring/
├── configs/
│   ├── graphs/
│   ├── contracts/
│   ├── datasets/
│   └── models/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── leakage/
│   ├── replay/
│   └── golden/
└── artifacts/  # metadata only; large data/models stored externally
```

---

## 15. סדר המימוש

### Phase 0 — Specification Freeze

**מטרה:** להפוך כל מושג בעץ לחוזה חד־משמעי.

Deliverables:

- Node registry עם type לכל Node.
- Feature Catalog v1.
- Label Contract v1.
- Candidate/Trade Contract schemas.
- רשימת Research Parameters לא פתורים.

Acceptance:

- אין Feature ללא unit, source, timestamp, null semantics ו־version.
- אין Label ללא Entry/Stop/Target/Expiry.
- אין Hard Gate שממומש כמשקל.

### Phase 1 — Data Foundation

Deliverables:

- raw inventory and source hashes.
- time/symbol/session normalization.
- quality reports and availability eras.
- point-in-time storage.

Acceptance:

- replay של interval זהה מייצר אותם נתונים.
- missing/stale/correction statuses נשמרים.

### Phase 2 — Deterministic Feature Engines

סדר מומלץ:

1. Shared Context.
2. TR Source Complete.
3. Order Flow Master Features.
4. Options Master Features.
5. Unified Market State.

Acceptance:

- unit/golden tests לכל Feature.
- no-future-data tests.
- provenance בכל ערך.

### Phase 3 — Candidate and Label Factory

Deliverables:

- Candidate generator לכל Graph/Producer.
- deterministic Trade Contract builder.
- fill/slippage simulator.
- outcome label builder.
- rejected-candidate logging.

Acceptance:

- Labels reproducible.
- ambiguous paths flagged.
- all candidates tracked to outcome/rejection reason.

### Phase 4 — Baseline Models

Deliverables:

- rule baseline.
- logistic calibrated model.
- gradient-boosted model.
- LONG/SHORT action-conditional scoring.
- calibration and evaluation report.

Acceptance:

- model beats naive and rule baselines Out-of-sample on agreed metrics.
- no segment shows unacceptable hidden failure.

### Phase 5 — Specialists and Meta Ranker

Deliverables:

- TR/OF/Options specialist reports.
- regime model.
- conflict features.
- meta candidate ranker.

Acceptance:

- no 2/3 vote.
- unavailable brain handled explicitly.
- reliability segmented by regime and era.

### Phase 6 — Runtime Integration

Deliverables:

- slow/fast loops.
- prediction/decision event logging.
- risk and execution adapters.
- full lifecycle state machine.

Acceptance:

- deterministic replay equals recorded decisions for same versions.
- order/fill distinction tested.
- Kill Switch and rollback tested.

### Phase 7 — Shadow, Paper, Controlled Release

Deliverables:

- shadow comparison dashboard.
- paper trading report.
- drift/calibration monitoring.
- promotion package.

Acceptance:

- sufficient sample coverage across relevant regimes.
- no unresolved high-severity failure.
- explicit approval before capital deployment.

### Phase 8 — Optional Offline RL

Offline RL נשקל רק לניהול רציף של Entry/Scale-in/Reduce/Exit, לאחר שקיים Simulator אמין. הוא אינו מחליף Hard Gates ואינו שלב ראשון.

---

## 16. בדיקות חובה

### 16.1 Unit

- each feature calculation.
- null/status semantics.
- timezone/DST/session boundaries.
- contract and label calculations.

### 16.2 Leakage

- feature timestamp > observation time must fail.
- normalization fit on future data must fail.
- revised data injected into past must fail.
- overlapping labels across split must fail.

### 16.3 Golden Cases

ליצור fixtures ידניים לכל Setup מאושר:

- valid LONG.
- valid SHORT.
- WAIT pending retest.
- NO_TRADE due data.
- NO_TRADE due risk.
- conflict between brains.
- missing OF/options.
- target/stop same-bar ambiguity.
- partial fill and revalidation.
- invalidation after fill.

### 16.4 Replay

- same raw data + same versions = same snapshots/candidates/labels/predictions/decisions.
- version change produces explicit diff, never silent mutation.

---

## 17. Research Parameters שאסור להמציא

כל ערך הבא נשאר configurable/research עד שיש Evidence:

- exact vector thresholds and baseline.
- pattern quality formulas.
- V-Shape timing and completion thresholds.
- retest zone width and expiry.
- cycle reset rules.
- regime thresholds.
- imbalance/absorption/iceberg thresholds.
- gamma/dealer sign assumptions.
- minimum probability/EV thresholds.
- calibration method and window.
- loss weights and sample weighting.
- recency weighting.
- slippage/fill assumptions.
- risk size and exposure limits.

כל Research Parameter חייב לכלול:

```text
parameter_id
hypothesis
allowed_range
source/evidence
experiment_id
status
approved_version
```

---

## 17A. External Architecture Review — ממצאים, הכרעות ו־Edge

פרק זה משלב ביקורת ארכיטקטונית חיצונית על התוכנית. הממצאים אינם משנים אוטומטית את המערכת; הם הופכים ל־Decision Items ולחוזי יישום שרועי והצוות יכולים לאשר, לדחות או לשנות. כל בחירה חייבת להיות versioned ומגובה ב־Evidence.

### 17A.1 מסקנת הביקורת

עקרונות היסוד נשארים תקפים:

- Hard Gates מופרדים מ־Alpha Evidence.
- TR, Order Flow ו־Options אינם הצבעת 2/3.
- `false`, `unknown`, `unavailable`, `not_applicable` ו־`0` נשמרים בנפרד.
- Setup, Trigger, Entry ו־Fill הם מצבים שונים.
- Target/Risk geometry מחושבים לפני צריכת Trigger.
- אין Online Rule Mutation; למידה עוברת Offline Evaluation ו־Promotion Gate.
- Metrics מפולחים לפי producer, graph, version, regime ו־era.

הפער המרכזי שנמצא הוא בין **Architecture Principles** לבין **Executable Runtime Contracts**. לכן יש להוסיף את החוזים המפורטים להלן לפני מימוש Unified Brain.

### 17A.2 Node Taxonomy מורחב

הסיווג `HARD_GATE` מפוצל לשלושה סוגים:

| סוג | Scope | דוגמה | תוצאה בכישלון |
|---|---|---|---|
| `GLOBAL_HARD_GATE` | כל המערכת | data invalid, account blocked, kill switch | `NO_TRADE` גלובלי |
| `GRAPH_ELIGIBILITY_GATE` | Graph/Candidate מסוים | W חסר ב־W Graph, OF tape חסר ב־OF Graph | דחיית Graph בלבד |
| `ALPHA_EVIDENCE` | ציון הסתברותי | retest quality, vector strength, options prior | שינוי score/confidence |

אסור להפוך Evidence ל־Global Veto ללא Experiment ו־Promotion. אסור להפוך Dependency מחייב ל־Feature רך רק כדי לשמור Candidate.

### 17A.3 Feature Dependency Graph

יש ליצור `configs/features/feature-dependency-graph.yaml`. לכל Feature Family:

```yaml
feature_family: tr.vector
inputs:
  - normalized_bars
  - volume_provenance
update_trigger: bar_close
loop: fast
max_compute_ms: null  # research/benchmark required
ttl_ms: null          # must be approved per instrument/timeframe
fallback: UNAVAILABLE
consumers:
  - tr_graphs
  - unified_state
skip_rule: null
```

הגרף חייב לאפשר:

- topological execution.
- lazy evaluation כאשר בטוח.
- failure propagation ללא silent defaults.
- cache invalidation לפי version/timestamp.
- compute/latency profiling.

### 17A.4 Partial Evaluation ו־Skip Rules

Early Exit מותר רק כאשר הוא אינו יוצר False Negative לא מאושר.

Safe examples:

```text
GLOBAL data gate failed → stop all new candidates
required Graph dependency unavailable → skip that Graph
candidate expired → stop candidate evaluation
```

Unsafe by default:

```text
Regime score weak → skip all setup engines
TR weak → skip independent OF candidate generation
Options unavailable → block TR globally
```

כל Skip Rule חייב לכלול test שמוכיח deterministic routing ו־coverage impact report.

### 17A.5 Compute Budget Contract

יש ליצור Budget לפי node/feature family:

```text
trigger_type
expected_frequency
p50/p95/p99 latency
maximum allowed latency
CPU/GPU/memory budget
cache policy
degraded behavior
```

Slow Loop ו־Fast Loop כבר קיימים ארכיטקטונית; לפני Production יש למפות כל Feature לאחד מהם או ל־event-driven update. אין להריץ LangGraph checkpointing במסלול per-tick אם אינו עומד ב־latency budget.

### 17A.6 Freshness / TTL Policy

יש ליצור `configs/features/freshness-policy.yaml` עם TTL לפי:

```text
feature family
instrument
timeframe/session
source latency
market status
```

סטטוסים מחייבים:

```text
FRESH
STALE_USABLE
STALE_BLOCKING
UNAVAILABLE
NOT_APPLICABLE
```

TTL אינו מספר גלובלי ואינו מומצא. הוא Research/Operations Parameter עד למדידת קצב עדכון ו־latency בפועל.

### 17A.7 Critical Dependency Matrix

יש ליצור `configs/graphs/critical-dependency-matrix.yaml`:

```yaml
graph_id: tr-vshape-retest-long
required:
  - data.ohlcv
  - tr.location
  - tr.vshape
  - tr.retest
optional:
  - order_flow.absorption
  - options.prior
degraded_policy:
  order_flow.absorption: LOWER_CONFIDENCE
  options.prior: UNKNOWN_PRIOR
blocking_policy:
  tr.location: REJECT_GRAPH
```

Matrix זו מגדירה Degraded Mode ברמת Graph ולא באמצעות כלל גלובלי עמום.

### 17A.8 Historical Conditional Contract

יש ליצור `configs/history/historical-match-policy.yaml`. המנוע חייב להגדיר:

- state representation and included feature versions.
- scaling/normalization fitted on Train only.
- exact distance/similarity metric.
- categorical matching policy.
- producer/graph/regime/symbol/asset constraints.
- time-decay policy.
- `effective_n`, לא רק raw N.
- minimum sample/coverage policy.
- confidence/credible interval.
- hierarchical fallback.
- OOS calibration and drift monitoring.

Output contract:

```json
{
  "probability": 0.64,
  "effective_n": 137,
  "interval_low": 0.55,
  "interval_high": 0.72,
  "match_level": "GRAPH_REGIME_ASSET_CLASS",
  "coverage": "MEDIUM",
  "policy_version": "historical-match-0.1.0"
}
```

Fallback hierarchy example:

```text
Graph + Regime + Symbol
→ Graph + Regime + Asset Class
→ Graph + Broad Regime
→ Global calibrated model prior
→ INSUFFICIENT_EVIDENCE
```

אין להציג point estimate ללא N, interval, match level ו־coverage. Thresholds ו־minimum N נשארים Research Parameters עד OOS validation.

### 17A.9 Conflict Policy

יש ליצור `configs/decision/conflict-policy.yaml`. המדיניות אינה LLM discretion.

Inputs:

- candidate producer/graph/direction.
- calibrated probability and EV.
- regime.
- producer reliability in matching regime.
- data quality/coverage.
- disagreement type.
- portfolio exposure.

Outputs:

```text
SELECT_CANDIDATE
WAIT
NO_TRADE
LOWER_SIZE
REQUIRE_CONFIRMATION
SPECIAL_SETUP
```

כל rule חייב לכלול `policy_version`, reason code ו־evidence. כלל 2/3 אסור כברירת מחדל.

### 17A.10 Options Operating Mode

Options נשאר Producer עצמאי ארכיטקטונית, אך כל Graph/Release מגדיר capability:

```text
PRIOR_ONLY
CONFIRMATION_ONLY
CANDIDATE_PRODUCER
DISABLED
```

לגרסה ראשונה מומלץ `PRIOR_ONLY` עד ש־Options-native Candidates מוכיחים Edge עצמאי.

Options prior חייב לכלול:

```text
sign_assumption
inventory_assumption
assumption_confidence
chain_quality
prior_confidence
maximum_rank_influence
```

כאשר sign/inventory assumptions אינן מאומתות, prior confidence יורד. Maximum influence מוגבל לפי policy מאושרת; אין וטו גלובלי.

### 17A.11 Order Flow Executability Contract

יש להגדיר לכל OF Graph:

- required executed-flow sources.
- whether displayed DOM is optional or required.
- minimum classification/coverage quality.
- allowed partial evidence.
- stale/gap thresholds.
- behavior when tape, aggressor classification, MBO או DOM unavailable.

Executed Flow ו־Displayed Liquidity נשארים מקורות שונים. Absorption/Imbalance חלקיים אינם הופכים אוטומטית ל־Candidate executable.

### 17A.12 Risk, Sizing ו־Portfolio Policy

יש ליצור `configs/risk/portfolio-sizing-policy.yaml` עם:

- approved sizing family per graph/style: fixed-fractional, volatility-targeted או capped model.
- per-trade, per-symbol, per-direction and portfolio caps.
- correlation/exposure methodology and lookback policy.
- regime-conditional stress multipliers.
- behavior for existing correlated positions.
- max concentration and event exposure.
- explicit prohibition on uncapped Kelly sizing.

Sizing Model Selection הוא policy versioned. המודל אינו בוחר שיטת sizing באופן חופשי.

### 17A.13 Empirical Cost / Fill / Capacity Model

יש ליצור `configs/execution/cost-fill-policy.yaml` ו־Model Card נפרד.

ה־model חייב להפריד:

```text
commission
spread
slippage
market impact
queue/fill probability
partial fill
cancel/replace cost
adverse selection
```

Priority:

1. empirical fills כאשר קיימים.
2. empirical proxy calibrated by session/volatility/size/liquidity.
3. conservative theoretical fallback עם confidence נמוך.

יש לחשב Edge אחרי עלויות ולדווח Capacity Curve לפי size. Touch במחיר אינו הוכחת Fill.

### 17A.14 Kill Switch Taxonomy

יש ליצור `configs/runtime/kill-switch-policy.yaml`:

| Kill Type | Scope | Example | Required action |
|---|---|---|---|
| DATA | producer/global | stale/corrupt feed | block affected scope |
| RISK | account/portfolio | loss/exposure breach | block new risk, manage exits |
| EXECUTION | broker/venue | rejects/disconnect | cancel/reconcile/block |
| MODEL | model/graph | schema/OOD/calibration failure | fallback or disable model |
| SYSTEMIC | global | clock/storage/event bus failure | global safe mode |
| MANUAL | configured scope | human emergency stop | immediate policy action |

Kill State חייב להיות auditable, idempotent ועם recovery/acknowledgement policy. גם במצב חסימה ממשיכים לנהל פוזיציות קיימות לפי safe policy.

### 17A.15 LLM Meta Contract

המלצה לגרסה ראשונה: LLM פועל להסבר, Audit, assumption detection ו־Research בלבד. הוא אינו משנה Rank, Size או Order.

אם בעתיד יאושר כ־Evidence, נדרש schema:

```json
{
  "thesis": "string",
  "supported_state_paths": ["tr.vector.recovery_pct"],
  "assumptions": [],
  "contradictions": [],
  "recommended_action": "WAIT",
  "confidence": 0.61,
  "schema_version": "llm-meta-0.1.0"
}
```

Validator בודק שכל path קיים ב־Snapshot, כל assumption מסומנת וכל output enum תקין. Unsupported claim גורם reject/flag. LLM אינו עוקף Hard Gate ואינו שולח Order.

### 17A.16 Multiple Testing ו־Experiment Ledger

יש להוסיף `research/experiment-ledger` ששומר גם ניסויים שנכשלו:

```text
experiment_id
hypothesis
features/graphs/parameters
dataset manifest
train/validation/test periods
number of prior trials
metrics and costs
accepted/rejected
decision reason
```

Walk-forward לבדו אינו מספיק אם הצוות מכוונן שוב ושוב על אותם חלונות. Promotion Report חייב לכלול correction/robustness analysis עבור multiple testing, selection bias ו־non-normal returns, וכן רשימת כל ה־trials הרלוונטיים.

### 17A.17 מה מוסיף Edge ומה רק שומר עליו

| סוג | רכיבים | משמעות |
|---|---|---|
| Potential Alpha Edge | historical conditional, regime reliability, conflict meta-ranker, OF/Options signals | חייב הוכחת OOS |
| Execution Edge | empirical fills, slippage, impact, order selection, capacity | עשוי לשמר Alpha לאחר עלויות |
| Risk/Robustness Edge | dependencies, TTL, degraded mode, kill switches, null policy | מפחית false edge ותקלות; אינו Alpha בפני עצמו |
| Governance | experiment ledger, LLM validation, promotion | מונע overfitting ושינוי לא מבוקר |

אין לסמן Feature או Policy כ־Edge על בסיס הסבר סביר. Edge קיים רק לאחר OOS, costs, calibration, stability ו־multiple-testing controls.

### 17A.18 Artifacts חדשים

```text
configs/features/feature-dependency-graph.yaml
configs/features/freshness-policy.yaml
configs/graphs/critical-dependency-matrix.yaml
configs/history/historical-match-policy.yaml
configs/decision/conflict-policy.yaml
configs/risk/portfolio-sizing-policy.yaml
configs/execution/cost-fill-policy.yaml
configs/runtime/degraded-mode-policy.yaml
configs/runtime/kill-switch-policy.yaml
schemas/llm-meta-output.schema.json
research/experiment-ledger/
research/priority-register.yaml
```

### 17A.19 Research Priority Register

`research/priority-register.yaml` יסווג כל פרמטר:

```text
P0_BLOCKS_DATASET
P0_BLOCKS_SHADOW
P0_BLOCKS_LIVE
P1_REQUIRED_BEFORE_UNIFIED
P2_OPTIMIZATION
```

Suggested priority:

1. P0: point-in-time data, labels, dependencies, TTL, critical matrix.
2. P0: cost/fill, risk/sizing, degraded/kill policies.
3. P0/P1: historical matching, effective N, calibration and fallback.
4. P1: conflict policy and producer reliability.
5. P1: OF executable contracts.
6. P1: Options prior limits and assumptions.
7. P2: LLM as constrained Evidence; explanation/Audit may start earlier.

### 17A.20 Decision Items לרועי

רועי נדרש לאשר או לשנות, עם reason ו־version:

1. האם Options ב־v1 הוא `PRIOR_ONLY`.
2. האם LLM ב־v1 הוא `EXPLANATION_AUDIT_ONLY`.
3. איזה TR Graph הוא Vertical Slice הראשון.
4. איזה Labels ו־Trade Contract מגדירים הצלחה ב־v1.
5. איזה Sizing Family הוא ברירת המחדל.
6. אילו Dependencies הן P0 לכל Graph.
7. מהו Promotion Standard מ־Research ל־Shadow ול־Live.
8. כיצד נמדדים multiple testing ו־minimum evidence.

אי־הכרעה נשמרת כ־OPEN Decision ואינה מקבלת ברירת מחדל מוסתרת בקוד.

---

## 18. הוראות עבודה לכלי LLM

כלי LLM שמקבל מסמך זה חייב לפעול לפי הכללים הבאים:

1. קרא את המסמך במלואו לפני שינוי קוד.
2. בדוק `AGENTS.md`, README, schemas ו־existing tests בריפו.
3. אל תמציא Threshold, Label, Feed או Feature שלא הוגדרו.
4. אם חסר Research Parameter, הוסף TODO/config/schema; אל תקבע ערך Live.
5. אל תמזג Hard Gates לתוך מודל סטטיסטי.
6. אל תמלא null ב־0 ללא contract מפורש.
7. שמור provenance, timestamp ו־version בכל Artifact.
8. כתוב קודם schema/test ורק אחר כך implementation כאשר החוזה חדש.
9. כל חישוב היסטורי חייב להיות point-in-time.
10. כל Candidate, כולל rejected, חייב להירשם.
11. אל תאמן על החלטת העץ בלבד; Label מגיע מ־Outcome עתידי לפי Trade Contract.
12. אל תבצע random split לסדרות זמן.
13. אל תשנה מודל Live לאחר דוגמה בודדת.
14. אל תאפשר למודל לבצע Order ישירות; עבור דרך Decision Policy, Risk ו־Execution.
15. שמור backward compatibility בין schema versions או כתוב migration.
16. הוסף tests לכל failure path, לא רק happy path.
17. אל תטען ששיפור הושג ללא Out-of-sample evidence.
18. בסיום כל Phase, הפק Implementation Report: files, tests, decisions, unresolved risks ו־next phase.

### 18.1 תבנית משימה לכלי LLM

```text
Objective:
Implement <phase/component> according to
TR-TREE-TO-TRAINED-MODEL-IMPLEMENTATION-PLAN.md.

Scope:
<exact files/modules>

Required inputs:
<schemas/configs/raw sources>

Contracts:
<feature/label/candidate versions>

Non-negotiables:
- point-in-time correctness
- no invented research parameters
- hard gates remain deterministic
- provenance and versioning
- tests before completion

Acceptance criteria:
<machine-verifiable tests and outputs>

Out of scope:
<explicit exclusions>
```

---

## 19. Definition of Done למערכת הראשונה

המערכת הראשונה נחשבת מוכנה ל־Shadow בלבד כאשר:

- כל 22 השכבות ממופות ל־Node Registry.
- כל 14 שלבי TR מיושמים או מסומנים במפורש כ־Unavailable/Research.
- קיימים Shared Context, TR, OF ו־Options contracts.
- Candidate Snapshot ו־Outcome Labels ניתנים לשחזור.
- LONG ו־SHORT מוערכים לפני בחירה.
- WAIT ו־NO_TRADE הם outputs מלאים עם reasons.
- Hard Gates אינם נלמדים.
- 16 השנים מחולקות לפי data availability eras.
- Walk-forward + purging + embargo עברו.
- הסתברויות מכוילות ונבדקו לפי segment.
- costs/fills/ambiguity מטופלים.
- כל prediction ו־decision נשמרים עם versions.
- rollback ו־kill switch נבדקו.
- אין online auto-learning.

---

## 20. הצעד הראשון המומלץ

לא להתחיל מאימון. להתחיל מ־Specification Freeze ולייצר שלושה Artifacts:

1. `node-registry.yaml` — כל Node, סוגו ותלויותיו.
2. `feature-catalog.yaml` — schema מלא לכל Feature.
3. `label-contracts.yaml` — Entry/Stop/Target/Expiry/Costs לכל Graph.

לאחר אישור שלושת הקבצים, יש ליישם Dataset Factory קטן עבור Symbol אחד, Graph אחד ותקופה מוגבלת. רק לאחר שה־Replay, Features ו־Labels נכונים, להרחיב ל־16 שנים ולשאר המוחות.

---

## 21. סיכום מחייב

```text
Tree = computation order + feature definitions + candidates + hard constraints
Features = point-in-time state derived from the tree
Labels = future outcomes derived from a versioned trade contract
Model = probabilistic mapping from state + candidate action to outcomes
Decision Policy = comparison of calibrated LONG/SHORT utilities
Risk/Execution = deterministic control surrounding the model
Learning = offline, versioned, validated and explicitly promoted
```

העץ אינו מוחלף במודל. העץ הופך לתשתית שמייצרת את הקלט, מגדירה את הבעיה, מגינה על המערכת ומאפשרת למודל ללמוד רק את החלק שאכן צריך להילמד מהדאטה.
