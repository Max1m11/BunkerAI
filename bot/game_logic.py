from __future__ import annotations

import json
import math
import random
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from .cards import (
    BUNKER_CARDS,
    CARD_KEYS,
    CHARACTER_KEYS,
    THREAT_CARDS,
    draw_character_cards,
    draw_special_condition,
    get_bunker_card,
    get_scenario_by_id,
    get_threat_card,
    round_exiles_for,
)
from .config import settings
from .database import (
    cast_vote,
    create_player,
    get_active_game_by_chat,
    get_game,
    get_player,
    get_player_by_id,
    get_players,
    get_votes,
    save_player,
    update_game,
)
from .models import Game, Player, RevealResult, RoundResolution, SpecialResult, Vote, VoteProgress
from .specials import (
    condition_available,
    condition_effect,
    condition_text,
    condition_title,
    has_fertile_pair,
    initial_condition_state,
    normalize_condition,
    player_tag_set,
)
from .strings import card_label, mode_label, phase_label, player_status


INFECTIOUS_TAG = "infection"


class GameLogicError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def deadline_after(minutes: int) -> str:
    return (utc_now() + timedelta(minutes=minutes)).isoformat()


def calculate_slots(total_players: int) -> int:
    if total_players in {4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}:
        schedule_total = sum(round_exiles_for(total_players, round_number) for round_number in range(1, 6))
        return max(1, total_players - schedule_total)
    return max(1, math.ceil(total_players / 2))


def _loads(raw: str | None, default):
    if not raw:
        return default
    return json.loads(raw)


def opened_bunker_cards(game: Game) -> list[dict]:
    return _loads(game.opened_bunker_cards, [])


def set_opened_bunker_cards(game: Game, cards: list[dict]) -> None:
    game.opened_bunker_cards = json.dumps(cards, ensure_ascii=False)


def opened_threat_cards(game: Game) -> list[dict]:
    return _loads(game.opened_threat_cards, [])


def set_opened_threat_cards(game: Game, cards: list[dict]) -> None:
    game.opened_threat_cards = json.dumps(cards, ensure_ascii=False)


def revote_state(game: Game) -> dict:
    return _loads(game.revote_state, {})


def set_revote_state(game: Game, state: dict) -> None:
    game.revote_state = json.dumps(state, ensure_ascii=False)


def endgame_state(game: Game) -> dict:
    return _loads(game.endgame_state, {})


def set_endgame_state(game: Game, state: dict) -> None:
    game.endgame_state = json.dumps(state, ensure_ascii=False)


def player_cards(player: Player) -> dict[str, dict]:
    return _loads(player.character_cards, {})


def set_player_cards(player: Player, cards: dict) -> None:
    player.character_cards = json.dumps(cards, ensure_ascii=False)


def player_condition(player: Player) -> dict:
    return normalize_condition(_loads(player.special_condition, {}))


def set_player_condition(player: Player, condition: dict) -> None:
    player.special_condition = json.dumps(normalize_condition(condition), ensure_ascii=False)


def player_special_state(player: Player) -> dict:
    return _loads(player.special_state, {})


def set_player_special_state(player: Player, state: dict) -> None:
    player.special_state = json.dumps(state, ensure_ascii=False)


def revealed_keys(player: Player) -> list[str]:
    return _loads(player.revealed_character_keys, [])


def set_revealed(player: Player, keys: list[str]) -> None:
    player.revealed_character_keys = json.dumps(keys, ensure_ascii=False)


def alive_players(players: list[Player]) -> list[Player]:
    return [player for player in players if player.faction_status == "alive"]


def exiled_players(players: list[Player]) -> list[Player]:
    return [player for player in players if player.faction_status == "exiled"]


def unique_vote_count(votes: list[Vote]) -> int:
    return len({vote.voter_id for vote in votes})


def build_revealed_cards(player: Player) -> dict[str, str]:
    cards = player_cards(player)
    return {key: cards[key]["text"] for key in revealed_keys(player) if key in cards}


AVATAR_VARIANTS = ("navy", "pink", "brown", "teal")


def _player_initials(full_name: str) -> str:
    parts = [part for part in full_name.replace("-", " ").split() if part]
    if not parts:
        return "??"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return f"{parts[0][0]}{parts[1][0]}".upper()


def _avatar_variant(user_id: int) -> str:
    return AVATAR_VARIANTS[abs(user_id) % len(AVATAR_VARIANTS)]


def _player_subtitle(player: Player, revealed: dict[str, str], cards: dict[str, dict], is_viewer: bool) -> str:
    if is_viewer and cards.get("profession"):
        return cards["profession"]["text"]
    if "profession" in revealed:
        return revealed["profession"]
    if player.faction_status in {"exiled", "winner", "lost"}:
        return player_status(player)
    return "Профессия скрыта"


def _hidden_labels(player: Player) -> list[str]:
    revealed = set(revealed_keys(player))
    return [card_label(key) for key in CHARACTER_KEYS if key not in revealed]


def _layout_trait_rows(rows: list[dict[str, str | bool]]) -> list[dict[str, str | bool]]:
    open_half_index: int | None = None
    for index, row in enumerate(rows):
        if row["full_width"]:
            if open_half_index is not None:
                rows[open_half_index]["full_width"] = True
            open_half_index = None
            continue
        if open_half_index is None:
            open_half_index = index
        else:
            open_half_index = None
    if open_half_index is not None:
        rows[open_half_index]["full_width"] = True
    return rows


def _trait_rows(player: Player, cards: dict[str, dict], revealed: dict[str, str], is_viewer: bool) -> list[dict[str, str | bool]]:
    rows: list[dict[str, str | bool]] = []
    for key in CHARACTER_KEYS:
        if is_viewer:
            card = cards.get(key)
            value = card["text"] if card else None
            masked = key not in revealed
        else:
            value = revealed.get(key)
            masked = False
        if not value:
            continue
        rows.append(
            {
                "key": key,
                "label": card_label(key),
                "value": value,
                "full_width": key == "fact",
                "masked": masked,
            }
        )
    return _layout_trait_rows(rows)


def _sort_players_for_viewer(players: list[Player], viewer_user_id: int | None) -> list[Player]:
    if viewer_user_id is None:
        return list(players)
    return sorted(
        players,
        key=lambda player: (
            0 if player.user_id == viewer_user_id else 1,
            player.full_name.lower(),
        ),
    )


def build_public_player(player: Player, candidate_ids: set[int] | None = None, viewer_user_id: int | None = None) -> dict:
    cards = player_cards(player)
    revealed = build_revealed_cards(player)
    candidate_ids = candidate_ids or set()
    is_viewer = viewer_user_id == player.user_id
    return {
        "id": player.id,
        "user_id": player.user_id,
        "name": player.full_name,
        "username": player.username,
        "initials": _player_initials(player.full_name),
        "avatar_variant": _avatar_variant(player.user_id),
        "subtitle": _player_subtitle(player, revealed, cards, is_viewer),
        "faction_status": player.faction_status,
        "status": player_status(player),
        "is_alive": player.faction_status == "alive",
        "is_exiled": player.faction_status == "exiled",
        "is_candidate": player.user_id in candidate_ids,
        "is_viewer": is_viewer,
        "revealed_cards": revealed,
        "revealed_traits": _trait_rows(player, cards, revealed, is_viewer),
        "hidden_count": max(0, len(CARD_KEYS) - len(revealed)),
        "hidden_labels": [] if is_viewer else _hidden_labels(player),
    }


def build_public_game_payload(game: Game, players: list[Player], viewer_user_id: int | None = None) -> dict:
    sorted_players = _sort_players_for_viewer(players, viewer_user_id)
    alive = _sort_players_for_viewer(alive_players(players), viewer_user_id)
    exiled = _sort_players_for_viewer(exiled_players(players), viewer_user_id)
    vote_state = current_vote_state(game, players) if players else {
        "ballot_index": 1,
        "ballot_total": 0,
        "revote": False,
        "candidate_ids": [],
    }
    vote_state = {
        **vote_state,
        "active": game.phase == "voting",
        "candidate_count": len(vote_state["candidate_ids"]),
    }
    candidate_ids = set(vote_state["candidate_ids"]) if vote_state["active"] else set()
    return {
        "id": game.id,
        "mode": game.mode,
        "mode_label": mode_label(game.mode),
        "phase": game.phase,
        "phase_label": phase_label(game.phase),
        "phase_step": game.phase_step,
        "phase_deadline_at": game.phase_deadline_at,
        "server_time": iso_now(),
        "round": game.round,
        "round_limit": game.round_limit,
        "slots": game.slots,
        "scenario_title": game.scenario_title,
        "scenario_hint": game.scenario_hint,
        "catastrophe": {
            "id": game.catastrophe_id,
            "title": game.catastrophe_title,
            "text": game.catastrophe_text,
        },
        "opened_bunker_cards": opened_bunker_cards(game),
        "opened_threat_cards": opened_threat_cards(game),
        "vote_state": vote_state,
        "alive_count": len(alive),
        "exiled_count": len(exiled),
        "viewer_user_id": viewer_user_id,
        "alive_players": [build_public_player(player, candidate_ids=candidate_ids, viewer_user_id=viewer_user_id) for player in alive],
        "exiled_players": [build_public_player(player, candidate_ids=candidate_ids, viewer_user_id=viewer_user_id) for player in exiled],
        "players": [build_public_player(player, candidate_ids=candidate_ids, viewer_user_id=viewer_user_id) for player in sorted_players],
    }


def build_public_player_payload(game: Game, player: Player, viewer_user_id: int | None = None) -> dict:
    payload = build_public_player(player, viewer_user_id=viewer_user_id)
    payload["game_id"] = game.id
    payload["mode"] = game.mode
    payload["mode_label"] = mode_label(game.mode)
    payload["phase"] = game.phase
    payload["phase_label"] = phase_label(game.phase)
    payload["phase_deadline_at"] = game.phase_deadline_at
    payload["server_time"] = iso_now()
    payload["viewer_user_id"] = viewer_user_id
    return payload


def format_revealed_lines(player: Player) -> list[tuple[str, str]]:
    revealed = build_revealed_cards(player)
    return [(card_label(key), value) for key, value in revealed.items()]


def current_vote_state(game: Game, players: list[Player]) -> dict:
    meta = _current_vote_meta(game, len(players))
    candidate_ids = meta.get("candidate_ids") or [player.user_id for player in players if player.faction_status == "alive"]
    return {
        "ballot_index": int(meta.get("ballot_index", 1)),
        "ballot_total": int(meta.get("ballot_total", 0)),
        "revote": bool(meta.get("revote")),
        "candidate_ids": candidate_ids,
    }


def _phase_step(ballot_index: int, revote: bool = False) -> str:
    return f"ballot-{ballot_index}{'-revote' if revote else ''}"


def _current_vote_meta(game: Game, total_players: int) -> dict:
    state = revote_state(game)
    if not state:
        return {
            "ballot_index": 1,
            "ballot_total": round_exiles_for(total_players, game.round),
            "revote": False,
            "candidate_ids": [],
        }
    return state


def _set_reveal_count(player: Player, round_number: int, value: int) -> None:
    state = player_special_state(player)
    counts = dict(state.get("round_reveal_counts") or {})
    counts[str(round_number)] = value
    state["round_reveal_counts"] = counts
    set_player_special_state(player, state)


def _get_reveal_count(player: Player, round_number: int) -> int:
    state = player_special_state(player)
    return int((state.get("round_reveal_counts") or {}).get(str(round_number), 0))


def _allowed_reveals(player: Player, round_number: int) -> int:
    state = player_special_state(player)
    bonus_rounds = set(state.get("extra_reveal_rounds") or [])
    return 2 if round_number in bonus_rounds else 1


def _open_next_bunker_card(game: Game) -> dict:
    state = endgame_state(game)
    deck_ids = state.get("bunker_deck_ids") or []
    next_index = int(state.get("next_bunker_index", 0))
    if next_index >= len(deck_ids):
        existing = opened_bunker_cards(game)
        return existing[-1] if existing else {"title": "Без карты", "text": ""}

    card = get_bunker_card(deck_ids[next_index])
    cards = opened_bunker_cards(game)
    cards.append(card)
    set_opened_bunker_cards(game, cards)
    state["next_bunker_index"] = next_index + 1
    set_endgame_state(game, state)
    return card


def _open_story_threats(game: Game, count: int = 2) -> list[dict]:
    state = endgame_state(game)
    deck_ids = state.get("threat_deck_ids") or []
    next_index = int(state.get("next_threat_index", 0))
    threats = opened_threat_cards(game)
    added: list[dict] = []
    while next_index < len(deck_ids) and len(added) < count:
        card = get_threat_card(deck_ids[next_index])
        threats.append(card)
        added.append(card)
        next_index += 1
    state["next_threat_index"] = next_index
    set_opened_threat_cards(game, threats)
    set_endgame_state(game, state)
    return added


def _target_name_map(players: list[Player]) -> dict[int, str]:
    return {player.user_id: player.full_name for player in players}


def _team_tag_pool(players: list[Player]) -> set[str]:
    pool: set[str] = set()
    for player in players:
        pool.update(player_tag_set(player_cards(player)))
    return pool


def _evaluate_condition_bonus(owner: Player, side_players: list[Player], all_players: list[Player], side_name: str) -> tuple[int, list[str]]:
    condition = player_condition(owner)
    state = player_special_state(owner)
    effect = condition_effect(condition)
    params = dict(condition.get("params") or {})
    notes: list[str] = []
    bonus = 0
    team_tags = _team_tag_pool(side_players)
    side_cards = [player_cards(player) for player in side_players]
    all_by_user_id = {player.user_id: player for player in all_players}

    if effect == "goal_keep_tag_alive":
        goal_tag = params.get("goal_tag")
        if goal_tag in team_tags:
            bonus += int(params.get("success_bonus", 2))
            notes.append(f"{owner.full_name}: условие «{condition_title(condition)}» сработало.")
        else:
            bonus -= int(params.get("fail_penalty", 2))
            notes.append(f"{owner.full_name}: условие «{condition_title(condition)}» не выполнено.")
    elif effect == "endgame_bonus_tag":
        goal_tag = params.get("goal_tag")
        if goal_tag in team_tags:
            bonus += int(params.get("success_bonus", 1))
            notes.append(f"{owner.full_name}: команда получила бонус за «{condition_title(condition)}».")
    elif effect == "goal_need_pair":
        if has_fertile_pair(side_cards):
            bonus += int(params.get("success_bonus", 2))
            notes.append(f"{owner.full_name}: найден шанс на продолжение рода.")
        else:
            bonus -= int(params.get("fail_penalty", 2))
            notes.append(f"{owner.full_name}: условие о репродуктивной паре не выполнено.")
    elif effect == "goal_no_tag":
        forbidden = params.get("forbidden_tag")
        if forbidden not in team_tags:
            bonus += int(params.get("success_bonus", 2))
            notes.append(f"{owner.full_name}: команда прошла проверку «{condition_title(condition)}».")
        else:
            bonus -= int(params.get("fail_penalty", 1))
            notes.append(f"{owner.full_name}: команде помешало условие «{condition_title(condition)}».")
    elif effect == "goal_target_alive":
        target_id = state.get("goal_target_user_id")
        if any(player.user_id == target_id for player in side_players):
            bonus += int(params.get("success_bonus", 2))
            notes.append(f"{owner.full_name}: его тайная цель осталась в стороне {side_name}.")
        else:
            bonus -= int(params.get("fail_penalty", 2))
            notes.append(f"{owner.full_name}: тайная цель не дошла до стороны {side_name}.")
    elif effect == "goal_target_exiled":
        target_id = state.get("goal_target_user_id")
        target_player = all_by_user_id.get(target_id)
        if target_player and target_player.faction_status == "exiled":
            bonus += int(params.get("success_bonus", 2))
            notes.append(f"{owner.full_name}: его тайная цель оказалась среди изгнанных.")
        else:
            bonus -= int(params.get("fail_penalty", 2))
            notes.append(f"{owner.full_name}: тайная цель не попала в изгнанные.")
    elif effect == "outside_bonus" and side_name == "outside":
        bonus += int(params.get("outside_bonus", 2))
        notes.append(f"{owner.full_name}: сторона изгнанных получила бонус по его условию.")
    elif effect == "bunker_bonus" and side_name == "bunker":
        bonus += int(params.get("bunker_bonus", 2))
        notes.append(f"{owner.full_name}: бункер получил бонус по его условию.")

    return bonus, notes


def _catastrophe_rules(game: Game) -> tuple[list[str], list[str], list[str], int, bool]:
    try:
        scenario = get_scenario_by_id(game.catastrophe_id)
    except KeyError as exc:
        raise GameLogicError(f"Неизвестная катастрофа для финального расчёта: {game.catastrophe_id}.") from exc

    return (
        list(scenario.get("required_tags", [])),
        list(scenario.get("helpful_tags", [])),
        list(scenario.get("harmful_tags", [])),
        int(scenario.get("threshold", 0)),
        bool(scenario.get("requires_pair", False)),
    )


def _evaluate_side(game: Game, players: list[Player], side_name: str, use_bunker_cards: bool, all_players: list[Player]) -> tuple[int, bool, list[str]]:
    if not players:
        return 0, False, [f"Сторона {side_name} отсутствует."]

    required, helpful, harmful, threshold, requires_pair = _catastrophe_rules(game)

    team_tags = _team_tag_pool(players)
    notes: list[str] = []
    score = 0

    for tag in required:
        if tag in team_tags:
            score += 2
            notes.append(f"Команда {side_name}: закрыт критичный тег {tag}.")
        else:
            score -= 2
            notes.append(f"Команда {side_name}: не хватает критичного тега {tag}.")
    for tag in helpful:
        if tag in team_tags:
            score += 1
    for tag in harmful:
        if tag in team_tags:
            score -= 2
            notes.append(f"Команда {side_name}: проблемный тег {tag} снижает шансы.")

    if requires_pair:
        if has_fertile_pair([player_cards(player) for player in players]):
            score += 2
            notes.append(f"Команда {side_name}: есть шанс на продолжение рода.")
        else:
            score -= 3
            notes.append(f"Команда {side_name}: нет репродуктивно совместимой пары.")

    if use_bunker_cards:
        for card in opened_bunker_cards(game):
            score += int(card.get("score", 0))
            notes.append(f"Бункер даёт бонус: {card['title']}.")

    for threat in opened_threat_cards(game):
        threat_tags = set(threat.get("required_tags", []))
        if threat_tags and threat_tags.issubset(team_tags):
            score += 1
        else:
            score -= int(threat.get("threshold", 1))
            notes.append(f"Угроза «{threat['title']}» ударила по стороне {side_name}.")
        for harmful_tag in threat.get("harmful_tags", []):
            if harmful_tag in team_tags:
                score -= 1

    for owner in players:
        bonus, condition_notes = _evaluate_condition_bonus(owner, players, all_players, side_name)
        score += bonus
        notes.extend(condition_notes)

    threshold_value = threshold + (2 if side_name == "outside" else 0) + len(opened_threat_cards(game))
    success = score >= threshold_value
    notes.append(f"Итоговый счёт стороны {side_name}: {score} при пороге {threshold_value}.")
    return score, success, notes


async def add_player_to_lobby(game: Game, user_id: int, username: str | None, full_name: str) -> Player:
    if game.phase != "lobby":
        raise GameLogicError("Лобби уже закрыто.")

    current_players = await get_players(game.id)
    if any(player.user_id == user_id for player in current_players):
        raise GameLogicError("Вы уже участвуете в этой партии.")

    if len(current_players) >= settings.max_players:
        raise GameLogicError("Достигнут лимит игроков.")

    player = Player(
        id=str(uuid.uuid4()),
        game_id=game.id,
        user_id=user_id,
        username=username,
        full_name=full_name,
    )
    await create_player(player)
    return player


async def ensure_active_chat_game(chat_id: int) -> Game:
    game = await get_active_game_by_chat(chat_id)
    if not game:
        raise GameLogicError("В этом чате нет активной партии.")
    return game


async def choose_game_mode(game_id: str, host_id: int, mode: str) -> Game:
    game = await get_game(game_id)
    if not game:
        raise GameLogicError("Партия не найдена.")
    if game.phase != "lobby":
        raise GameLogicError("Менять режим можно только в лобби.")
    if game.host_id != host_id:
        raise GameLogicError("Менять режим может только инициатор лобби.")
    if mode not in {"basic_final", "survival_story"}:
        raise GameLogicError("Неизвестный режим.")
    game.mode = mode
    game.updated_at = iso_now()
    await update_game(game)
    return game


async def start_game(game_id: str) -> tuple[Game, list[Player], dict]:
    game = await get_game(game_id)
    if not game:
        raise GameLogicError("Партия не найдена.")
    if game.phase != "lobby":
        raise GameLogicError("Партия уже запущена.")

    players = await get_players(game.id)
    if len(players) < settings.min_players:
        raise GameLogicError(f"Нужно минимум {settings.min_players} игрока(ов).")

    player_ids = [player.user_id for player in players]
    name_map = _target_name_map(players)
    existing_game_ui = dict((endgame_state(game).get("_ui") or {}))
    bunker_deck_ids = [card["id"] for card in BUNKER_CARDS]
    random.shuffle(bunker_deck_ids)
    threat_deck_ids = [card["id"] for card in THREAT_CARDS]
    random.shuffle(threat_deck_ids)

    for player in players:
        cards = draw_character_cards()
        condition = draw_special_condition()
        state = initial_condition_state(condition, player.user_id, player_ids)
        existing_player_ui = dict((player_special_state(player).get("_ui") or {}))
        target_id = state.get("goal_target_user_id")
        if target_id:
            state["goal_target_user_name"] = name_map.get(target_id)
        if existing_player_ui:
            state["_ui"] = existing_player_ui
        player.faction_status = "alive"
        player.is_exiled = 0
        set_player_cards(player, cards)
        set_player_condition(player, condition)
        set_player_special_state(player, state)
        set_revealed(player, [])
        await save_player(player)

    game.phase = "discussion"
    game.phase_step = "discussion"
    game.round = 1
    game.round_limit = 5
    game.slots = calculate_slots(len(players))
    set_revote_state(game, {})
    set_opened_bunker_cards(game, [])
    set_opened_threat_cards(game, [])
    new_endgame_state = {
        "bunker_deck_ids": bunker_deck_ids,
        "threat_deck_ids": threat_deck_ids,
        "next_bunker_index": 0,
        "next_threat_index": 0,
    }
    if existing_game_ui:
        new_endgame_state["_ui"] = existing_game_ui
    set_endgame_state(game, new_endgame_state)
    opened_card = _open_next_bunker_card(game)
    game.phase_deadline_at = deadline_after(settings.discussion_minutes)
    game.updated_at = iso_now()
    await update_game(game)
    return game, await get_players(game.id), opened_card


async def _reveal_for_player(player: Player, game: Game, trait_key: str, auto_revealed: bool) -> RevealResult:
    cards = player_cards(player)
    if trait_key not in cards:
        raise GameLogicError("Неизвестная карта персонажа.")

    revealed = revealed_keys(player)
    if trait_key in revealed:
        raise GameLogicError("Эта карта уже раскрыта.")

    if not auto_revealed:
        if game.round == 1 and trait_key != "profession":
            raise GameLogicError("В первом раунде по официальным правилам раскрывается профессия.")
        if _get_reveal_count(player, game.round) >= _allowed_reveals(player, game.round):
            raise GameLogicError("В этом раунде лимит раскрытий уже исчерпан.")

    revealed.append(trait_key)
    set_revealed(player, revealed)
    _set_reveal_count(player, game.round, _get_reveal_count(player, game.round) + 1)
    await save_player(player)
    return RevealResult(
        game=game,
        player=player,
        trait_key=trait_key,
        trait_value=cards[trait_key]["text"],
        auto_revealed=auto_revealed,
    )


async def reveal_trait(game_id: str, user_id: int, trait_key: str) -> RevealResult:
    if trait_key not in CHARACTER_KEYS:
        raise GameLogicError("Можно раскрывать только карты персонажа.")

    game = await get_game(game_id)
    if not game:
        raise GameLogicError("Партия не найдена.")
    if game.phase != "discussion":
        raise GameLogicError("Раскрытие карт доступно только во время обсуждения.")

    player = await get_player(game_id, user_id)
    if not player:
        raise GameLogicError("Вы не участвуете в этой партии.")
    if player.faction_status != "alive":
        raise GameLogicError("Изгнанные не раскрывают карты персонажа в обсуждении.")

    return await _reveal_for_player(player, game, trait_key, auto_revealed=False)


async def _auto_reveal_missing(game: Game, players: list[Player]) -> list[RevealResult]:
    results: list[RevealResult] = []
    for player in alive_players(players):
        while _get_reveal_count(player, game.round) < _allowed_reveals(player, game.round):
            cards = player_cards(player)
            hidden = [key for key in CHARACTER_KEYS if key not in revealed_keys(player)]
            if not hidden:
                break
            if game.round == 1 and "profession" in hidden:
                key = "profession"
            else:
                key = random.choice(hidden)
            results.append(await _reveal_for_player(player, game, key, auto_revealed=True))
    return results


async def close_discussion(game_id: str) -> dict:
    game = await get_game(game_id)
    if not game:
        raise GameLogicError("Партия не найдена.")
    if game.phase != "discussion":
        raise GameLogicError("Сейчас обсуждение не активно.")

    players = await get_players(game.id)
    auto_reveals = await _auto_reveal_missing(game, players)
    total_players = len(players)
    ballot_total = round_exiles_for(total_players, game.round)

    if ballot_total <= 0:
        if game.round >= game.round_limit:
            resolution = await _finalize_game(game)
            return {"kind": "finished", "resolution": resolution, "auto_reveals": auto_reveals}

        skipped_round = game.round
        game.round += 1
        game.phase = "discussion"
        game.phase_step = "discussion"
        game.phase_deadline_at = deadline_after(settings.discussion_minutes)
        game.updated_at = iso_now()
        opened_card = _open_next_bunker_card(game)
        await update_game(game)
        return {
            "kind": "no_vote_round",
            "game": game,
            "players": await get_players(game.id),
            "auto_reveals": auto_reveals,
            "bunker_card": opened_card,
            "skipped_round": skipped_round,
        }

    game.phase = "voting"
    game.phase_step = _phase_step(1, False)
    set_revote_state(game, {"ballot_index": 1, "ballot_total": ballot_total, "revote": False, "candidate_ids": []})
    game.phase_deadline_at = deadline_after(settings.voting_minutes)
    game.updated_at = iso_now()
    await update_game(game)
    return {
        "kind": "voting_started",
        "game": game,
        "players": await get_players(game.id),
        "auto_reveals": auto_reveals,
        "ballot_index": 1,
        "ballot_total": ballot_total,
        "candidate_ids": [],
        "revote": False,
    }


def _eligible_voters(players: list[Player]) -> list[Player]:
    return [player for player in players if player.faction_status in {"alive", "exiled"}]


async def submit_vote(game_id: str, voter_id: int, target_user_id: int) -> VoteProgress:
    game = await get_game(game_id)
    if not game:
        raise GameLogicError("Партия не найдена.")
    if game.phase != "voting":
        raise GameLogicError("Сейчас тайное голосование закрыто.")

    players = await get_players(game.id)
    voter = next((player for player in players if player.user_id == voter_id), None)
    target = next((player for player in players if player.user_id == target_user_id), None)
    if not voter or voter.faction_status not in {"alive", "exiled"}:
        raise GameLogicError("Сейчас вы не можете голосовать.")
    if not target or target.faction_status != "alive":
        raise GameLogicError("Голосовать можно только против живого игрока.")

    meta = _current_vote_meta(game, len(players))
    if meta.get("revote") and target_user_id not in meta.get("candidate_ids", []):
        raise GameLogicError("В перевыборе можно голосовать только за игроков-лидеров.")

    vote = Vote(
        id=str(uuid.uuid4()),
        game_id=game.id,
        round=game.round,
        phase_step=game.phase_step,
        faction=voter.faction_status,
        voter_id=voter_id,
        target_id=str(target_user_id),
        created_at=iso_now(),
    )
    await cast_vote(vote)
    votes = await get_votes(game.id, game.round, game.phase_step)
    expected = len(_eligible_voters(players))
    return VoteProgress(
        game=game,
        voter=voter,
        total_votes=unique_vote_count(votes),
        total_expected=expected,
        all_voted=unique_vote_count(votes) >= expected,
    )


def _aggregate_exiled_vote(votes: list[Vote], exiled_players_list: list[Player]) -> str | None:
    if not votes:
        return None
    tally = Counter(vote.target_id for vote in votes)
    max_votes = max(tally.values())
    leaders = [target_id for target_id, count in tally.items() if count == max_votes]
    if len(leaders) == 1:
        return leaders[0]

    decider = next(
        (
            player
            for player in exiled_players_list
            if condition_effect(player_condition(player)) == "exiled_tiebreak"
        ),
        None,
    )
    if decider:
        decider_vote = next((vote for vote in votes if vote.voter_id == decider.user_id), None)
        if decider_vote and decider_vote.target_id in leaders:
            return decider_vote.target_id
    return None


def _vote_weight_for_player(player: Player, game: Game) -> int:
    condition = player_condition(player)
    state = player_special_state(player)
    if condition_effect(condition) == "double_vote_once":
        if state.get("double_vote_round") == game.round and state.get("double_vote_step") == game.phase_step:
            return 2
    return 1


async def use_special_condition(game_id: str, user_id: int, target_user_id: int | None = None) -> SpecialResult:
    game = await get_game(game_id)
    if not game:
        raise GameLogicError("Партия не найдена.")

    player = await get_player(game_id, user_id)
    if not player:
        raise GameLogicError("Вы не участвуете в этой партии.")
    if player.faction_status not in {"alive", "exiled"}:
        raise GameLogicError("Сейчас вы не можете использовать особое условие.")

    condition = player_condition(player)
    state = player_special_state(player)
    if not condition_available(condition, state, game.phase):
        raise GameLogicError("Это особое условие сейчас недоступно.")

    players = await get_players(game.id)
    effect = condition_effect(condition)
    target = next((item for item in players if item.user_id == target_user_id), None) if target_user_id else None

    if effect == "peek_hidden_once":
        if not target:
            raise GameLogicError("Нужно выбрать цель.")
        hidden = [key for key in CHARACTER_KEYS if key not in revealed_keys(target)]
        if not hidden:
            raise GameLogicError("У цели нет скрытых карт.")
        key = random.choice(hidden)
        card = player_cards(target)[key]
        state["used"] = True
        set_player_special_state(player, state)
        await save_player(player)
        return SpecialResult(game=game, player=player, action=effect, target=target, private_message=f"Подсмотрено: {card_label(key)} — {card['text']}")

    if effect == "peek_condition_once":
        if not target:
            raise GameLogicError("Нужно выбрать цель.")
        target_condition = player_condition(target)
        state["used"] = True
        set_player_special_state(player, state)
        await save_player(player)
        return SpecialResult(game=game, player=player, action=effect, target=target, private_message=f"Особое условие игрока {target.full_name}: {condition_title(target_condition)} — {condition_text(target_condition)}")

    if effect == "force_reveal_once":
        if not target or target.faction_status != "alive":
            raise GameLogicError("Нужно выбрать живого игрока.")
        hidden = [key for key in CHARACTER_KEYS if key not in revealed_keys(target)]
        if not hidden:
            raise GameLogicError("У цели нет скрытых карт.")
        key = "profession" if game.round == 1 and "profession" in hidden else random.choice(hidden)
        result = await _reveal_for_player(target, game, key, auto_revealed=True)
        state["used"] = True
        set_player_special_state(player, state)
        await save_player(player)
        return SpecialResult(
            game=game,
            player=player,
            action=effect,
            target=target,
            private_message=f"Игрок {target.full_name} вынужден открыть карту {card_label(key)}.",
            public_message=f"{player.full_name} разыграл особое условие. {target.full_name} открывает карту {card_label(key)}: {result.trait_value}",
        )

    if effect == "extra_reveal_once":
        extra_rounds = list(state.get("extra_reveal_rounds") or [])
        if game.round not in extra_rounds:
            extra_rounds.append(game.round)
        state["extra_reveal_rounds"] = extra_rounds
        state["used"] = True
        set_player_special_state(player, state)
        await save_player(player)
        return SpecialResult(game=game, player=player, action=effect, private_message="В этом раунде вы можете открыть на одну карту персонажа больше.")

    if effect == "double_vote_once":
        state["used"] = True
        state["double_vote_round"] = game.round
        state["double_vote_step"] = game.phase_step
        set_player_special_state(player, state)
        await save_player(player)
        return SpecialResult(game=game, player=player, action=effect, private_message="Текущий бюллетень теперь будет считаться за два голоса.")

    if effect == "shield_target_once":
        if not target or target.faction_status != "alive":
            raise GameLogicError("Нужно выбрать живого игрока.")
        state["used"] = True
        state["protected_user_id"] = target.user_id
        state["protected_round"] = game.round
        set_player_special_state(player, state)
        await save_player(player)
        return SpecialResult(game=game, player=player, action=effect, target=target, private_message=f"Игрок {target.full_name} защищён от ближайшего изгнания в этом раунде.")

    if effect == "peek_bunker_once":
        state_data = endgame_state(game)
        deck_ids = state_data.get("bunker_deck_ids") or []
        next_index = int(state_data.get("next_bunker_index", 0))
        if next_index >= len(deck_ids):
            raise GameLogicError("Следующих карт бункера больше нет.")
        card = get_bunker_card(deck_ids[next_index])
        state["used"] = True
        set_player_special_state(player, state)
        await save_player(player)
        return SpecialResult(game=game, player=player, action=effect, private_message=f"Следующая карта бункера: {card['title']} — {card['text']}")

    if effect == "peek_threat_once":
        state_data = endgame_state(game)
        deck_ids = state_data.get("threat_deck_ids") or []
        next_index = int(state_data.get("next_threat_index", 0))
        if next_index >= len(deck_ids):
            raise GameLogicError("Будущих угроз больше нет.")
        card = get_threat_card(deck_ids[next_index])
        state["used"] = True
        set_player_special_state(player, state)
        await save_player(player)
        return SpecialResult(game=game, player=player, action=effect, private_message=f"Одна из будущих угроз: {card['title']} — {card['text']}")

    raise GameLogicError("Это особое условие не требует ручной активации.")


async def _protects_target(target: Player, players: list[Player], game: Game) -> bool:
    target_condition = player_condition(target)
    target_state = player_special_state(target)
    if condition_effect(target_condition) == "shield_self_once" and not target_state.get("used"):
        target_state["used"] = True
        set_player_special_state(target, target_state)
        await save_player(target)
        return True

    for player in players:
        condition = player_condition(player)
        state = player_special_state(player)
        if condition_effect(condition) == "shield_target_once":
            if state.get("protected_user_id") == target.user_id and state.get("protected_round") == game.round:
                state["protected_user_id"] = None
                state["protected_round"] = None
                set_player_special_state(player, state)
                await save_player(player)
                return True
    return False


async def _advance_after_ballot(game: Game, players: list[Player], exiled_now: list[Player], notes: list[str], outcome: str) -> RoundResolution:
    total_players = len(players)
    meta = _current_vote_meta(game, total_players)
    ballot_index = int(meta.get("ballot_index", 1))
    ballot_total = int(meta.get("ballot_total", 0))

    if ballot_index < ballot_total:
        next_index = ballot_index + 1
        game.phase = "voting"
        game.phase_step = _phase_step(next_index, False)
        set_revote_state(game, {"ballot_index": next_index, "ballot_total": ballot_total, "revote": False, "candidate_ids": []})
        game.phase_deadline_at = deadline_after(settings.voting_minutes)
        game.updated_at = iso_now()
        await update_game(game)
        return RoundResolution(game=game, players=await get_players(game.id), exiled=exiled_now, outcome=outcome, notes=notes)

    if game.round >= game.round_limit:
        return await _finalize_game(game, notes=notes, exiled_now=exiled_now)

    game.round += 1
    game.phase = "discussion"
    game.phase_step = "discussion"
    set_revote_state(game, {})
    opened_card = _open_next_bunker_card(game)
    game.phase_deadline_at = deadline_after(settings.discussion_minutes)
    game.updated_at = iso_now()
    await update_game(game)
    notes = notes + [f"Открыта следующая карта бункера: {opened_card['title']}."]
    return RoundResolution(game=game, players=await get_players(game.id), exiled=exiled_now, outcome=outcome, notes=notes)


async def finish_voting_round(game_id: str) -> RoundResolution:
    game = await get_game(game_id)
    if not game:
        raise GameLogicError("Партия не найдена.")
    if game.phase != "voting":
        raise GameLogicError("Сейчас нет активного голосования.")

    players = await get_players(game.id)
    votes = await get_votes(game.id, game.round, game.phase_step)
    alive_votes = [vote for vote in votes if vote.faction == "alive"]
    exiled_votes_raw = [vote for vote in votes if vote.faction == "exiled"]
    tally: Counter[str] = Counter()
    notes: list[str] = []

    players_by_id = {player.user_id: player for player in players}
    for vote in alive_votes:
        voter = players_by_id.get(vote.voter_id)
        if not voter:
            continue
        tally[vote.target_id] += _vote_weight_for_player(voter, game)

    common_exiled_target = _aggregate_exiled_vote(exiled_votes_raw, exiled_players(players))
    if common_exiled_target:
        tally[common_exiled_target] += 1
        notes.append("Изгнанные сформировали общий голос.")
    elif exiled_votes_raw:
        notes.append("Изгнанные не смогли сформировать общий голос.")

    if not tally:
        notes.append("В этом голосовании не удалось собрать решающий бюллетень.")
        return await _advance_after_ballot(game, players, [], notes, "no_exile")

    max_votes = max(tally.values())
    leaders = [int(target_id) for target_id, score in tally.items() if score == max_votes]
    meta = _current_vote_meta(game, len(players))

    if len(leaders) > 1:
        if not meta.get("revote"):
            set_revote_state(
                game,
                {
                    "ballot_index": int(meta.get("ballot_index", 1)),
                    "ballot_total": int(meta.get("ballot_total", 0)),
                    "revote": True,
                    "candidate_ids": leaders,
                },
            )
            game.phase = "voting"
            game.phase_step = _phase_step(int(meta.get("ballot_index", 1)), True)
            game.phase_deadline_at = deadline_after(settings.voting_minutes)
            game.updated_at = iso_now()
            await update_game(game)
            notes.append("Назначен перевыбор между лидерами.")
            return RoundResolution(game=game, players=players, exiled=[], outcome="revote_started", notes=notes)

        notes.append("После перевыбора единоличного изгнания не произошло.")
        return await _advance_after_ballot(game, players, [], notes, "no_exile")

    target_player = players_by_id.get(leaders[0])
    if not target_player:
        notes.append("Цель голосования не найдена.")
        return await _advance_after_ballot(game, players, [], notes, "no_exile")

    if await _protects_target(target_player, players, game):
        notes.append(f"Игрок {target_player.full_name} был спасён особым условием.")
        return await _advance_after_ballot(game, players, [], notes, "saved")

    target_player.faction_status = "exiled"
    target_player.is_exiled = 1
    set_revealed(target_player, CHARACTER_KEYS.copy())
    await save_player(target_player)
    notes.append(f"Игрок {target_player.full_name} перешёл в сторону изгнанных.")
    return await _advance_after_ballot(game, await get_players(game.id), [target_player], notes, "exiled")


async def _finalize_game(game: Game, notes: list[str] | None = None, exiled_now: list[Player] | None = None) -> RoundResolution:
    players = await get_players(game.id)
    bunker_side = alive_players(players)
    outside_side = exiled_players(players)
    notes = notes or []
    exiled_now = exiled_now or []

    if game.mode == "survival_story":
        _open_story_threats(game, count=2)

    bunker_score, bunker_success, bunker_notes = _evaluate_side(game, bunker_side, "bunker", use_bunker_cards=True, all_players=players)
    outside_score, outside_success, outside_notes = _evaluate_side(game, outside_side, "outside", use_bunker_cards=False, all_players=players)
    notes.extend(bunker_notes)
    if game.mode == "survival_story":
        notes.extend(outside_notes)
    else:
        outside_success = False

    winners = bunker_side if bunker_success else []
    outside_winners = outside_side if outside_success else []
    winner_ids = {player.user_id for player in winners + outside_winners}
    for player in players:
        player.faction_status = "winner" if player.user_id in winner_ids else "lost"
        await save_player(player)

    final_state = endgame_state(game)
    final_state["bunker_score"] = bunker_score
    final_state["outside_score"] = outside_score
    final_state["bunker_success"] = bunker_success
    final_state["outside_success"] = outside_success
    set_endgame_state(game, final_state)
    game.phase = "finished"
    game.phase_step = "finished"
    game.phase_deadline_at = None
    game.updated_at = iso_now()
    await update_game(game)
    return RoundResolution(
        game=game,
        players=await get_players(game.id),
        exiled=exiled_now,
        outcome="finished",
        finished=True,
        winners=winners,
        outside_winners=outside_winners,
        notes=notes,
    )


async def finish_game(game_id: str, forced: bool = False) -> tuple[Game, list[Player]]:
    game = await get_game(game_id)
    if not game:
        raise GameLogicError("Партия не найдена.")
    players = await get_players(game.id)
    if forced:
        for player in players:
            player.faction_status = "lost"
            await save_player(player)
    game.phase = "finished"
    game.phase_step = "finished"
    game.phase_deadline_at = None
    game.updated_at = iso_now()
    await update_game(game)
    return game, await get_players(game.id)


async def get_game_players_or_raise(game_id: str) -> tuple[Game, list[Player]]:
    game = await get_game(game_id)
    if not game:
        raise GameLogicError("Партия не найдена.")
    return game, await get_players(game.id)


async def get_player_for_webapp(game_id: str, player_id: str) -> tuple[Game, Player]:
    game = await get_game(game_id)
    player = await get_player_by_id(player_id)
    if not game or not player or player.game_id != game_id:
        raise GameLogicError("Игрок или партия не найдены.")
    return game, player


def analyze_survivors(players: list[Player]) -> list[str]:
    if not players:
        return ["Никто не пережил сценарий."]
    tags = _team_tag_pool(players)
    notes: list[str] = []
    if "medicine" in tags:
        notes.append("В команде есть медицинская экспертиза.")
    else:
        notes.append("Команде не хватает медицинской экспертизы.")
    if has_fertile_pair([player_cards(player) for player in players]):
        notes.append("Есть шанс на продолжение рода.")
    else:
        notes.append("Нет репродуктивно совместимой пары.")
    if INFECTIOUS_TAG in tags:
        notes.append("Среди выживших есть инфекционный риск.")
    return notes


def find_player_by_vote_token(players: list[Player], token: str) -> Player | None:
    normalized = token.strip().lstrip("@").lower()
    if not normalized:
        return None
    for player in players:
        if player.username and player.username.lower() == normalized:
            return player
    for player in players:
        if player.full_name.lower() == normalized:
            return player
    return None
