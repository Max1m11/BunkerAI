# SPEC: Telegram Bot «Бункер» (@BunkerGameBot)

## Цель
Telegram-бот для групповой игры «Бункер». Управление — через команды и inline-кнопки в чате/ЛС. Информация (карточки игроков, статус игры) — через Telegram MiniApp (WebApp), который бот открывает кнопкой. MiniApp — только для чтения, без управления.

---

## Стек

- **Python 3.11+**
- **aiogram 3.x** — Telegram Bot API
- **SQLite + aiosqlite** — хранилище (простота деплоя; легко мигрировать на PostgreSQL)
- **FastAPI + uvicorn** — сервер для MiniApp (отдаёт HTML/JSON)
- **Jinja2** — шаблоны MiniApp
- **APScheduler** — таймеры фаз (обсуждение, голосование)
- **httpx** — запросы к Anthropic API (AI-судья)
- **python-dotenv** — конфиг
- **Pillow** — не используется (заменено MiniApp)

---

## Файловая структура

```
bunker_bot/
├── bot/
│   ├── __init__.py
│   ├── main.py              # Точка входа, запуск бота + FastAPI
│   ├── config.py            # Настройки из .env
│   ├── database.py          # Инициализация SQLite, CRUD
│   ├── models.py            # Dataclasses / TypedDict схемы
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── group.py         # Команды в группе (/start_game, /join, /vote...)
│   │   └── private.py       # ЛС: показ карточки, кнопки раскрытия
│   ├── keyboards.py         # Все inline/reply клавиатуры
│   ├── game_logic.py        # Раздача карт, фазы, голосование, победа
│   ├── cards.py             # База характеристик (генерация карточки игрока)
│   └── ai_judge.py          # Запрос к Claude API для финального вердикта
├── webapp/
│   ├── server.py            # FastAPI роуты: /webapp/{game_id}, /api/game/{game_id}
│   ├── templates/
│   │   ├── base.html        # Базовый шаблон с Telegram WebApp JS SDK
│   │   ├── game.html        # Главная страница: все игроки + их открытые карты
│   │   └── player.html      # Карточка одного игрока (детально)
│   └── static/
│       └── style.css        # Тёмная тема под Telegram
├── .env.example
├── requirements.txt
└── README.md
```

---

## База данных (SQLite)

### Таблица `games`
```sql
CREATE TABLE games (
    id          TEXT PRIMARY KEY,   -- uuid4
    chat_id     INTEGER NOT NULL,   -- Telegram chat_id группы
    scenario    TEXT NOT NULL,      -- Сценарий апокалипсиса
    phase       TEXT NOT NULL,      -- lobby | discussion | voting | finished
    round       INTEGER DEFAULT 0,
    host_id     INTEGER NOT NULL,   -- user_id создателя
    slots       INTEGER NOT NULL,   -- сколько мест в бункере (ceil(players/2))
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
```

### Таблица `players`
```sql
CREATE TABLE players (
    id              TEXT PRIMARY KEY,  -- uuid4
    game_id         TEXT NOT NULL REFERENCES games(id),
    user_id         INTEGER NOT NULL,  -- Telegram user_id
    username        TEXT,
    full_name       TEXT NOT NULL,
    is_alive        INTEGER DEFAULT 1, -- 1 = в игре, 0 = выгнан
    in_bunker       INTEGER DEFAULT 0, -- 1 = победил
    cards           TEXT NOT NULL,     -- JSON: {profession, health, age_gender, hobby, phobia, luggage, fact, special}
    revealed        TEXT DEFAULT '[]'  -- JSON: список раскрытых ключей карточки
);
```

### Таблица `votes`
```sql
CREATE TABLE votes (
    id          TEXT PRIMARY KEY,
    game_id     TEXT NOT NULL REFERENCES games(id),
    round       INTEGER NOT NULL,
    voter_id    INTEGER NOT NULL,   -- user_id голосующего
    target_id   INTEGER NOT NULL,  -- user_id цели
    created_at  TEXT NOT NULL
);
```

---

## Карточка игрока (`cards.py`)

Каждая характеристика — случайный выбор из предопределённого списка. Структура:

```python
CARD_KEYS = [
    "profession",   # Профессия
    "health",       # Здоровье / болезнь
    "age_gender",   # Возраст и пол
    "hobby",        # Хобби
    "phobia",       # Фобия
    "luggage",      # Багаж (1 предмет)
    "fact",         # Особый факт о себе
    "special",      # Спецспособность (редкая, не у всех)
]
```

Функция `generate_card() -> dict` возвращает словарь с одним случайным значением на каждый ключ.

Примеры значений (минимум 30 на каждый ключ в `cards.py`):
- **profession**: Хирург, Агроном, Инженер-ядерщик, Повар, Психолог, Военный, Учитель, Программист, Механик...
- **health**: Абсолютно здоров, Астма, Диабет 2 типа, ВИЧ+, Беременна (7 мес.), Потеря слуха, Слепота на 1 глаз...
- **hobby**: Огородничество, Стрельба, Медицина (самоучка), Радиолюбительство, Кулинария...
- **phobia**: Клаустрофобия, Арахнофобия, Социофобия, Нет фобий...
- **luggage**: Набор хирурга, 10 кг семян, Генератор, Библия, Ноутбук, АК-47 + 2 магазина...
- **special**: (30% шанс иметь) Может посмотреть карту другого игрока; Может поменяться 1 картой; Иммунитет к 1 голосованию...

---

## Сценарии апокалипсиса (`cards.py`)

```python
SCENARIOS = [
    {"name": "Ядерная война", "emoji": "☢️", "hint": "Радиация снаружи 500 лет. Нужны: медик, инженер, агроном."},
    {"name": "Пандемия", "emoji": "🦠", "hint": "Смертельный вирус. Нужен: врач, иммунолог. Опасны: инфицированные."},
    {"name": "Зомби-апокалипсис", "emoji": "🧟", "hint": "Нужны: военный, психолог. Опасны: трусы и паникёры."},
    {"name": "Глобальный потоп", "emoji": "🌊", "hint": "Нужны: рыбак, инженер. Бесполезны: офисные работники."},
    {"name": "Ледниковый период", "emoji": "🧊", "hint": "Нужны: охотник, геолог. Важно: физическое здоровье."},
    {"name": "Падение астероида", "emoji": "☄️", "hint": "Хаос и паника. Нужны: лидер, психолог, военный."},
]
```

---

## Игровые фазы и логика (`game_logic.py`)

### Фазы
```
lobby → discussion → voting → [следующий раунд или finished]
```

### Переходы

**lobby** → Игроки регистрируются через `/join`. Хост запускает `/start_game`.  
При старте: перемешать игроков, раздать карточки, задать сценарий, вычислить `slots = ceil(N/2)`.

**discussion** (5 минут таймер):  
- Каждый игрок в ЛС нажимает кнопку «Открыть характеристику» → выбирает одну из нераскрытых.  
- Бот в группу: `«[Имя] открыл: Профессия — Хирург»`  
- По истечении таймера или `/next` от хоста → переход в voting.

**voting**:  
- Бот публикует inline-клавиатуру: список живых игроков.  
- Каждый живой игрок голосует 1 раз (кнопка в группе или ЛС).  
- После всех голосов (или таймер 2 мин) → подсчёт.  
- Игрок с большинством голосов → `is_alive = 0`, бот открывает ВСЕ его карты.  
- Проверка победы (см. ниже) → если нет, следующий раунд.

**finished**:  
- Объявление победителей.  
- Запрос к AI-судье (если включён в .env).

### Проверка победы
```python
def check_victory(game_id) -> str | None:
    alive = get_alive_players(game_id)
    if len(alive) <= game.slots:
        return "bunker_filled"   # Победа — бункер укомплектован
    if len(alive) == 0:
        return "everyone_dead"   # Технически невозможно, но страховка
    return None  # Игра продолжается
```

Дополнительные условия поражения (проверяются при `bunker_filled`):
- Нет ни одного медика/врача → штраф-предупреждение от AI-судьи
- Все игроки одного пола → предупреждение
- Есть инфекционная болезнь без врача → катастрофа

---

## Команды бота

### В группе
| Команда | Описание |
|---|---|
| `/new_game` | Создать лобби |
| `/join` | Вступить в игру |
| `/players` | Список участников |
| `/start_game` | Начать (только хост, мин. 4 игрока) |
| `/reveal` | Открыть характеристику (редирект в ЛС) |
| `/vote @username` | Проголосовать за выбывание |
| `/next` | Перейти к голосованию (только хост) |
| `/status` | Текущий статус игры + кнопка MiniApp |
| `/end_game` | Принудительно завершить (только хост) |

### В ЛС
| Команда / Кнопка | Описание |
|---|---|
| `/start` | Показать свою карточку |
| `[Открыть характеристику]` | Inline-кнопки для раскрытия карт |
| `[📱 Смотреть игру]` | Открыть MiniApp |

---

## MiniApp (WebApp)

### Что это
Веб-страница, которую Telegram открывает внутри приложения. Бот отправляет кнопку типа `WebAppInfo` с URL `https://yourdomain.com/webapp/{game_id}`.

### Страницы

**`/webapp/{game_id}`** — главная (game.html):
- Сценарий апокалипсиса (название + описание)
- Прогресс: Осталось мест в бункере N/M
- Список всех игроков:
  - Имя
  - Статус: 🟢 В игре / 🔴 Выбыл / 🏆 В бункере
  - Раскрытые характеристики: `Профессия: Хирург | Хобби: Огородничество`
  - Нераскрытые: `🔒 🔒 🔒`
  - Кнопка → переход на `/webapp/{game_id}/player/{player_id}`

**`/webapp/{game_id}/player/{player_id}`** — карточка игрока (player.html):
- Имя, статус
- Все раскрытые характеристики (красиво, по одной на строку с эмодзи)
- Нераскрытые — замочек

### API для MiniApp
```
GET /api/game/{game_id}
→ JSON: {scenario, phase, round, slots, players: [{id, name, is_alive, in_bunker, revealed_cards: {key: value}}]}

GET /api/game/{game_id}/player/{player_id}
→ JSON: {name, is_alive, in_bunker, revealed_cards: {key: value}, hidden_count: int}
```

### Стиль MiniApp
- Тёмная тема, переменные из `window.Telegram.WebApp.themeParams`
- Адаптив под мобильный
- Автообновление каждые 10 секунд (polling `/api/game/{game_id}`)
- Без кнопок управления игрой — только чтение

---

## AI-судья (`ai_judge.py`)

Вызывается после завершения игры. Делает запрос к Anthropic API.

```python
async def get_verdict(scenario: str, survivors: list[dict]) -> str:
    """
    survivors: [{name, profession, health, hobby, luggage, fact}]
    Возвращает текст вердикта от Claude.
    """
    prompt = f"""
Сценарий апокалипсиса: {scenario}

Выжившие в бункере:
{format_survivors(survivors)}

Оцени шансы этой группы на выживание через 10 лет. 
Учти: профессии, здоровье, возраст, хобби, багаж.
Укажи сильные стороны группы, слабые стороны и итоговый вердикт одним предложением.
Ответ на русском, не более 200 слов.
"""
    # httpx POST к https://api.anthropic.com/v1/messages
    # model: claude-sonnet-4-20250514
    # max_tokens: 400
```

Если `ANTHROPIC_API_KEY` не задан в `.env` → пропустить, не ломать игру.

---

## .env.example

```env
BOT_TOKEN=your_telegram_bot_token
ANTHROPIC_API_KEY=your_anthropic_key   # опционально
WEBAPP_URL=https://yourdomain.com       # публичный URL FastAPI сервера
WEBAPP_PORT=8000
DB_PATH=./bunker.db
DISCUSSION_MINUTES=5
VOTING_MINUTES=2
MIN_PLAYERS=4
MAX_PLAYERS=12
```

---

## Ключевые требования к реализации

1. **Один бот = один процесс**: aiogram polling + FastAPI запускаются вместе через `asyncio.gather`.
2. **Все состояния — в БД**, не в памяти. Бот должен переживать перезапуск.
3. **MiniApp не требует авторизации** — данные публичны в рамках game_id (UUID достаточно для защиты).
4. **Голосование — анонимно** в публичном чате. Итоги объявляются только после завершения голосования.
5. **Таймеры** через APScheduler: при рестарте — проверять активные игры и восстанавливать джобы.
6. **Один активный game_id на группу** — нельзя запустить вторую игру пока идёт первая.
7. **Локализация**: весь текст на русском, вынести в отдельный файл `strings.py`.

---

## Порядок разработки (рекомендуемый)

1. `database.py` — схема и CRUD
2. `cards.py` — базы данных характеристик и функция генерации
3. `game_logic.py` — логика фаз без Telegram
4. `handlers/group.py` — базовые команды (new_game, join, start_game)
5. `handlers/private.py` — карточка в ЛС, раскрытие
6. `keyboards.py` — все клавиатуры
7. `webapp/server.py` + шаблоны — MiniApp
8. `ai_judge.py` — финальный вердикт
9. Таймеры, edge cases, тесты
