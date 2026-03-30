from __future__ import annotations

import json

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from .callbacks import (
    CardViewCallback,
    JoinGameCallback,
    NextPhaseCallback,
    RevealTraitCallback,
    SetModeCallback,
    SpecialMenuCallback,
    SpecialUseCallback,
    VoteCallback,
)
from .config import settings
from .strings import CARD_LABELS, mode_label


def get_webapp_kb(game_id: str) -> InlineKeyboardMarkup:
    url = f"{settings.webapp_url.rstrip('/')}/webapp/{game_id}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть MiniApp", web_app=WebAppInfo(url=url))],
        ]
    )


def get_lobby_kb(game_id: str, current_mode: str) -> InlineKeyboardMarkup:
    basic_label = f"{'✓ ' if current_mode == 'basic_final' else ''}{mode_label('basic_final')}"
    story_label = f"{'✓ ' if current_mode == 'survival_story' else ''}{mode_label('survival_story')}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Присоединиться", callback_data=JoinGameCallback(game_id=game_id).pack())],
            [InlineKeyboardButton(text=basic_label, callback_data=SetModeCallback(game_id=game_id, mode="basic_final").pack())],
            [InlineKeyboardButton(text=story_label, callback_data=SetModeCallback(game_id=game_id, mode="survival_story").pack())],
        ]
    )


def get_next_phase_kb(game_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Закрыть обсуждение", callback_data=NextPhaseCallback(game_id=game_id).pack())],
        ]
    )


def get_reveal_kb(player, game_phase: str, game_round: int, condition: dict | None = None) -> InlineKeyboardMarkup:
    character_cards = json.loads(player.character_cards or "{}")
    revealed = set(json.loads(player.revealed_character_keys or "[]"))
    special_state = json.loads(player.special_state or "{}")
    rows: list[list[InlineKeyboardButton]] = []

    if game_phase == "discussion" and player.faction_status == "alive":
        bonus_rounds = set(special_state.get("extra_reveal_rounds") or [])
        allowed_reveals = 2 if game_round in bonus_rounds else 1
        revealed_this_round = int((special_state.get("round_reveal_counts") or {}).get(str(game_round), 0))
        if revealed_this_round < allowed_reveals:
            available_keys = ["profession"] if game_round == 1 else list(character_cards.keys())
            for key in available_keys:
                if key in revealed:
                    continue
                rows.append(
                    [
                        InlineKeyboardButton(
                            text=f"Открыть: {CARD_LABELS[key]}",
                            callback_data=RevealTraitCallback(game_id=player.game_id, trait_key=key).pack(),
                        )
                    ]
                )

    if condition:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Особое условие",
                    callback_data=SpecialMenuCallback(game_id=player.game_id).pack(),
                )
            ]
        )

    rows.append([get_webapp_kb(player.game_id).inline_keyboard[0][0]])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_vote_kb(players, game_id: str, candidate_ids: list[int] | None = None) -> InlineKeyboardMarkup:
    candidate_ids = candidate_ids or [player.user_id for player in players if player.faction_status == "alive"]
    rows: list[list[InlineKeyboardButton]] = []
    for player in players:
        if player.user_id not in candidate_ids:
            continue
        rows.append(
            [
                InlineKeyboardButton(
                    text=player.full_name,
                    callback_data=VoteCallback(game_id=game_id, target_user_id=player.user_id).pack(),
                )
            ]
        )
    rows.append([get_webapp_kb(game_id).inline_keyboard[0][0]])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_special_kb(player, game, players) -> InlineKeyboardMarkup:
    condition = json.loads(player.special_condition or "{}")
    target_mode = condition.get("target", "none")
    rows: list[list[InlineKeyboardButton]] = []

    if target_mode == "none":
        rows.append(
            [
                InlineKeyboardButton(
                    text="Активировать",
                    callback_data=SpecialUseCallback(game_id=game.id, target_user_id=player.user_id).pack(),
                )
            ]
        )
    else:
        for target_player in players:
            if target_mode in {"alive_any", "alive_other"} and target_player.faction_status != "alive":
                continue
            if target_mode == "alive_other" and target_player.user_id == player.user_id:
                continue
            rows.append(
                [
                    InlineKeyboardButton(
                        text=target_player.full_name,
                        callback_data=SpecialUseCallback(game_id=game.id, target_user_id=target_player.user_id).pack(),
                    )
                ]
            )

    rows.append(
        [
            InlineKeyboardButton(
                text="Назад к руке",
                callback_data=CardViewCallback(game_id=game.id).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
