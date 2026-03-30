from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from .ai_judge import generate_ai_verdict
from .config import settings
from .game_logic import (
    GameLogicError,
    alive_players,
    analyze_survivors,
    close_discussion,
    current_vote_state,
    finish_game,
    finish_voting_round,
    opened_bunker_cards,
    opened_threat_cards,
    reveal_trait,
    start_game,
    use_special_condition,
)
from .keyboards import get_next_phase_kb, get_vote_kb, get_webapp_kb
from .runtime import bot
from .strings import (
    discussion_started_text,
    endgame_started_text,
    exile_text,
    finished_text,
    no_exile_text,
    no_vote_round_text,
    private_vote_prompt,
    reveal_announcement,
    revote_text,
    saved_text,
    voting_started_text,
)


async def _safe_private_message(user_id: int, text: str, reply_markup=None) -> None:
    try:
        await bot.send_message(user_id, text, reply_markup=reply_markup)
    except (TelegramForbiddenError, TelegramBadRequest):
        return


async def _send_auto_reveals(chat_id: int, auto_reveals: list) -> None:
    for item in auto_reveals:
        await bot.send_message(
            chat_id,
            reveal_announcement(
                item.player.full_name,
                item.trait_key,
                item.trait_value,
                auto_revealed=item.auto_revealed,
            ),
        )


async def _broadcast_vote_prompts(game, players: list, candidate_ids: list[int], ballot_index: int, ballot_total: int, revote: bool) -> None:
    markup = get_vote_kb(players, game.id, candidate_ids=candidate_ids)
    text = private_vote_prompt(game, ballot_index, ballot_total, revote=revote)
    for player in players:
        if player.faction_status not in {"alive", "exiled"}:
            continue
        await _safe_private_message(player.user_id, text, reply_markup=markup)


async def _announce_finished(resolution) -> None:
    from .scheduler import sync_game_deadline

    await sync_game_deadline(resolution.game)
    threats = opened_threat_cards(resolution.game)
    if threats:
        await bot.send_message(
            resolution.game.chat_id,
            endgame_started_text(resolution.game.mode, threats),
        )

    checks = analyze_survivors(resolution.winners)
    ai_verdict = await generate_ai_verdict(
        resolution.game,
        resolution.winners,
        resolution.outside_winners,
        checks,
        resolution.notes,
    )
    await bot.send_message(
        resolution.game.chat_id,
        finished_text(
            resolution.game,
            resolution.winners,
            resolution.outside_winners,
            resolution.notes,
            ai_verdict=ai_verdict,
        ),
    )


async def start_game_and_announce(game_id: str):
    from .scheduler import sync_game_deadline

    game, players, bunker_card = await start_game(game_id)
    await sync_game_deadline(game)
    await bot.send_message(
        game.chat_id,
        discussion_started_text(game, bunker_card, len(alive_players(players)), settings.discussion_minutes),
        reply_markup=get_next_phase_kb(game.id),
    )
    await bot.send_message(game.chat_id, "Мини-приложение партии:", reply_markup=get_webapp_kb(game.id))
    return game, players


async def close_discussion_and_announce(game_id: str, by_timer: bool = False):
    from .scheduler import sync_game_deadline

    result = await close_discussion(game_id)

    if result["kind"] == "finished":
        resolution = result["resolution"]
        await _send_auto_reveals(resolution.game.chat_id, result["auto_reveals"])
        await _announce_finished(resolution)
        return resolution

    game = result["game"]
    players = result["players"]
    await _send_auto_reveals(game.chat_id, result["auto_reveals"])
    await sync_game_deadline(game)

    if result["kind"] == "no_vote_round":
        await bot.send_message(game.chat_id, no_vote_round_text(result["skipped_round"]))
        await bot.send_message(
            game.chat_id,
            discussion_started_text(game, result["bunker_card"], len(alive_players(players)), settings.discussion_minutes),
            reply_markup=get_next_phase_kb(game.id),
        )
        return result

    await bot.send_message(
        game.chat_id,
        voting_started_text(
            game,
            result["ballot_index"],
            result["ballot_total"],
            settings.voting_minutes,
            revote=bool(result["revote"]),
        ),
    )
    await _broadcast_vote_prompts(
        game,
        players,
        result["candidate_ids"],
        result["ballot_index"],
        result["ballot_total"],
        revote=bool(result["revote"]),
    )
    return result


async def reveal_trait_and_announce(game_id: str, user_id: int, trait_key: str):
    result = await reveal_trait(game_id, user_id, trait_key)
    await bot.send_message(
        result.game.chat_id,
        reveal_announcement(result.player.full_name, result.trait_key, result.trait_value),
    )
    return result


async def use_special_and_announce(game_id: str, user_id: int, target_user_id: int | None = None):
    result = await use_special_condition(game_id, user_id, target_user_id=target_user_id)
    if result.public_message:
        await bot.send_message(result.game.chat_id, result.public_message)
    return result


async def finish_voting_and_announce(game_id: str):
    from .scheduler import sync_game_deadline

    resolution = await finish_voting_round(game_id)

    if resolution.outcome == "revote_started":
        vote_state = current_vote_state(resolution.game, resolution.players)
        candidate_names = [
            player.full_name for player in resolution.players if player.user_id in vote_state["candidate_ids"]
        ]
        await sync_game_deadline(resolution.game)
        await bot.send_message(resolution.game.chat_id, revote_text(candidate_names))
        await bot.send_message(
            resolution.game.chat_id,
            voting_started_text(
                resolution.game,
                vote_state["ballot_index"],
                vote_state["ballot_total"],
                settings.voting_minutes,
                revote=True,
            ),
        )
        await _broadcast_vote_prompts(
            resolution.game,
            resolution.players,
            vote_state["candidate_ids"],
            vote_state["ballot_index"],
            vote_state["ballot_total"],
            revote=True,
        )
        return resolution

    if resolution.outcome == "exiled":
        for player in resolution.exiled:
            await bot.send_message(resolution.game.chat_id, exile_text(player.full_name))
    elif resolution.outcome == "saved":
        await bot.send_message(resolution.game.chat_id, saved_text())
    elif resolution.outcome == "no_exile":
        await bot.send_message(resolution.game.chat_id, no_exile_text())

    if resolution.finished:
        await _announce_finished(resolution)
        return resolution

    await sync_game_deadline(resolution.game)
    if resolution.game.phase == "voting":
        vote_state = current_vote_state(resolution.game, resolution.players)
        await bot.send_message(
            resolution.game.chat_id,
            voting_started_text(
                resolution.game,
                vote_state["ballot_index"],
                vote_state["ballot_total"],
                settings.voting_minutes,
                revote=vote_state["revote"],
            ),
        )
        await _broadcast_vote_prompts(
            resolution.game,
            resolution.players,
            vote_state["candidate_ids"],
            vote_state["ballot_index"],
            vote_state["ballot_total"],
            revote=vote_state["revote"],
        )
        return resolution

    bunker_card = opened_bunker_cards(resolution.game)[-1]
    await bot.send_message(
        resolution.game.chat_id,
        discussion_started_text(
            resolution.game,
            bunker_card,
            len(alive_players(resolution.players)),
            settings.discussion_minutes,
        ),
        reply_markup=get_next_phase_kb(resolution.game.id),
    )
    return resolution


async def force_finish_and_announce(game_id: str):
    from .scheduler import sync_game_deadline

    game, _players = await finish_game(game_id, forced=True)
    await sync_game_deadline(game)
    await bot.send_message(
        game.chat_id,
        finished_text(
            game,
            [],
            [],
            ["Игра остановлена ведущим до итогового подсчёта."],
            ai_verdict=None,
            forced=True,
        ),
    )
    return game
