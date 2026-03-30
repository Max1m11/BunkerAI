from __future__ import annotations

import asyncio
import logging

import uvicorn

from webapp.server import app

from .commands import setup_bot_commands
from .config import settings
from .database import init_db
from .handlers import group, private
from .runtime import bot, dp, scheduler
from .scheduler import restore_game_deadlines

dp.include_router(private.router)
dp.include_router(group.router)


async def start_bot() -> None:
    await init_db()
    await setup_bot_commands()
    if not scheduler.running:
        scheduler.start()
    await restore_game_deadlines()
    await dp.start_polling(bot)


async def start_webapp() -> None:
    config = uvicorn.Config(app=app, host="0.0.0.0", port=settings.webapp_port, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    await asyncio.gather(start_bot(), start_webapp())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
