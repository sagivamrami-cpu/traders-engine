# מסירה ליובל — 16 בספטמבר 2026

יובל, הפרויקט וכל ההחלטות נשמרים בקבצים. אינך צריך את היסטוריית השיחה כדי
להמשיך. פתח קודם את [PROJECT_STATE.md](../../PROJECT_STATE.md), שמגדיר מה קיים,
מה עדיין פתוח ומהי המשימה הבאה. ההסבר המסחרי והטכני המורחב נמצא
ב־[מדריך HTML](YUVAL-PROJECT-ONBOARDING.html).

## מה אנחנו בונים

העץ של שגיב קורא את מצב השוק ומציע עסקאות עם כיוון, כניסה, סטופ ויעדים.
אנחנו משחזרים את פעולתו לאורך ההיסטוריה ומצלמים את כל הנתונים שהיו ידועים
ברגע ההחלטה. נתונים אלה הם **features**: ממוצעים, שיפועים, רמות, וקטורים,
סשן, מבנה שוק, תשובות וענפים שנבדקו, וכן הקשר זמין ממקורות נוספים.

לאחר מכן סימולטור אמור לבדוק מה קרה לעסקה לפי מדיניות ביצוע מוגדרת. התוצאה
היא **label**: רווח נטו חיובי, שלילי או אפס, ולצדו `net_R` — רווח נטו ביחס
לסיכון ההתחלתי. תוצאה עתידית אינה נכנסת לפיצ'רים של רגע הכניסה. ניסיון שלא
התמלא או שחסר מידע להכריע לגביו נשמר במצב המתאים ואינו הופך אוטומטית להפסד.

מודל הבחירה הראשון אמור לדרג/לסנן מועמדים שהעץ מציע. CatBoost הוא המועמד
הראשי לטבלה המשלבת מספרים וקטגוריות, אך עליו להראות תוספת ערך מול העץ
לבדו ומול מודלים פשוטים, בתקופות שלא שימשו לאימון ובניכוי עלויות.
אחוזי הצלחה שהוצהרו על העץ טרם הוכחו באמצעות הצינור החדש.

ניהול עסקה דינמי הוא המשך מפורש בתוכנית: בכל נקודת זמן מתעדים מצב,
פעולות מותרות, פעולה שנבחרה ותוצאת ההמשך. הוא דורש דוגמאות וכללים משגיב
ומדידה נפרדת. לא מעתיקים את תוצאת העסקה הסופית לכל החלטת ניהול בתוכה.

## הורדה והתקנה

המסירה נמצאת בענף `plan/tree-to-trained-model-langgraph` במאגר
`sagivamrami-cpu/traders-engine`. יש לבחור את הענף הזה גם בממשק GitHub.
ההעלאה אינה מיזוג ל־main ואינה מפעילה את מערכת המסחר.

```powershell
git clone --branch plan/tree-to-trained-model-langgraph https://github.com/sagivamrami-cpu/traders-engine.git
cd traders-engine
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -c constraints-handoff.txt
.\.venv\Scripts\python.exe tools/prepare_tree_sources.py
.\.venv\Scripts\python.exe tools/inspect_alert_baseline.py --root .source-checkouts --require-source-verified
```

ב־Linux/macOS משתמשים ב־`python3 -m venv .venv` ואז ב־`.venv/bin/python`.
סביבת רועי שנבדקה היא Python 3.13.5 ו־Git 2.50.0.windows.1; יש להשתמש ב־Git
התומך ב־`--no-lazy-fetch`. הקובץ `constraints-handoff.txt` מקבע את גרסאות
התלויות המספריות וכלי הבדיקה שנמצאו בסביבת רועי כדי לא לשנות חישובים במעבר.
הוא משלים את `requirements.txt`; זה אינו lockfile מלא של כל תלויות מנוע התוכן.
במקרה של אי־תאימות יש לתעד גרסאות בפועל.

`prepare_tree_sources.py` מכין שישה checkouts נפרדים בגרסאות המקור המדויקות
מתוך `configs/trees/existing-alerts-baseline.json`. הם מיועדים להשוואת קוד,
לא להפעלת מערכות המקור. אין להשתמש ב־HEAD החדש של chart-desk במקום ה־pin.
הכלי אינו אמור לדרוס checkout קיים ששונה או מכוון לגרסה אחרת.

יובל צריך הרשאת קריאה לכל ששת מאגרי המקור. אם מאגר דורש התחברות, יש להגדיר
Git credential helper במחשב שלו (למשל באמצעות התחברות GitHub מקומית).
הכלי משתמש בהתחברות הקיימת ואינו שומר טוקן במאגר או מבקש להעביר טוקן בשיחה.

אפשר לבחור תיקיית מקור אחרת ולהגדיר `TR_TREE_SOURCE_ROOT` כתיקיית האב של
ששת המאגרים ו־`TR_CHARTDESK_SOURCE_ROOT` כתיקיית `chart-desk` שבתוכה.
ברירת המחדל היא `.source-checkouts/` בתוך מאגר המחקר. אין עוד צורך בנתיב Temp
של רועי. הקוד המקורי נשאר במאגרי GitHub שלו; המתאמים וההקרנות שנכתבו במחקר
נמצאים כאן ב־`trading_system/tree_replay/_vendor/`.

## בדיקות כניסה

אין צורך במפתחות API לבדיקות הסינתטיות. מהרוט של המאגר:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/tree_spec/test_economics.py tests/tree_replay/test_cross_market_flow_policy.py tests/tree_replay/test_cross_market_flow.py tests/tree_replay/test_full_tree_cross_market_context.py tests/tree_replay/test_full_tree_capture.py tests/tree_replay/test_full_tree_replay.py tests/research/test_xauusd_local_source_audit.py -q --tb=short -p no:cacheprovider
```

לאחר הכנת ששת המקורות, להרצת חבילת העץ והבדיקות המשוות למקור:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/tree_replay tests/tree_spec -q --tb=short -p no:cacheprovider
```

הבדיקות המקיפות עשויות להימשך עשרות דקות; בבדיקת המסירה עברו 4,585 בדיקות
בכ־34 דקות, עם אזהרת תצורת pytest אחת וללא כשלים. הוכחת source parity מחייבת את
ה־checkouts; אין לדלג על כשל מקור ולדווח שההשוואה עברה. תוצאות מסירה בפועל
נרשמות ב־`agent-exchange/status/2026-09-16T080722Z-codex-yuval-handoff.md`.
בדיקות אלו אינן הוכחה לרווחיות או למוכנות למסחר. חבילת `tests/` כולה כוללת
גם את מחקר ה־GC הישן ותלויה בהקשרים נוספים.

לביקורות המקור שבתור, אלו פקודות עדכניות המחליפות נתיבי Temp שמופיעים
בבקשות ההיסטוריות. ב־Linux/macOS החלף את קידומת Python ב־`.venv/bin/python`:

```powershell
.\.venv\Scripts\python.exe -B tools/check_full_tree_replay_source_parity.py --source-root .source-checkouts
.\.venv\Scripts\python.exe -B tools/check_full_tree_capture_source.py
.\.venv\Scripts\python.exe -B tools/check_handoff.py
```

## מפת הקבצים

| מיקום | שימוש |
|---|---|
| `PROJECT_STATE.md` | סטטוס קצר, החלטות תקפות וסדר ההמשך |
| `AGENTS.md`, `CLAUDE.md` | נקודות כניסה לכלי פיתוח והפניה לפרוטוקול |
| `docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md` | תוכנית האב, כולל ניהול דינמי J0–J7 |
| `docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md` | מעקב ביצוע והיסטוריית ראיות |
| `docs/superpowers/specs/`, `plans/` | מפרטים ותוכניות ממוקדות |
| `trading_system/tree_replay/` | קוראי העץ, חישובים, שעונים, מצב ו־replay |
| `trading_system/tree_spec/` | חוזים, קטלוג, ביקורת נאמנות למקור וחשבונאות כלכלית |
| `configs/trees/`, `configs/data/`, `schemas/` | source pins, הגדרות נתונים וסכמות |
| `tests/tree_replay/`, `tests/tree_spec/` | תרחישים ובדיקות שינוי/נאמנות |
| `tools/` | CLIs לבדיקה, אבחון והכנת המקורות |
| `agent-exchange/` | בקשות, תוצאות, ביקורות והחלטות אנושיות |
| `docs/sources/` | עץ HTML המקורי וחומרי ניהול עסקה |
| `.superpowers/sdd/` | ארכיון תוכניות עבודה, ביקורות ו־diffs קודמים; לא הוראות להרצה |
| `engine/`, `run_daily.py` | מנוע התוכן המקורי; אינו נתיב הכניסה למחקר המודל |
| שאר `trading_system/`, `research/` | תשתית ומחקרים קודמים; יש לבדוק התאמה למטרה הנוכחית לפני reuse |

## מה לא עובר דרך Git

נתוני שוק גולמיים (`market-data/`, CSV/Parquet/DBN/ZIP), סודות, סביבות Python,
לוגים ומאגרים מקומיים של המקורות אינם מועלים. זו גם המדיניות הקיימת של
הפרויקט. רועי צריך להעביר נתונים ורישיונות גישה בערוץ פרטי, עם checksums
ושמות מקורות; מסמכי ההחלטה וה־manifests נשארים במאגר.

יש להפריד בין שלושה פריטים בהעברה: קוד המקור המקובע שניתן לשחזור מ־GitHub,
ארכיון GC שכבר נבדק מקומית, והיסטוריית OANDA/news/options שעדיין חסרה או
שכיסויה אינו מספיק. שכפול המאגר אינו יוצר אוטומטית היסטוריה מסונכרנת.
הדוח [XAUUSD-LOCAL-DATA-AUDIT.md](XAUUSD-LOCAL-DATA-AUDIT.md) מפרט מה נמצא
במחשב רועי; נתיב שמופיע בו אינו נתיב שצפוי להתקיים אצל יובל.

## מה לעשות בבקשה הראשונה "תמשיך את התוכנית"

הדבק בכלי הפיתוח:

> קרא את AGENTS.md, PROJECT_STATE.md ואת docs/architecture/YUVAL-HANDOFF.md.
> בדוק את git status, את מקור הענף ואת הודעות agent-exchange החדשות.
> הסבר בקצרה מהי נקודת ההמשך ובצע את המשימה הזמינה הראשונה בתור.
> קרא את המפרט, הקוד והבדיקות שלה. השתמש בהחלטות המאושרות, תעד כל חוסר
> מסחרי במפורש והמשך בעבודה ההנדסית שאינה תלויה בו. סיים עם בדיקות ועדכון
> זיכרון. אל תסיק שביקורת מתנהלת רק מכך שקיים קובץ בקשה.

המשימה הראשונה המעשית היא קליטה/ביצוע של הביקורות הפתוחות על provider,
capture והקשר GC. בדיקת קוד אינה דורשת את עלויות המסחר משגיב. במקביל,
רועי ויובל מטפלים במקורות הנתונים ושגיב משלים את חוזה הביצוע והניהול.
הסדר המדויק והנתיבים לבקשות נמצאים ב־PROJECT_STATE.

## תפקידי הצוות ועדכון הזיכרון

שגיב מגדיר את כוונת המסחר ואת ההחלטות שאינן חד־משמעיות בקוד. רועי ויובל
אחראים להנדסה, סביבת העבודה וגישה לנתונים. כלי הפיתוח מממשים, בודקים
ומתעדים. החלטות שאושרו נשמרות ב־`agent-exchange/decisions/` עם היקף וראיות.

לאחר כל משימה יש לשמור קוד ובדיקות, לרשום תוצאת בדיקה והגבלות ב־status,
ולעדכן את PROJECT_STATE ואת tracker. הערות ישנות נשמרות כראיות היסטוריות;
"הבא בתור" במסמך מלפני שבוע אינו גובר על נקודת ההמשך העדכנית.
