# OSINT Telegram Bot — Design

Status: Approved for planning
Date: 2026-09-10

## Мета

Telegram-бот на aiogram 3.x, який приймає від користувача номер телефону,
email або юзернейм, паралельно запускає набір OSINT-інструментів, і повертає
готовий, красиво оформлений HTML-звіт (окремий файл-документ).

Ціль встановлення: нуль зовнішньої інфраструктури. `pip install`, `.env`
з токеном, і бот працює локально/на сервері без Docker, без API-ключів,
без ручного обслуговування (за винятком опціонального GHunt).

## Область (scope) v1

Включено:
- Розпізнавання типу запиту: телефон / email / юзернейм
- username → **blackbird** + **maigret** + **sherlock** запускаються паралельно,
  кожен — окрема картка в звіті (тимчасовий "порівняльний" режим — усі три
  перевіряють по суті одне й те саме, тримаємо всі три навмисно, щоб порівняти
  якість результатів наживо; після порівняння користувач вирішує, які лишити,
  окремим циклом змін)
  - **blackbird** (`p1ngul1n0/blackbird`, git clone + `pip install -r requirements.txt`, без API-ключів)
  - **maigret** (`pip install maigret`, без API-ключів для базового пошуку)
  - **sherlock** (`pipx install sherlock-project`, без API-ключів)
- email → **holehe** (`pip install holehe`, без API-ключів) + опціонально **GHunt** (`pipx install ghunt`) для gmail.com-адрес, якщо ввімкнено в налаштуваннях
- phone → **phonenumbers** (`pip install phonenumbers`, чистий Python, без API-ключів; порт Google libphonenumber) — країна, регіон, оператор, тип лінії, валідність, часовий пояс
- HTML-звіт у темній "tactical" стилістиці (Tailwind CDN + inline CSS), надсилається як `.html` документ
- Керування ботом повністю через inline-кнопки (не команди)
- Whitelist-доступ з адмін-панеллю (додавання/видалення юзерів, перемикання режиму доступу, перемикання GHunt) — все через inline-кнопки
- SQLite (aiosqlite) для users/settings
- Історія згенерованих звітів (файли залишаються на диску в `reports/`)

Явно виключено з v1 (можна додати пізніше окремим циклом):
- GHunt: без вбудованого управління авторизацією — адмін один раз локально виконує
  `ghunt login` (через GHunt Companion, браузерне розширення), GHunt сам зберігає
  сесію на машині; бот лише перемикає `settings.ghunt_enabled` (намагатись/не
  намагатись його викликати) і не знає деталей автентифікації
- SpiderFoot, web-check — не включені (SpiderFoot: своя база даних і десятки
  опціональних API-ключів, без яких більшість модулів не працює, суперечить
  вимозі "без гемору"; web-check: для доменів/IP, не для телефону/email/юзернейма)
- Рейт-ліміти по кількості запитів — не потрібні, бо доступ і так через whitelist
- Веб-хостинг / webhook-режим — бот працює через polling

## Архітектура

Один Python-процес (asyncio). Основні шари:

```
bot/
  main.py              # entrypoint, aiogram Dispatcher, polling
  config.py            # читання .env (BOT_TOKEN, ADMIN_ID)
  db.py                 # aiosqlite: users, settings
  keyboards.py          # усі InlineKeyboardMarkup білдери
  handlers/
    start.py             # /start, головне меню
    search.py             # FSM: очікування запиту -> розпізнавання типу -> запуск інструментів -> звіт
    admin.py              # inline-адмінка: users, mode, ghunt toggle
  osint/
    detect.py             # визначення типу запиту (phone/email/username)
    runners/
      blackbird.py         # subprocess-обгортка, парсинг json
      maigret.py            # subprocess-обгортка, парсинг json
      sherlock.py            # subprocess-обгортка, парсинг csv
      holehe.py             # subprocess-обгортка, парсинг csv
      phone.py              # прямий виклик phonenumbers (без subprocess)
      ghunt.py              # subprocess-обгортка (умовно, якщо увімкнено в settings)
  report/
    template.html.j2      # Jinja2-шаблон звіту (tactical dark theme)
    render.py              # збірка контексту з результатів -> рендер -> запис файлу
reports/                  # згенеровані .html-звіти (persist)
data/
  bot.sqlite3             # users, settings
.env.example
requirements.txt
README.md                 # інструкція встановлення, включно з git clone blackbird, ghunt login
```

## Дані

**SQLite таблиці:**

```sql
CREATE TABLE users (
    telegram_id INTEGER PRIMARY KEY,
    added_at TEXT NOT NULL,
    added_by INTEGER NOT NULL
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- settings: access_mode = 'open' | 'whitelist' (default 'whitelist')
--           ghunt_enabled = 'true' | 'false' (default 'false')
```

Адмін (`ADMIN_ID` з `.env`) завжди має доступ незалежно від режиму й таблиці
users; в `users` потрапляють лише додані ним інші люди.

## UX / навігація (inline-кнопки, без команд)

Єдина команда: `/start`.

**Головне меню** (`InlineKeyboardMarkup`):
- 🔍 Новий пошук
- 📄 Мої звіти
- ⚙️ Налаштування *(тільки якщо `user_id == ADMIN_ID`)*

**Пошук** (FSM state `waiting_for_query`):
1. Користувач тисне "🔍 Новий пошук"
2. Бот: "Надішли номер телефону, email або юзернейм"
3. Користувач надсилає текст (єдине місце вводу тексту для самого запиту)
4. `osint/detect.py` визначає тип
5. Якщо у користувача вже є активний запит в обробці — бот відповідає "Зачекай, попередній запит ще виконується" і не запускає новий
6. Бот редагує повідомлення в "⏳ Виконується..." (опційно з переліком інструментів, що запущені)
7. `asyncio.gather` запускає релевантні runner'и з timeout ~120с кожен
8. Кожен runner: успіх → структуровані дані; помилка/timeout → позначка "недоступно" в цьому блоці звіту, решта не блокується
9. `report/render.py` збирає контекст, рендерить `.html`, зберігає в `reports/<telegram_id>/<timestamp>_<query>.html`
10. Бот надсилає файл як документ

**Мої звіти**: список останніх файлів користувача (inline-кнопки з датою/запитом), тиск на кнопку — бот пересилає той файл повторно.

**Налаштування (адмін)**:
- 👥 Користувачі → список, навпроти кожного ❌ (callback `deluser:<id>`); внизу "➕ Додати" → FSM `waiting_for_new_user_id` → адмін надсилає ID текстом → додається в `users`
- Кнопка-перемикач режиму: "🔓 Режим: Відкритий" / "🔒 Режим: Whitelist" (тиск міняє `settings.access_mode`)
- Кнопка-перемикач: "GHunt: 🟢 Увімкнено" / "GHunt: 🔴 Вимкнено" (тиск міняє `settings.ghunt_enabled`; якщо `ghunt` на машині не залогінений — виклик просто впаде як звичайна помилка runner'а і позначиться "недоступно" в звіті, окремої перевірки наявності сесії бот не робить)
- ⬅️ Назад

## Інструменти — деталі інтеграції

Всі запускаються в ізольованій тимчасовій директорії на запит (`tempfile.mkdtemp()`),
щоб паралельні запити різних юзерів не тереблись у output-файлах.

**blackbird** (username):
```
python blackbird.py --username <query> --json --output-dir <tmp_dir>
```
Читаємо згенерований `*.json`, парсимо список знайдених сервісів (service name + link),
формат вже підтверджено (`src/modules/export/json.py` — прямий `json.dump(results, ...)`).

**maigret** (username):
```
maigret <query> -J simple -fo <tmp_dir> --no-progressbar --no-color
```
Читаємо `<tmp_dir>/report_<query>_simple.json`, парсимо список знайдених сайтів.
Прапорці підтверджені по джерелу (`maigret.py`: `-J/--json TYPE`, `-fo/--folderoutput`).

**sherlock** (username):
```
sherlock <query> --csv --folderoutput <tmp_dir> --timeout 60
```
Читаємо `<tmp_dir>/<query>.csv`, парсимо колонки (site, url, status). Прапорці
підтверджені по джерелу (`sherlock.py`: `--csv`, `--json` там — це НЕ вивід
результатів, а завантаження стороннього файла з переліком сайтів для перевірки,
тому для результатів використовуємо `--csv`, а не `--json`).

**holehe** (email):
```
holehe <query> --csv --no-color
```
Читаємо згенерований `holehe_*_<email>_results.csv`, парсимо колонки
(name, exists, rateLimit, emailrecovery, phoneNumber, others).

**GHunt** (email, тільки gmail.com і якщо `ghunt_enabled=true` в settings):
```
ghunt email <query> --json <tmp_dir>/ghunt_result.json
```
Читаємо `ghunt_result.json`. Якщо `ghunt` не залогінений на машині (`ghunt login`
не виконувався) — subprocess завершиться помилкою, обробляється як звичайний
provider failure ("недоступно" в звіті), без окремої перевірки стану сесії.

**phonenumbers** (phone) — без subprocess, прямий Python-виклик у процесі бота:
```python
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
num = phonenumbers.parse(query, None)
# valid, region, carrier_name, line_type, timezones
```

## Звіт (report/render.py + template.html.j2)

Jinja2-шаблон за мотивами наданого прикладу (`report_mrmozozavr.html`) —
темна "tactical" тема, JetBrains Mono, картки на кожен інструмент — але:
- точніші дані (реальні результати з JSON/CSV, не заглушки)
- блок інструмента, який не запускався для цього типу запиту, взагалі не рендериться
  (а не залишається порожнім, як у прикладі)
- блок інструмента, що впав/timeout — показує позначку "недоступно" замість тиші

Контекст рендера: query, query_type, timestamp, список карток
`{tool_name, status: ok|failed|skipped, items: [...]}`.

## Обробка помилок

- Невалідний ввід (не схоже ні на телефон, ні на email, ні на прийнятний юзернейм) —
  бот пояснює і просить повторити, не запускає інструменти
- Один інструмент впав — позначка в звіті, інші продовжують
- Немає доступу (не адмін, не в whitelist, режим `whitelist`) — бот ввічливо відмовляє на `/start`
- Одночасний повторний запит від того ж юзера — блокується до завершення першого

## Тестування

- Юніт-тести: `osint/detect.py` (розпізнавання типу — таблиця кейсів), парсери
  результатів blackbird/maigret/sherlock/holehe (на фікстурних json/csv файлах,
  без реального виклику інструмента), рендер шаблону (snapshot на фікстурному контексті)
- Ручна перевірка: повний цикл на власному username/email/номері з реального бота,
  включно з admin-flow (додавання/видалення юзера, перемикачі)
