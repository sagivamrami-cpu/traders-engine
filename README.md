# TRADERS REALITY Content Engine (עסק עצמאי)

מנוע תוכן עצמאי לחלוטין ל-TRADERS REALITY. **אין כאן שום קשר או קובץ משותף עם עסק הקוסמטיקה.**
Notion משלו, WhatsApp משלך, API key משלו.

```
traders-engine/
├── engine/
│   ├── prompts.py
│   ├── generate.py
│   ├── deliver_notion.py
│   └── deliver_whatsapp.py
├── brand.py               # פרטי המותג + guardrails (בלי הבטחות רווח/איתותים)
├── run_daily.py
├── .env.example
├── crontab.txt
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
3. **WhatsApp** — במספר שלך: CallMeBot → `I allow callmebot to send me messages` → טלפון+apikey ל-.env.

## הרצה
```bash
python run_daily.py --dry-run
python run_daily.py --count 5
```

## cron
שורה מ-`crontab.txt` ל-`crontab -e`. תזמנתי אותו ל-07:15 כדי לא להתנגש עם עסק אחר על אותו שרת (לא חובה — הם עצמאיים).
