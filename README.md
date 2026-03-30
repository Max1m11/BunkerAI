# BunkerAI

Локальный Telegram-бот с MiniApp для партии в стиле `Бункер 3.x/3.3`.

Проект поднимает:
- Telegram-бота на `aiogram`
- MiniApp/API на `FastAPI`
- таймеры фаз через `APScheduler`
- локальную SQLite-базу

## Что реализовано

- 2 режима: `basic_final` и `survival_story`
- 6 карт персонажа: `biology`, `profession`, `health`, `hobby`, `luggage`, `fact`
- отдельная карта `special_condition`
- 5-раундовый цикл игры
- обязательное раскрытие профессии в 1-м раунде
- тайное голосование в личных сообщениях
- перевыбор при ничьей
- отдельная сторона изгнанных с общим голосом
- MiniApp с публичным состоянием партии

## Требования

- Python 3.11+
- Telegram-бот токен
- публичный URL для MiniApp, если хотите открывать веб-часть из Telegram

## Быстрый запуск

1. Создайте виртуальное окружение:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Установите зависимости:

```powershell
python -m pip install -U pip
python -m pip install -r requirements.txt
```

3. Создайте `.env` на основе примера:

```powershell
Copy-Item .env.example .env
```

4. Заполните обязательные переменные в `.env`:

- `BOT_TOKEN` — токен Telegram-бота
- `WEBAPP_URL` — внешний URL MiniApp, например через `ngrok`

Опционально:
- `AI_API_KEY`
- `AI_PROVIDER`
- `AI_MODEL`
- `DB_PATH`
- `DISCUSSION_MINUTES`
- `VOTING_MINUTES`
- `MIN_PLAYERS`
- `MAX_PLAYERS`

5. Запустите проект:

```powershell
python -m bot.main
```

После запуска:
- бот начнёт polling Telegram
- FastAPI MiniApp поднимется на `http://127.0.0.1:8000` или на порту из `WEBAPP_PORT`

## MiniApp локально

Если хотите просто открыть веб-часть локально в браузере:

```powershell
uvicorn webapp.server:app --host 127.0.0.1 --port 8000
```

Но для открытия MiniApp из Telegram нужен внешний `WEBAPP_URL`.

## Тесты

```powershell
python -m pytest -q
```

## Структура проекта

- [bot/main.py](c:/Users/max/projects/BunkerAI/bot/main.py) — входная точка
- [bot/game_logic.py](c:/Users/max/projects/BunkerAI/bot/game_logic.py) — основная логика игры
- [bot/handlers/group.py](c:/Users/max/projects/BunkerAI/bot/handlers/group.py) — команды группы
- [bot/handlers/private.py](c:/Users/max/projects/BunkerAI/bot/handlers/private.py) — личные сообщения
- [webapp/server.py](c:/Users/max/projects/BunkerAI/webapp/server.py) — FastAPI и API MiniApp
- [tests/test_game_logic.py](c:/Users/max/projects/BunkerAI/tests/test_game_logic.py) — тесты игровой логики
- [tests/test_webapp.py](c:/Users/max/projects/BunkerAI/tests/test_webapp.py) — тесты MiniApp/API

## Полезные команды

Запуск тестов:

```powershell
python -m pytest -q
```

Проверка импорта и синтаксиса:

```powershell
python -m compileall bot webapp tests
```

## Статус

Сейчас это локальный проект без настроенного remote-origin. Если позже появится `gh` или GitHub token/API-доступ в сессии, удалённый репозиторий можно создать отдельно за пару команд.
