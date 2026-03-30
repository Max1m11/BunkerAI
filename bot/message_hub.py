from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from .database import save_player, update_game
from .game_logic import endgame_state, player_special_state, set_endgame_state, set_player_special_state
from .runtime import bot


UI_STATE_KEY = "_ui"
MESSAGES_KEY = "messages"


def _bad_request_text(exc: TelegramBadRequest) -> str:
    return str(exc).lower()


def _is_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in _bad_request_text(exc)


def _can_fallback_to_send(exc: TelegramBadRequest) -> bool:
    text = _bad_request_text(exc)
    markers = (
        "message to edit not found",
        "message can't be edited",
        "there is no text in the message to edit",
        "message identifier is not specified",
    )
    return any(marker in text for marker in markers)


def _read_ui(data: dict) -> dict:
    return dict(data.get(UI_STATE_KEY) or {})


def _write_ui(data: dict, ui_state: dict) -> dict:
    updated = dict(data)
    if ui_state:
        updated[UI_STATE_KEY] = ui_state
    else:
        updated.pop(UI_STATE_KEY, None)
    return updated


async def _upsert_text_message(chat_id: int, text: str, reply_markup=None, message_id: int | None = None) -> int | None:
    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return message_id
        except TelegramBadRequest as exc:
            if _is_not_modified(exc):
                if reply_markup is not None:
                    try:
                        await bot.edit_message_reply_markup(
                            chat_id=chat_id,
                            message_id=message_id,
                            reply_markup=reply_markup,
                        )
                    except TelegramBadRequest:
                        pass
                return message_id
            if not _can_fallback_to_send(exc):
                raise
        except TelegramForbiddenError:
            return None

    try:
        message = await bot.send_message(chat_id, text, reply_markup=reply_markup)
    except TelegramForbiddenError:
        return None
    return message.message_id


async def _delete_message(chat_id: int, message_id: int | None) -> None:
    if not message_id:
        return
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return


def get_game_ui_value(game, key: str, default=None):
    state = endgame_state(game)
    return _read_ui(state).get(key, default)


async def set_game_ui_value(game, key: str, value) -> None:
    state = endgame_state(game)
    ui_state = _read_ui(state)
    if value is None:
        ui_state.pop(key, None)
    else:
        ui_state[key] = value
    set_endgame_state(game, _write_ui(state, ui_state))
    await update_game(game)


def get_player_ui_value(player, key: str, default=None):
    state = player_special_state(player)
    return _read_ui(state).get(key, default)


async def set_player_ui_value(player, key: str, value) -> None:
    state = player_special_state(player)
    ui_state = _read_ui(state)
    if value is None:
        ui_state.pop(key, None)
    else:
        ui_state[key] = value
    set_player_special_state(player, _write_ui(state, ui_state))
    await save_player(player)


async def upsert_game_message(game, slot: str, text: str, reply_markup=None) -> int | None:
    message_id = get_game_ui_value(game, MESSAGES_KEY, {}).get(slot)
    new_message_id = await _upsert_text_message(game.chat_id, text, reply_markup=reply_markup, message_id=message_id)
    if new_message_id != message_id:
        messages = dict(get_game_ui_value(game, MESSAGES_KEY, {}))
        if new_message_id is None:
            messages.pop(slot, None)
        else:
            messages[slot] = new_message_id
        await set_game_ui_value(game, MESSAGES_KEY, messages or None)
    return new_message_id


async def clear_game_message(game, slot: str) -> None:
    messages = dict(get_game_ui_value(game, MESSAGES_KEY, {}))
    message_id = messages.pop(slot, None)
    await _delete_message(game.chat_id, message_id)
    await set_game_ui_value(game, MESSAGES_KEY, messages or None)


async def upsert_player_message(player, slot: str, text: str, reply_markup=None) -> int | None:
    message_id = get_player_ui_value(player, MESSAGES_KEY, {}).get(slot)
    new_message_id = await _upsert_text_message(player.user_id, text, reply_markup=reply_markup, message_id=message_id)
    if new_message_id != message_id:
        messages = dict(get_player_ui_value(player, MESSAGES_KEY, {}))
        if new_message_id is None:
            messages.pop(slot, None)
        else:
            messages[slot] = new_message_id
        await set_player_ui_value(player, MESSAGES_KEY, messages or None)
    return new_message_id


async def bind_player_message(player, slot: str, message_id: int) -> None:
    messages = dict(get_player_ui_value(player, MESSAGES_KEY, {}))
    if messages.get(slot) == message_id:
        return
    messages[slot] = message_id
    await set_player_ui_value(player, MESSAGES_KEY, messages)


async def clear_player_message(player, slot: str) -> None:
    messages = dict(get_player_ui_value(player, MESSAGES_KEY, {}))
    message_id = messages.pop(slot, None)
    await _delete_message(player.user_id, message_id)
    await set_player_ui_value(player, MESSAGES_KEY, messages or None)
