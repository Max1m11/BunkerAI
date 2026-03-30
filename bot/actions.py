from __future__ import annotations

from .ai_judge import generate_ai_verdict
from .config import settings
from .database import update_game
from .game_logic import (
    alive_players,
    analyze_survivors,
    close_discussion,
    current_vote_state,
    endgame_state,
    finish_game,
    finish_voting_round,
    opened_bunker_cards,
    opened_threat_cards,
    player_cards,
    player_condition,
    player_special_state,
    reveal_trait,
    revealed_keys,
    set_endgame_state,
    start_game,
    use_special_condition,
)
from .keyboards import get_group_panel_kb, get_reveal_kb, get_vote_kb
from .message_hub import clear_player_message, upsert_game_message, upsert_player_message
from .runtime import bot
from .strings import (
    bot_mention,
    discussion_started_text,
    exile_text,
    finished_text,
    no_exile_text,
    no_vote_round_text,
    private_hand_text,
    private_vote_prompt,
    reveal_announcement,
    revote_text,
    saved_text,
    voting_started_text,
)


def _strip_html(text: str) -> str:
    plain = (
        text.replace("<b>", "")
        .replace("</b>", "")
        .replace("<i>", "")
        .replace("</i>", "")
        .replace("•", "")
    )
    return " ".join(plain.split())


async def _update_group_panel(game, text: str, can_advance: bool = False) -> None:
    await upsert_game_message(
        game,
        "main",
        text,
        reply_markup=get_group_panel_kb(game.id, can_advance=can_advance),
    )


async def _append_game_note(game, note: str) -> None:
    state = endgame_state(game)
    notes = list(state.get("ui_notes") or [])
    notes.append(_strip_html(note))
    state["ui_notes"] = notes[-8:]
    set_endgame_state(game, state)
    await update_game(game)


def _phase_panel_text(game, players: list, bunker_card: dict | None = None, vote_state: dict | None = None) -> str:
    action_hint = ""
    if game.phase == "discussion" and bunker_card:
        text = discussion_started_text(game, bunker_card, len(alive_players(players)), settings.discussion_minutes)
        action_hint = f"Откройте {bot_mention()} и раскройте карту в личных сообщениях."
    elif game.phase == "voting" and vote_state:
        text = voting_started_text(
            game,
            vote_state["ballot_index"],
            vote_state["ballot_total"],
            settings.voting_minutes,
            revote=vote_state["revote"],
        )
        action_hint = f"Откройте {bot_mention()} и проголосуйте в личных сообщениях."
    else:
        text = finished_text(game, [], [], [], ai_verdict=None, forced=False)

    if action_hint:
        text += f"\n\n<b>Действие:</b>\n{action_hint}"

    notes = list((endgame_state(game).get("ui_notes") or []))
    if notes and game.phase != "finished":
        text += "\n\n<b>События:</b>\n" + "\n".join(f"• {item}" for item in notes[-3:])
    return text


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


async def _refresh_private_hand(player, game) -> None:
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
        reply_markup=get_reveal_kb(
            player,
            game.phase,
            game.round,
            condition=player_condition(player),
            game=game,
        ),
    )


async def _broadcast_reveal_prompts(game, players: list) -> None:
    for player in players:
        if player.faction_status != "alive":
            await clear_player_message(player, "hand")
            await clear_player_message(player, "vote")
            continue
        await _refresh_private_hand(player, game)
        await clear_player_message(player, "vote")


async def _broadcast_vote_prompts(game, players: list, candidate_ids: list[int], ballot_index: int, ballot_total: int, revote: bool) -> None:
    markup = get_vote_kb(players, game.id, candidate_ids=candidate_ids, game=game)
    text = private_vote_prompt(game, ballot_index, ballot_total, revote=revote)
    for player in players:
        if player.faction_status not in {"alive", "exiled"}:
            await clear_player_message(player, "vote")
            continue
        await upsert_player_message(player, "vote", text, reply_markup=markup)


async def _announce_finished(resolution) -> None:
    from .scheduler import sync_game_deadline

    await sync_game_deadline(resolution.game)

    for player in resolution.players:
        await clear_player_message(player, "vote")
        await _refresh_private_hand(player, resolution.game)

    checks = analyze_survivors(resolution.winners)
    ai_verdict = await generate_ai_verdict(
        resolution.game,
        resolution.winners,
        resolution.outside_winners,
        checks,
        resolution.notes,
    )
    await _update_group_panel(
        resolution.game,
        finished_text(
            resolution.game,
            resolution.winners,
            resolution.outside_winners,
            resolution.notes,
            ai_verdict=ai_verdict,
        ),
        can_advance=False,
    )


async def start_game_and_announce(game_id: str):
    from .scheduler import sync_game_deadline

    game, players, bunker_card = await start_game(game_id)
    await sync_game_deadline(game)
    await _update_group_panel(
        game,
        _phase_panel_text(game, players, bunker_card=bunker_card),
        can_advance=True,
    )
    await _broadcast_reveal_prompts(game, players)
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
        await _append_game_note(game, no_vote_round_text(result["skipped_round"]))
        await _update_group_panel(
            game,
            _phase_panel_text(game, players, bunker_card=result["bunker_card"]),
            can_advance=True,
        )
        await _broadcast_reveal_prompts(game, players)
        return result

    vote_state = {
        "ballot_index": result["ballot_index"],
        "ballot_total": result["ballot_total"],
        "revote": bool(result["revote"]),
    }
    await _update_group_panel(
        game,
        _phase_panel_text(game, players, vote_state=vote_state),
        can_advance=False,
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
    await _refresh_private_hand(result.player, result.game)
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
        await _append_game_note(resolution.game, revote_text(candidate_names))
        await _update_group_panel(
            resolution.game,
            _phase_panel_text(resolution.game, resolution.players, vote_state=vote_state),
            can_advance=False,
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
        await _update_group_panel(
            resolution.game,
            _phase_panel_text(resolution.game, resolution.players, vote_state=vote_state),
            can_advance=False,
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
    await _update_group_panel(
        resolution.game,
        _phase_panel_text(resolution.game, resolution.players, bunker_card=bunker_card),
        can_advance=True,
    )
    await _broadcast_reveal_prompts(resolution.game, resolution.players)
    return resolution


async def force_finish_and_announce(game_id: str):
    from .scheduler import sync_game_deadline

    game, players = await finish_game(game_id, forced=True)
    await sync_game_deadline(game)
    for player in players:
        await clear_player_message(player, "vote")
        await _refresh_private_hand(player, game)
    await _update_group_panel(
        game,
        finished_text(
            game,
            [],
            [],
            ["Игра остановлена до итогового подсчёта."],
            ai_verdict=None,
            forced=True,
        ),
        can_advance=False,
    )
    return game
