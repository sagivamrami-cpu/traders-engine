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
