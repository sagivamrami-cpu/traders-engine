# TRADERS REALITY Content Engine (עסק עצמאי)

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

- Architecture blueprint: `docs/architecture/TR-TREE-TO-TRAINED-MODEL-IMPLEMENTATION-PLAN.md`
- Multi-tool operating model: `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`
- Phase 0 implementation plan: `docs/superpowers/plans/2026-08-31-phase-0-specification-freeze.md`
- Phase 0 report: `docs/implementation-reports/phase-0-specification-freeze.md`
