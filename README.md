# TR Hybrid Intelligence — פרויקט העץ, הסימולציה והמודל

**יובל וכלי הפיתוח: התחילו כאן.** קוד המחקר והעבודה המצטברת נמצאים בענף
`plan/tree-to-trained-model-langgraph`. הענף `main` עדיין משקף את בסיס מנוע התוכן.

- [מצב הפרויקט ונקודת ההמשך](PROJECT_STATE.md) — לקריאה בתחילת כל עבודה.
- [מסירה ליובל: התקנה, בדיקות, מקורות ותוכנית ההמשך](docs/architecture/YUVAL-HANDOFF.md).
- [הסבר הפרויקט לסוחר ולמהנדס, HTML](docs/architecture/YUVAL-PROJECT-ONBOARDING.html).
- [תוכנית האב המאושרת](docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md).
- [מה נדרש משגיב](docs/architecture/SAGIV-INPUTS-REQUIRED-FOR-PROJECT.md).
- [הוראות לסוכני פיתוח](AGENTS.md).

המטרה היא ללמוד אילו עסקאות שהעץ מציע מצליחות כלכלית, ובהמשך ללמוד ניהול
עסקה. קיימות תשתיות שחזור ובדיקת נאמנות למקור; יצירת דאטהסט התוצאות ואימון
המודל החדש עדיין לפנינו. חומרי המקור, ההחלטות והבדיקות נכללים במאגר.
ארכיוני שוק ומפתחות נשמרים מחוץ ל־Git; הוראות השחזור מפורטות במדריך המסירה.

```powershell
git clone --branch plan/tree-to-trained-model-langgraph https://github.com/sagivamrami-cpu/traders-engine.git
cd traders-engine
```

בכלי פיתוח אפשר לכתוב: **"קרא את AGENTS.md ואת PROJECT_STATE.md, בדוק את
מצב הקוד וההודעות החדשות, והמשך את התוכנית מהמשימה הראשונה שניתן לבצע."**

## מנוע התוכן המקורי (רכיב נפרד)

מנוע תוכן עצמאי לחלוטין ל-TRADERS REALITY. **אין כאן שום קשר או קובץ משותף עם עסק הקוסמטיקה.**
Notion משלו, בוט טלגרם משלו, API key משלו.

```
traders-engine/
├── engine/
│   ├── prompts.py
│   ├── generate.py
│   ├── deliver_notion.py
│   └── deliver_telegram.py
├── brand.py                        # פרטי המותג + guardrails (בלי הבטחות רווח/איתותים)
├── run_daily.py
├── com.tradersreality.daily.plist   # launchd — הריצה היומית האוטומטית (ראה "תזמון" למטה)
├── .env.example
├── crontab.txt                     # לא בשימוש בפועל — נשמר כדוגמת אלטרנטיבה ל-launchd
└── requirements.txt
```

## התקנה
```bash
cd traders-engine
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mkdir -p logs
cp .env.example .env
```

## הגדרות
1. **brand.py** — פרטי המותג. שים לב ל-guardrails: אסור הבטחות רווח, אסור איתותים, חובה מסגור סיכון — גם חוקית וגם מותגית ("בלי בולשיט").
2. **Notion** — Database נפרד משלך עם `Name`,`Status`(+`Draft`),`Pillar`,`Date`; הכנס id ל-`NOTION_DB`.
3. **Telegram** — בוט ייעודי ("TRADERS REALITY"): טוקן מ-BotFather ל-`TELEGRAM_BOT_TOKEN`, ה-chat id שלך ל-`TELEGRAM_CHAT_ID` ב-`.env`.

## הרצה
```bash
python run_daily.py --dry-run
python run_daily.py --count 5
python run_daily.py --count 5 --no-telegram   # דילוג על הודעת הטלגרם
```

## תזמון
הריצה היומית מנוהלת ב-launchd (macOS), לא ב-cron:

```bash
cp com.tradersreality.daily.plist ~/Library/LaunchAgents/
launchctl load -w ~/Library/LaunchAgents/com.tradersreality.daily.plist
```

רץ כל יום ב-09:00 (`StartCalendarInterval` בקובץ ה-plist). לוגים ב-`logs/run.log` / `logs/run.err.log`.
הקובץ **חייב** לשבת מחוץ ל-`~/Desktop`/`~/Documents`/`~/Downloads` — macOS חוסם גישת launchd לתיקיות המוגנות האלו.

`crontab.txt` נשאר בתיקייה כדוגמה בלבד, לשרת לינוקס/מכונה אחרת שבה cron רגיל מספיק.

## TR Hybrid Intelligence Planning

The trading-system implementation plan is tracked separately from the content
engine.

- Current agreed outcome-learning design (Hebrew): [Full plan](docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md)
- Initial implementation and remaining roadmap: [Tree replay foundation](docs/superpowers/plans/2026-09-08-tree-replay-foundation.md)
- Source inspection: `python tools/inspect_tree_source.py` (inventory only; not training readiness)
- Existing-source pins and economic arithmetic: [Offline contract usage](docs/architecture/EXISTING-BASELINE-CONTRACTS-USAGE.md) (not a replay or trained model)
- Historical EMA observations: [As-of adapter usage](docs/architecture/ASOF-EMA-ADAPTER-USAGE.md) (closed contiguous bars; no candidate generation)
- Session-aware EMA history: [Calendar adapter usage](docs/architecture/SESSION-EMA-ADAPTER-USAGE.md) (explicit research schedules; no historical-market certification)
- Offline reversal setup detection: [Level-reversal adapter](docs/architecture/LEVEL-REVERSAL-ASOF-USAGE.md) (supplied as-of levels; unpriced setups only, not admitted trades or labels)
- Original reversal pricing: [Pricing adapter](docs/architecture/REVERSAL-PRICING-USAGE.md) (entry/stop/targets and refusals; no admission, fills or outcome labels)
- Full remaining scope and evidence: [Implementation tracker](docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md)
- Running daily OHLC: [Period evidence adapter](docs/architecture/DAILY-PERIOD-ASOF-USAGE.md) (supplied boundaries/calendar; no future daily prices)
- Original range dependencies: [Range source subset](docs/architecture/RANGE-SOURCE-USAGE.md) (not a full level-map replay)
- Historical correction evidence: [As-of source assessment](docs/architecture/CORRECTION-ASOF-USAGE.md) (explicit replay clock; source flags are not trade admission or feed certification)
- Historical daily/intraday frames: [Causal frame construction](docs/architecture/HISTORICAL-FRAMES-USAGE.md) (explicit calendars/labels/grids; closed-base prefixes only)
- Complete original map graph: [Source graph and audit](docs/architecture/LEVELMAP-SOURCE-USAGE.md) (exact families/order/gates with offline source and clock)
- Historical map binding: [Map adapter](docs/architecture/HISTORICAL-LEVELMAP-USAGE.md) (causal dependencies and stable level IDs; BUILT_UNADMITTED, not fills or outcome labels)
- Between-close decision clocks: [Closed-base-prefix policy](docs/architecture/CLOSED-BASE-PREFIX-USAGE.md) (actual publication/freshness time; unchanged strict defaults)
- Original internal reversal producer: [As-of producer](docs/architecture/REVERSAL-PRODUCER-ASOF-USAGE.md) (real map, M5/M15 selection and original pricing; no external admission, fills or labels)
- Remaining operational gates: [Source intake](docs/architecture/MARKET-WATCH-ADMISSION-SOURCE-INTAKE.md) (read-only dependency mapping, not implemented admission)
- Admission calculation dependencies: [Source calculations](docs/architecture/ADMISSION-CALCULATIONS-USAGE.md) (component accepted; not full admission)
- Causal advisory memory: [Evidence journal](docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md) (accepted publication-time snapshots/checkpoints, not generated tracker transitions)
- Tracker gate/record source: [Offline ports](docs/architecture/TRACKER-ADMISSION-SOURCE-USAGE.md) (accepted original source closure; causal full-loop binding remains)
- Original selected Plan: [Internal handoff](docs/architecture/REVERSAL-HANDOFF-USAGE.md) (accepted original object retention; public evidence unchanged, actual causal providers remain)
- Causal admission frames: [Frame provider](docs/architecture/ADMISSION-FRAME-BINDING-USAGE.md) (accepted original matrix/tracker calculations on supplied history; full state/log/quote binding remains)
- Causal tracker storage: [Storage binding](docs/architecture/TRACKER-STORAGE-BINDING-USAGE.md) (accepted source load/save guards and artifact handoff; locks, quotes/logs and full lifecycle remain)
- Causal quote/watch IO: [Quote and raw-log binding](docs/architecture/CAUSAL-QUOTE-WATCH-IO-USAGE.md) (accepted exact source reads/appends; full caller, lock and lifecycle binding remains)
- Original tracker lock policy: [Offline lock ports](docs/architecture/TRACKER-LOCK-SOURCE-USAGE.md) (accepted skip/stall/reentrance/cleanup; shared scheduler and full caller binding remain)
- Shared causal admission context: [Context usage](docs/architecture/CAUSAL-ADMISSION-CONTEXT-USAGE.md) (accepted shared clock/publications and real tracker consumers; not full caller, lifecycle or training)
- Causal watch state: [Watch storage](docs/architecture/WATCH-STATE-BINDING-USAGE.md) (accepted original two save boundaries and persisted images; not full watch-loop checkpoint)
- Original post-fill geometry and movement proof: [Lifecycle primitives](docs/architecture/BAR-LIFECYCLE-PRIMITIVES-USAGE.md) (accepted original windows, explicit clocks and source audit; movement success is not economic profit or a completed replay)
- Original independent price-claim checker: [Verifier](docs/architecture/INDEPENDENT-CLAIM-VERIFIER-USAGE.md) (accepted decoder, clocks and source audit; not full gate effects or causal feed certification)
- Original daily extension state: [Stretch](docs/architecture/STRETCH-SOURCE-USAGE.md) (accepted complete calculations/source audit; actual ADR14 and half-ADR rails, not a new trading signal)
- Complete EMA windows and deep-history reader: [EMA reader](docs/architecture/EMA-DEEP-READER-USAGE.md) (accepted original six-window calculations and source audit; raw inputs are not certified historical features)

- Architecture blueprint: `docs/architecture/TR-TREE-TO-TRAINED-MODEL-IMPLEMENTATION-PLAN.md`
- Multi-tool operating model: `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`
- Phase 0 implementation plan: `docs/superpowers/plans/2026-08-31-phase-0-specification-freeze.md`
- Phase 0 report: `docs/implementation-reports/phase-0-specification-freeze.md`
