from __future__ import annotations

import random


MANUAL_EFFECT_CODES = {
    "peek_hidden_once",
    "peek_condition_once",
    "force_reveal_once",
    "extra_reveal_once",
    "double_vote_once",
    "shield_target_once",
    "peek_bunker_once",
    "peek_threat_once",
}


def normalize_condition(condition: dict) -> dict:
    condition.setdefault("id", "condition_unknown")
    condition.setdefault("title", "Особое условие")
    condition.setdefault("text", "Эта карта меняет базовые правила партии.")
    condition.setdefault("effect_code", "none")
    condition.setdefault("timing", "passive")
    condition.setdefault("activation", "passive")
    condition.setdefault("target", "none")
    condition.setdefault("params", {})
    condition.setdefault("visibility", "secret")
    condition.setdefault("official_prototype", "special_condition")
    condition.setdefault("source_confidence", "medium")
    return condition


def condition_title(condition: dict) -> str:
    return str(normalize_condition(condition)["title"])


def condition_text(condition: dict) -> str:
    return str(normalize_condition(condition)["text"])


def condition_effect(condition: dict) -> str:
    return str(normalize_condition(condition)["effect_code"])


def condition_timing(condition: dict) -> str:
    return str(normalize_condition(condition)["timing"])


def condition_target(condition: dict) -> str:
    return str(normalize_condition(condition)["target"])


def is_manual_condition(condition: dict) -> bool:
    condition = normalize_condition(condition)
    return condition["activation"] == "manual" or condition_effect(condition) in MANUAL_EFFECT_CODES


def initial_condition_state(condition: dict, owner_user_id: int, candidate_user_ids: list[int]) -> dict:
    condition = normalize_condition(condition)
    params = dict(condition.get("params") or {})
    state: dict = {
        "used": False,
        "protected_user_id": None,
        "protected_round": None,
        "double_vote_round": None,
        "double_vote_step": None,
        "extra_reveal_rounds": [],
        "peeked_bunker_ids": [],
        "peeked_threat_ids": [],
        "goal_target_user_id": None,
    }

    if condition_effect(condition) in {"goal_target_alive", "goal_target_exiled"}:
        options = [user_id for user_id in candidate_user_ids if user_id != owner_user_id]
        state["goal_target_user_id"] = random.choice(options) if options else None

    if params:
        state["params_snapshot"] = params
    return state


def condition_available(condition: dict, state: dict, game_phase: str) -> bool:
    condition = normalize_condition(condition)
    state = dict(state or {})
    if not is_manual_condition(condition):
        return False
    if state.get("used"):
        return False
    timing = condition_timing(condition)
    if timing == "discussion":
        return game_phase == "discussion"
    if timing == "before_vote":
        return game_phase == "voting"
    if timing == "any":
        return True
    return game_phase == timing


def player_tag_set(character_cards: dict) -> set[str]:
    tags: set[str] = set()
    for card in character_cards.values():
        tags.update(card.get("tags", []))
    return tags


def has_fertile_pair(cards_list: list[dict]) -> bool:
    has_male = False
    has_female = False
    for cards in cards_list:
        tags = player_tag_set(cards)
        if "fertile" not in tags:
            continue
        if "male" in tags:
            has_male = True
        if "female" in tags:
            has_female = True
    return has_male and has_female
