from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from ..actions import finish_voting_and_announce, reveal_trait_and_announce, use_special_and_announce
from ..callbacks import CardViewCallback, RevealTraitCallback, SpecialMenuCallback, SpecialUseCallback, VoteCallback
from ..database import get_active_player_by_user, get_game, get_player, get_players
from ..game_logic import (
    GameLogicError,
    current_vote_state,
    player_cards,
    player_condition,
    player_special_state,
    revealed_keys,
    submit_vote,
)
from ..keyboards import get_reveal_kb, get_special_kb, get_vote_kb
from ..message_hub import bind_player_message, clear_player_message, upsert_player_message
from ..strings import (
    private_hand_text,
    private_lobby_wait_text,
    private_start_intro_text,
    private_vote_prompt,
    special_condition_text,
    vote_saved_text,
)

router = Router()


async def _active_or_message(user_id: int, message: Message):
    active = await get_active_player_by_user(user_id)
    if not active:
        await message.answer(private_start_intro_text())
        return None
    return active


def _reveal_markup(game, player):
    return get_reveal_kb(
        player,
        game.phase,
        game.round,
        condition=player_condition(player),
        game=game,
    )


async def _send_vote_prompt(message: Message, game, player, players: list) -> None:
    if game.phase != "voting" or player.faction_status not in {"alive", "exiled"}:
        await clear_player_message(player, "vote")
        return
    vote_state = current_vote_state(game, players)
    await upsert_player_message(
        player,
        "vote",
        private_vote_prompt(
            game,
            vote_state["ballot_index"],
            vote_state["ballot_total"],
            revote=vote_state["revote"],
        ),
        reply_markup=get_vote_kb(players, game.id, candidate_ids=vote_state["candidate_ids"], game=game),
    )


async def _render_card_message(message: Message, game, player, players: list | None = None):
    await upsert_player_message(
        player,
        "hand",
        private_hand_text(
            game,
            player,
            player_cards(player),
            player_condition(player),
            revealed_keys(player),
            player_special_state(player),
        ),
        reply_markup=_reveal_markup(game, player),
    )
    if players is None:
        players = await get_players(game.id)
    await _send_vote_prompt(message, game, player, players)


async def _edit_card(call: CallbackQuery, game, player):
    await bind_player_message(player, "hand", call.message.message_id)
    await call.message.edit_text(
        private_hand_text(
            game,
            player,
            player_cards(player),
            player_condition(player),
            revealed_keys(player),
            player_special_state(player),
        ),
        reply_markup=_reveal_markup(game, player),
    )


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start_private(message: Message):
    active = await _active_or_message(message.from_user.id, message)
    if not active:
        return

    game, player = active
    if game.phase == "lobby":
        await upsert_player_message(
            player,
            "hand",
            private_lobby_wait_text(),
            reply_markup=get_reveal_kb(player, game.phase, game.round, game=game),
        )
        await clear_player_message(player, "vote")
        return

    players = await get_players(game.id)
    await _render_card_message(message, game, player, players)


@router.message(Command("special"), F.chat.type == "private")
async def cmd_special(message: Message):
    active = await _active_or_message(message.from_user.id, message)
    if not active:
        return

    game, player = active
    players = await get_players(game.id)
    await upsert_player_message(
        player,
        "special",
        special_condition_text(player_condition(player), player_special_state(player)),
        reply_markup=get_special_kb(player, game, players),
    )


@router.message(Command("vote"), F.chat.type == "private")
async def cmd_vote_private(message: Message):
    active = await _active_or_message(message.from_user.id, message)
    if not active:
        return

    game, player = active
    players = await get_players(game.id)
    if game.phase != "voting":
        await upsert_player_message(player, "vote", "Сейчас тайное голосование не открыто.")
        return
    await _send_vote_prompt(message, game, player, players)


@router.callback_query(CardViewCallback.filter())
async def callback_card_view(call: CallbackQuery, callback_data: CardViewCallback):
    player = await get_player(callback_data.game_id, call.from_user.id)
    game = await get_game(callback_data.game_id)
    if not player or not game:
        await call.answer("Не удалось обновить карточку.", show_alert=True)
        return

    await _edit_card(call, game, player)
    await call.answer()


@router.callback_query(SpecialMenuCallback.filter())
async def callback_special_menu(call: CallbackQuery, callback_data: SpecialMenuCallback):
    player = await get_player(callback_data.game_id, call.from_user.id)
    game = await get_game(callback_data.game_id)
    if not player or not game:
        await call.answer("Не удалось открыть особое условие.", show_alert=True)
        return

    players = await get_players(game.id)
    await bind_player_message(player, "special", call.message.message_id)
    await call.message.edit_text(
        special_condition_text(player_condition(player), player_special_state(player)),
        reply_markup=get_special_kb(player, game, players),
    )
    await call.answer()


@router.callback_query(SpecialUseCallback.filter())
async def callback_special_use(call: CallbackQuery, callback_data: SpecialUseCallback):
    try:
        result = await use_special_and_announce(
            callback_data.game_id,
            call.from_user.id,
            target_user_id=callback_data.target_user_id,
        )
    except GameLogicError as exc:
        await call.answer(str(exc), show_alert=True)
        return

    player = await get_player(result.game.id, call.from_user.id)
    game = await get_game(result.game.id)
    if not player or not game:
        await call.answer("Не удалось обновить карточку.", show_alert=True)
        return

    players = await get_players(game.id)
    await bind_player_message(player, "special", call.message.message_id)
    await call.message.edit_text(
        f"{special_condition_text(player_condition(player), player_special_state(player))}\n\n<b>Результат:</b>\n{result.private_message}",
        reply_markup=get_special_kb(player, game, players),
    )
    await upsert_player_message(
        player,
        "hand",
        private_hand_text(
            game,
            player,
            player_cards(player),
            player_condition(player),
            revealed_keys(player),
            player_special_state(player),
        ),
        reply_markup=_reveal_markup(game, player),
    )
    await call.answer("Особое условие применено.")


@router.callback_query(RevealTraitCallback.filter())
async def callback_reveal(call: CallbackQuery, callback_data: RevealTraitCallback):
    try:
        result = await reveal_trait_and_announce(
            callback_data.game_id,
            call.from_user.id,
            callback_data.trait_key,
        )
    except GameLogicError as exc:
        await call.answer(str(exc), show_alert=True)
        return

    player = await get_player(result.game.id, call.from_user.id)
    game = await get_game(result.game.id)
    if not player or not game:
        await call.answer("Не удалось обновить карточку.", show_alert=True)
        return

    await _edit_card(call, game, player)
    await call.answer("Карта раскрыта.")


@router.callback_query(VoteCallback.filter())
async def callback_vote(call: CallbackQuery, callback_data: VoteCallback):
    try:
        progress = await submit_vote(callback_data.game_id, call.from_user.id, callback_data.target_user_id)
    except GameLogicError as exc:
        await call.answer(str(exc), show_alert=True)
        return

    player = await get_player(callback_data.game_id, call.from_user.id)
    if player:
        await bind_player_message(player, "vote", call.message.message_id)
    await call.answer(vote_saved_text(progress.total_votes, progress.total_expected))
    if progress.all_voted:
        await finish_voting_and_announce(callback_data.game_id)
