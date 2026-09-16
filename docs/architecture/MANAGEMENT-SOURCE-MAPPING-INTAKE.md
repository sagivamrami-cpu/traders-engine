# מיפוי מקור: ניהול עסקה דינמי מול המימוש הקיים

תאריך: 2026-09-14.

מטרת המסמך היא לקדם את J2 בתוכנית האב: למפות מה כבר קיים במימוש המקורי
ובפרוסות ה־replay אל עץ ניהול העסקה החדש, ומה עדיין דורש חוזה או מימוש.
זהו מסמך קליטה ומיפוי בלבד. הוא אינו משנה מדיניות מסחר, אינו מאשר ספים,
ואינו נותן למערכת הרשאת ביצוע.

## חומר שנבדק

- עץ הניהול החדש: `C:/Users/roeea/Desktop/docs/DYNAMIC_MANAGEMENT_TREE_HE.html`.
- תרשימים: `C:/Users/roeea/Desktop/docs/MANAGEMENT_DIAGRAMS_HE.html`.
- דוח חשבון קטן: `C:/Users/roeea/Desktop/docs/ACCOUNT_1000_MANAGEMENT_REPORT_HE.html`.
- מקור ה־HTML הקודם: `C:/Users/roeea/Desktop/TR Hybrid Intelligence — עץ בינארי ומכונת מצבים.html`.
- עותק `chart-desk` המקומי ב־`C:/Users/roeea/sagiv-repos/chart-desk`, HEAD
  `7785534f1afb75d9a154b8118ad088cee9488b42`, עם שינוי מקומי שאינו שייך
  למיפוי: `data/basis_cache.json`.
- פרוסות lifecycle ו־replay ב־`trading_system/tree_replay/`.

קובץ ה־HTML המקורי המקומי תואם ל־SHA-256 שמצוין במסמך הניהול החדש:
`f7de3d8cfac6e468268ec79a8b3b990a97d62608a1fbe68b58952534c107f1ad`.

## מצב גרסאות

מסמך הניהול החדש מציין `source_chart_head`
`e79c3f854637fcce7b0f9de2efe239c27c259ab6`. בסיס המחקר המאושר מציין
`chart-desk` ב־`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`. העותק המקומי
שנבדק חסר את שני האובייקטים, אך ב־2026-09-14 אומתה זמינותם ב־origin ונוצר
עותק audit מבודד. לכן ההשוואה בוצעה מול הגרסאות המקובעות, בלי לשנות את
`chart-desk` הפעיל:

- `68b1d...` — `Stop live worker child processes safely`, 2026-09-08.
- `e79c3...` — `Add private read-only operations manager`, 2026-09-14.

ה־diff מכיל 152 קבצים, ולכן אינו אישור גורף לאימוץ כל השינויים. הוא כן
מאשר שבגרסת המקור החדשה נוספו רכיבי מחקר נפרדים לניהול (`management_trial.py`
ו־`be_shadow.py`), לצד רכיבי תצפית/דיווח נוספים. כל רכיב נבדק לפי החוזה
שלו ולא לפי שם הקובץ או לפי HEAD מקומי.

התאמת גרסאות כממצאי מקור הושלמה; התאמת *מדיניות* עדיין פתוחה: החלטות שגיב
על מצבי תזה, קדימויות ופעולות חוקיות נדרשות לפני שמותר להגדיר התנהגות חדשה.

## מה קיים וכיצד הוא ממופה

| אחריות בעץ החדש | מקור קיים | מה ניתן למחזר | גבול ברור |
| --- | --- | --- | --- |
| חוזה עסקה, כניסה, סטופ ויעדים | `chartdesk/strategy.py` | `TradePlan`, גיאומטריית stop/target, דחיית תרחיש לא תקין, יעד ראשון מול סיכון | אינו חוזה מילוי, הקצאת רגליים, expiry או state של פקודות |
| מדיניות stop/BE/trailing | `chartdesk/manage.py` | `Action`, מונוטוניות stop, פרופיל נכס וסגנון, משך החזקה | סדר קבוע BE → lock → trail; אין תזה, מימוש חלקי, פעולה/כמות בפועל או היסטוריית החלטות |
| איכות עסקה ורוחב סטופ | `chartdesk/manage.py` (`grade`, `stop_for`) | קלטי RR/reasons/warnings ומנגנון רצועת stop | מכיל פרמטרים פתוחים וערכי ברירת־מחדל; אינו אומדן מכויל של תועלת |
| סייזינג וחלוקת רגליים | `chartdesk/sizing.py` | בדיקת תקרת סיכון מול מינימום ניהול, עיגול lot, שימור כמות | 3%/5% ו־0.01 lot הם ערכים מקוריים מקומיים, לא מפרט ברוקר חדש; חלוקה לשלוש רגליים קבועה |
| סולם/הוספה | `chartdesk/policy.py` (`may_ladder`) | איסור averaging down; הוספה רק אחרי break מאומת ומתוכנן מראש | חסרים מצב fill, הקצאת סיכון נותר, כמות חדשה והגנה על הכמות שנוספה |
| מחקר TP/BE/partial/trail | `chartdesk/backtest.py` (`run`) | השוואת מדיניות, partials, BE, trailing, timeout ועלויות ביחידות R | פוזיציה אחת, כניסה בפתיחת הבר הבא, חלקיות אידאלית, ללא broker/order/account/episode state; כלי מחקר ולא ראיית מילוי |
| ניסוי paired בניהול חלקי/BE | `chartdesk/management_trial.py` ב־`e79c3...` | שני arms מחקריים: control של 25%/25%/50% מול arm עם יעדים ב־75%, חלוקות 50%/30%/20% ו־BE לאחר תנאי ATR; כולל bid/ask לכניסה, שימור כמות, gap ו־M5 ambiguity | הקובץ מצהיר `research_only`, ללא פקודות ברוקר או פרסום. שני arms קבועים אינם עץ החלטה דינמי, ואין בו reallocation, add, trailing או הגדרות התזה של שגיב |
| ניסוי shadow ל־BE | `chartdesk/be_shadow.py` ב־`e79c3...` | חוזה sealed, כרונולוגיה, states של resolved/censored/unknown/ambiguous והשוואת arms מנורמלת | מצהיר במפורש שאינו ממליץ ללקוח ואינו משנה עסקה חיה; אינו מקור לפעולת ניהול אוטומטית |
| התראות ומעקב | `scripts/market_watch.py`, `chartdesk/tracker.py` | זיהוי/רישום מועמדים והפרדת signal מ־broker fill | התראות אינן ביצוע; אין קבלות ברוקר או כמות בפועל |
| lifecycle replay | `tree_replay/_vendor/lifecycle_*.py` | PENDING/OPEN, סדר סגירות מקור, target/protection, סימון עמימות, ראיות סיבתיות | מצב מקור של tracker ללא גודל פוזיציה, חלקיות, פקודות stop, ACK או allocation; `minimum_success` אינו P&L ולא החלטת ניהול |
| ledger ו־replay סיבתי | `tree_replay/causal_replay*.py` | זמינות מידע, checkpoint/resume, lineage, חותמות evidence | כרגע מסלול `level_reversal:5m` ו־OBSERVE_ONLY; אינו מריץ מנהל פוזיציה |
| חשבונאות תוצאה כלכלית | `tree_spec/economics.py` | Decimal, עלויות מפורשות, net P&L/net R ולייבל סופי לעסקה שכבר הוכרעו מילויה | יציאה מלאה אחת מסופקת; אינו מסמלץ fills או partials |

## פערי המימוש מול עץ הניהול החדש

### 1. עץ ההחלטה אינו עדיין מנוע פעולה

העץ החדש מגדיר צמתים A01–B06, M01–M12 ו־R01–R04. מקבילת `manage.advise()`
ב־chart-desk בוחרת רק `hold`, `be`, `lock` או `trail`, ובסדר קבוע. היא אינה
מחשבת A05–A09/B01 של בחירת policy, אינה מקבלת פעולות מותרות, ואינה שומרת
נימוק, חלופות או גרסת policy לכל החלטה. לכן היא יכולה להיות מקור לקריאה
ולבדיקות חוזרות, אבל אינה מימוש של העץ החדש.

### 2. קיימת סתירה בסדר הפעולה שדורשת הכרעה

במסמך החדש ההסבר דורש הגנה לפני שינוי הקצאה והוספת חשיפה. בעץ live, M10
(`REALLOCATE`) קודם ל־M11 (`MODIFY_STOP`). המקור הקיים ב־`manage.advise()`
נותן BE/lock/trail לפני HOLD, אך אינו מכיל reallocation. אין לשלב את שלושת
הסדרים לפי ניחוש. החוזה העתידי צריך לקבוע scheduler יחיד, כולל קדימות בין
reconciliation, fill, emergency, stop/invalidation, mandatory exit, protection,
reallocation, add ו־hold.

### 3. lifecycle הקיים עוקב אחרי מצב רעיון, לא אחרי חשבון ביצוע

ה־resolver הקיים יודע ש־TP הושג ומסמן `hit`; הוא סוגר את העסקה כאשר כל
היעדים סומנו. אין לו `actual_filled_qty`, יתרה, רגלי מימוש, stop order,
ACK, `MODIFY_PENDING` או fill של הוספה. ההודעות אומרות במפורש שמימוש וניהול
הם לשיקול הסוחר. לכן אסור להציג target hit כאילו היה partial fill או P&L.

### 4. הוספה דורשת מעברי מצב ותקציב

המקור מגביל ladder ל־confirmed break מתוכנן מראש, והעץ החדש אוסר averaging
down. עדיין אין מעבר מפורש עבור fill נוסף ב־OPEN/REDUCED/RUNNER, ואין כלל
שמבצע התאמת stop/OCO לכמות החדשה. נדרש חוזה תת־עסקה או ledger של lots:
entry fill, allocation, protective coverage, reserved risk, realized costs
ו־remaining quantity. כל fill נוסף חייב לעבור הגנה לפני פעולה אחרת.

### 5. הסייזינג הקיים אינו מדיניות מאושרת לעץ החדש

המסמך החדש מציע ארבעה פרופילים ותלות במינימום lot; דוח ה־$1,000 משנה
חלוקות ואחוזי סיכון בפרופילים אחדים. `sizing.py` מניח שלוש רגליים וערכי
חשבון/lot מקומיים. יש למחזר את העקרונות של ceiling, floor ועיגול, אך להגדיר
policy מפורש הממפה `(profile, broker spec, quantity, risk budget)` אל
`effective_legs`. שומרים גם `intended_legs` וגם `effective_legs` כדי שלא
ללמד מודל כאילו האחוזים המתוכננים בוצעו כאשר העיגול שינה אותם.

### 6. הסימולטור הקיים שימושי כ־control, לא כסימולטור ביצוע מלא

`backtest.run` כבר מכבד stop-first ומימושים חלקיים פשוטים, ולכן הוא מקור
טוב להשוואת policies קבועות. הוא אינו מספיק ל־J3: אין bid/ask, slippage
תלוי פעולה, latency, OCO, כמה עסקאות/חשיפות במקביל, מילוי חלקי, פעולה
דינמית מתוך snapshot או הפרדה בין פעולה נצפית לפעולה מסומלצת. אין לשנותו
בשקט כך שיתיימר להיות מסלול ברוקר.

### 7. רכיבי הניהול החדשים הם ראיית מחקר, לא מנהל דינמי מלא

`management_trial.py` הוא בסיס שימושי ל־J3: הוא קובע גאומטריית עסקה,
מזהה fill בתוך zone לפי quote צדדי, שומר invariant של כמות, ומתייחס לנר
M5 שבו גם stop וגם יעד נגעו כ־`AMBIGUOUS` ולא כמימוש מומצא. זהו שיפור
חשוב על פני backtest כללי. עם זאת, ה־arms שלו קבועים מראש, ה־dollar_pnl
מסומן `None`, ואישור ברוקר נשאר `PENDING_MT5_SPEC_AND_EXECUTION`.

`be_shadow.py` ו־`post_tp3.py` תורמים חוזי תצפית ושמירה על כיוון הסטופ,
אך `post_tp3.py` עצמו מגדיר את המעקב לאחר TP3 כייעוצי בלבד. לכן אף אחד
מהרכיבים אינו פותר את J1/J2 ואינו הופך target hit למילוי או להמלצת ביצוע.

### 8. זרוע ה־CONTROL במקור אינה ה־baseline המאושר של הפרויקט

החלטת המחקר המאושרת מ־2026-09-08 מגדירה `full exit at TP1`, ללא partial,
הוספה, BE או trailing, עבור ניסוי בחירת העסקאות הראשון. לעומתה,
`management_trial.py` מגדיר `CONTROL` כ־25%/25%/50% בשלושה יעדים. שני
הדברים יכולים להיות ניסויי מחקר תקפים, אך הם עונים על שאלות שונות ואסור
לערבב את תוצאותיהם או לקרוא לשניהם אותו baseline.

לכן J3/J4 יחזיקו מזהי policy נפרדים לפחות:

- `fixed_full_tp1_v1` — זרוע הביקורת המאושרת לבחירת עסקאות.
- `chartdesk_management_trial_control_v2` — זרוע מקורית קיימת של partials,
  לשחזור או להשוואת ניהול בלבד.
- כל policy דינמי חדש — מזהה, horizon, assumptions ועלויות נפרדים.

אין בשמות אלה קביעה של מחיר, עלות, סף או פעולה חיה. הם מונעים זליגת label:
למודל בחירת עסקאות אסור ללמוד תוצאת 25%/25%/50% כאילו הייתה תוצאת TP1 מלאה,
ולמודל ניהול אסור להציג את השיפור מול partial-control כשיפור מול baseline
המאושר בלי השוואה מפורשת בשתי הזרועות.

## סדר המיחזור המוצע

1. שומרים את ה־TP1 המלא עם stop מקורי כ־`policy_id` של control, בדיוק לפי
   החלטת המחקר שכבר אושרה.
2. יוצרים חוזה policy נפרד, ללא שיגור פקודות, המייצג פעולות חוקיות ושינויי
   מצב עתידיים. המנהל החדש צורך snapshots סיבתיים ותוצאתו recommendation
   מתועדת; שכבת execution העתידית בלבד ממירה אותה לכוונת פקודה.
3. משתמשים בעקרונות של `manage.py`, `sizing.py`, `policy.py` ו־`backtest.py`
   כמקור לתרחישי בדיקה ולחלופות control, רק לאחר קיבוע גרסת המקור והפרדת
   פרמטרים פתוחים מכללים שנבחרו על ידי שגיב.
4. מרחיבים את חשבונאות ה־replay/כלכלה אחרי J1: עץ ניהול ללא הגדרות HELD,
   BROKEN, כניסה, זמן/חדשות ופעולות מותרות אינו בר־סימולציה.
5. מייצרים training view רק אחרי שהסימולטור מזהה פעולה, כמות, מצב עוקב
   ואופק תוצאה. לייבל סיום העסקה נשאר נפרד מלייבל הפעולה.

## תלות בצוות

שגיב צריך להכריע את משמעות מצבי התזה והפעולות שמהם הם נובעים, כולל דוגמאות
מנוגדות. גרסאות ה־source אומתו מול origin; רועי/יובל צריכים לתעד את בחירת
הרכיבים שימוחזרו ואת מפרט הנכס והברוקר האמיתי לפני J3. אין כאן בקשה
להמציא סף או לבחור פעולה חיה.

## ראיות בדיקה

- `git ls-remote origin` אימת ש־`68b1d...` הוא `main` וש־`e79c3...` הוא
  `codex/roi-handoff-2026-09-07`.
- בעותק audit מבודד: `git show` אימת את שני ה־commits ו־`git diff --stat
  68b1d... e79c3...` החזיר 152 קבצים שהשתנו.
- קריאה ממוקדת של `management_trial.py`, `be_shadow.py`, `post_tp3.py`,
  `manage.py`, `sizing.py`, `policy.py`, `backtest.py`, `strategy.py`, lifecycle
  vendor ports וה־economic contract בוצעה ב־2026-09-14.
- בעותק audit, `pytest tests/test_management_trial.py tests/test_be_shadow.py`
  נתן 24 passed ו־1 failed. הכשל הוא ב־`research_packet._exclusive_write`:
  הוא מנסה `os.open(directory, O_RDONLY)` לצורך fsync של directory, פעולה
  שמחזירה `PermissionError` ב־Windows. probe מינימלי שחזר זאת. 24 הבדיקות
  האחרות עברו; אין להסיק מכשל התאימות הזה כשל ב־partial/BE, ואין בכך הכשרת
  הרכיב למסחר חי.

המסמך אינו הוכחת parity בין גרסאות, בדיקת רווחיות או אישור מנהל פוזיציה.
