from __future__ import annotations

import logging
import uuid

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..actions import close_discussion_and_announce, force_finish_and_announce, start_game_and_announce
from ..callbacks import JoinGameCallback, NextPhaseCallback, SetModeCallback
from ..cards import get_random_scenario
from ..database import create_game, get_active_game_by_chat, get_game, get_players
from ..game_logic import (
    GameLogicError,
    add_player_to_lobby,
    alive_players,
    choose_game_mode,
    current_vote_state,
    ensure_active_chat_game,
    exiled_players,
    opened_bunker_cards,
    opened_threat_cards,
)
from ..keyboards import get_group_panel_kb, get_lobby_kb, get_webapp_kb
from ..message_hub import get_game_ui_value, set_game_ui_value, upsert_game_message
from ..models import Game
from ..strings import (
    game_status_text,
    group_reveal_redirect_text,
    group_vote_redirect_text,
    lobby_card_text,
    lobby_players_text,
    new_game_text,
    player_status_badge,
    safe,
)

router = Router()
logger = logging.getLogger(__name__)


def _is_host(user_id: int, game: Game) -> bool:
    return user_id == game.host_id


def _players_overview(players: list) -> str:
    if not players:
        return "В партии пока нет участников."

    lines = ["<b>Участники партии</b>"]
    for index, player in enumerate(players, start=1):
        username = f" (@{player.username})" if player.username else ""
        lines.append(f"{index}. {safe(player.full_name)}{safe(username)} — {player_status_badge(player)}")
    return "\n".join(lines)


@router.message(Command("new_game"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_new_game(message: Message):
    active = await get_active_game_by_chat(message.chat.id)
    if active:
        await message.answer("В этом чате уже есть активная партия. Завершите её через /end_game.")
        return

    scenario = get_random_scenario()
    title = f"{scenario['emoji']} {scenario['title']}"
    game = Game(
        id=str(uuid.uuid4()),
        chat_id=message.chat.id,
        mode="basic_final",
        scenario_id=scenario["id"],
        scenario_title=title,
        scenario_hint=scenario["hint"],
        phase="lobby",
        phase_step="lobby",
        round=0,
        round_limit=5,
        host_id=message.from_user.id,
        slots=0,
        catastrophe_id=scenario["id"],
        catastrophe_title=title,
        catastrophe_text=scenario["text"],
        phase_deadline_at=None,
        created_at=message.date.isoformat(),
        updated_at=message.date.isoformat(),
    )
    await create_game(game)
    await set_game_ui_value(game, "initiator_name", message.from_user.full_name)
    await upsert_game_message(
        game,
        "main",
        lobby_card_text(game, message.from_user.full_name, []),
        reply_markup=get_lobby_kb(game.id, game.mode),
    )


@router.message(Command("join"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_join(message: Message):
    try:
        game = await ensure_active_chat_game(message.chat.id)
        await add_player_to_lobby(game, message.from_user.id, message.from_user.username, message.from_user.full_name)
    except GameLogicError as exc:
        await message.answer(str(exc))
        return

    players = await get_players(game.id)
    initiator_name = get_game_ui_value(game, "initiator_name", message.from_user.full_name)
    await upsert_game_message(
        game,
        "main",
        lobby_card_text(game, initiator_name, players),
        reply_markup=get_lobby_kb(game.id, game.mode),
    )


@router.callback_query(JoinGameCallback.filter())
async def cb_join_game(call: CallbackQuery, callback_data: JoinGameCallback):
    game = await get_game(callback_data.game_id)
    if not game or game.phase != "lobby":
        await call.answer("Лобби уже закрыто.", show_alert=True)
        return

    try:
        await add_player_to_lobby(game, call.from_user.id, call.from_user.username, call.from_user.full_name)
    except GameLogicError as exc:
        await call.answer(str(exc), show_alert=True)
        return

    players = await get_players(game.id)
    await call.answer("Вы присоединились к партии.")
    initiator_name = get_game_ui_value(game, "initiator_name", call.from_user.full_name)
    await upsert_game_message(
        game,
        "main",
        lobby_card_text(game, initiator_name, players),
        reply_markup=get_lobby_kb(game.id, game.mode),
    )


@router.callback_query(SetModeCallback.filter())
async def cb_set_mode(call: CallbackQuery, callback_data: SetModeCallback):
    try:
        game = await choose_game_mode(callback_data.game_id, call.from_user.id, callback_data.mode)
    except GameLogicError as exc:
        await call.answer(str(exc), show_alert=True)
        return

    players = await get_players(game.id)
    initiator_name = get_game_ui_value(game, "initiator_name", call.from_user.full_name)
    await upsert_game_message(
        game,
        "main",
        lobby_card_text(game, initiator_name, players),
        reply_markup=get_lobby_kb(game.id, game.mode),
    )
    await call.answer("Режим обновлён.")


@router.message(Command("players"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_players(message: Message):
    try:
        game = await ensure_active_chat_game(message.chat.id)
    except GameLogicError as exc:
        await message.answer(str(exc))
        return

    players = await get_players(game.id)
    text = lobby_players_text(players) if game.phase == "lobby" else _players_overview(players)
    await message.answer(text)


@router.message(Command("start_game"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_start_game(message: Message):
    try:
        game = await ensure_active_chat_game(message.chat.id)
    except GameLogicError as exc:
        await message.answer(str(exc))
        return

    if not _is_host(message.from_user.id, game):
        await message.answer("Запустить партию может только инициатор лобби.")
        return

    try:
        await start_game_and_announce(game.id)
    except GameLogicError as exc:
        await message.answer(str(exc))
    except Exception:
        logger.exception("Failed to start game %s", game.id)
        await message.answer("Игра стартовала с ошибкой обновления сообщений. Попробуйте /status и /start в личке, если нужно восстановить интерфейс.")


@router.message(Command("reveal"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_reveal(message: Message):
    await message.answer(group_reveal_redirect_text())


@router.message(Command("vote"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_vote(message: Message):
    try:
        game = await ensure_active_chat_game(message.chat.id)
    except GameLogicError as exc:
        await message.answer(str(exc))
        return

    if game.phase != "voting":
        await message.answer("Сейчас тайное голосование не открыто.")
        return

    players = await get_players(game.id)
    vote_state = current_vote_state(game, players)
    await message.answer(
        group_vote_redirect_text(
            game,
            vote_state["ballot_index"],
            vote_state["ballot_total"],
            revote=vote_state["revote"],
        )
    )


@router.message(Command("next"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_next(message: Message):
    try:
        game = await ensure_active_chat_game(message.chat.id)
    except GameLogicError as exc:
        await message.answer(str(exc))
        return

    if not _is_host(message.from_user.id, game):
        await message.answer("Закрыть обсуждение может только инициатор лобби.")
        return

    try:
        await close_discussion_and_announce(game.id)
    except GameLogicError as exc:
        await message.answer(str(exc))
    except Exception:
        logger.exception("Failed to close discussion for game %s", game.id)
        await message.answer("Фаза сменилась с ошибкой обновления сообщений. Попробуйте /status.")


@router.callback_query(NextPhaseCallback.filter())
async def cb_next_phase(call: CallbackQuery, callback_data: NextPhaseCallback):
    game = await get_game(callback_data.game_id)
    if not game or game.phase == "finished":
        await call.answer("Партия уже завершена.", show_alert=True)
        return
    if not _is_host(call.from_user.id, game):
        await call.answer("Закрыть обсуждение может только инициатор лобби.", show_alert=True)
        return

    try:
        await close_discussion_and_announce(game.id)
    except GameLogicError as exc:
        await call.answer(str(exc), show_alert=True)
        return
    except Exception:
        logger.exception("Failed to close discussion from callback for game %s", game.id)
        await call.answer("Не удалось обновить сообщения после смены фазы.", show_alert=True)
        return

    await call.answer("Обсуждение закрыто.")


@router.message(Command("status"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_status(message: Message):
    try:
        game = await ensure_active_chat_game(message.chat.id)
    except GameLogicError as exc:
        await message.answer(str(exc))
        return

    players = await get_players(game.id)
    await upsert_game_message(
        game,
        "main",
        game_status_text(
            game,
            len(alive_players(players)),
            len(exiled_players(players)),
            opened_bunker_cards(game),
            opened_threat_cards(game),
        ),
        reply_markup=get_group_panel_kb(game.id, can_advance=game.phase == "discussion"),
    )


@router.message(Command("end_game"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_end_game(message: Message):
    try:
        game = await ensure_active_chat_game(message.chat.id)
    except GameLogicError as exc:
        await message.answer(str(exc))
        return

    if not _is_host(message.from_user.id, game):
        await message.answer("Завершить партию может только инициатор лобби.")
        return

    try:
        await force_finish_and_announce(game.id)
    except GameLogicError as exc:
        await message.answer(str(exc))
