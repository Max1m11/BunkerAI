from __future__ import annotations

from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats

from .runtime import bot


PRIVATE_COMMANDS = [
    BotCommand(command="start", description="Открыть инструкцию и свою руку"),
    BotCommand(command="special", description="Посмотреть особое условие"),
    BotCommand(command="vote", description="Открыть приватное голосование"),
]

GROUP_COMMANDS = [
    BotCommand(command="new_game", description="Создать новую партию"),
    BotCommand(command="join", description="Присоединиться к лобби"),
    BotCommand(command="players", description="Показать участников"),
    BotCommand(command="start_game", description="Запустить партию"),
    BotCommand(command="status", description="Показать статус партии"),
    BotCommand(command="reveal", description="Напоминание о раскрытии в личке"),
    BotCommand(command="vote", description="Напоминание о голосовании в личке"),
    BotCommand(command="next", description="Закрыть обсуждение"),
    BotCommand(command="end_game", description="Завершить партию"),
]


async def setup_bot_commands() -> None:
    await bot.set_my_commands(PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(GROUP_COMMANDS, scope=BotCommandScopeAllGroupChats())
