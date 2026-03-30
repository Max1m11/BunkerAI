import json
from datetime import datetime, timezone

import pytest

from bot.cards import CHARACTER_KEYS, SCENARIOS, SPECIAL_CONDITIONS, get_random_scenario, get_special_condition
from bot.config import settings
from bot.database import create_game, get_game, get_player, get_players, init_db, save_player, update_game
from bot.game_logic import (
    GameLogicError,
    _catastrophe_rules,
    _evaluate_side,
    add_player_to_lobby,
    close_discussion,
    current_vote_state,
    endgame_state,
    finish_voting_round,
    opened_bunker_cards,
    opened_threat_cards,
    player_special_state,
    reveal_trait,
    set_endgame_state,
    set_player_condition,
    set_player_special_state,
    start_game,
    submit_vote,
)
from bot.models import Game, Player
from bot.specials import initial_condition_state


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _create_lobby(tmp_path, player_count: int, mode: str = "basic_final") -> Game:
    settings.db_path = str(tmp_path / "test.db")
    await init_db()
    scenario = get_random_scenario()
    title = f"{scenario['emoji']} {scenario['title']}"
    game = Game(
        id="game-1",
        chat_id=100,
        mode=mode,
        scenario_id=scenario["id"],
        scenario_title=title,
        scenario_hint=scenario["hint"],
        phase="lobby",
        phase_step="lobby",
        round=0,
        round_limit=5,
        host_id=1,
        slots=0,
        catastrophe_id=scenario["id"],
        catastrophe_title=title,
        catastrophe_text=scenario["text"],
        phase_deadline_at=None,
        created_at=_now(),
        updated_at=_now(),
    )
    await create_game(game)
    for user_id in range(1, player_count + 1):
        await add_player_to_lobby(game, user_id, f"user{user_id}", f"Player {user_id}")
    return game


def _scenario_game(scenario_id: str) -> Game:
    scenario = next(item for item in SCENARIOS if item["id"] == scenario_id)
    title = f"{scenario['emoji']} {scenario['title']}"
    return Game(
        id=f"game-{scenario_id}",
        chat_id=100,
        mode="survival_story",
        scenario_id=scenario_id,
        scenario_title=title,
        scenario_hint=scenario["hint"],
        phase="endgame",
        phase_step="endgame",
        round=5,
        round_limit=5,
        host_id=1,
        slots=2,
        catastrophe_id=scenario_id,
        catastrophe_title=title,
        catastrophe_text=scenario["text"],
        opened_bunker_cards="[]",
        opened_threat_cards="[]",
        revote_state="{}",
        endgame_state="{}",
        phase_deadline_at=None,
        created_at=_now(),
        updated_at=_now(),
    )


def _player_with_tags(user_id: int, biology_tags: list[str], extra_tags: list[str] | None = None) -> Player:
    cards = {
        "biology": {"text": f"Biology {user_id}", "tags": biology_tags},
        "profession": {"text": f"Profession {user_id}", "tags": extra_tags or []},
        "health": {"text": f"Health {user_id}", "tags": []},
        "hobby": {"text": f"Hobby {user_id}", "tags": []},
        "luggage": {"text": f"Luggage {user_id}", "tags": []},
        "fact": {"text": f"Fact {user_id}", "tags": []},
    }
    return Player(
        id=f"player-{user_id}",
        game_id="game-test",
        user_id=user_id,
        username=f"user{user_id}",
        full_name=f"Player {user_id}",
        faction_status="alive",
        is_exiled=0,
        character_cards=json.dumps(cards),
        special_condition="{}",
        special_state="{}",
        revealed_character_keys="[]",
    )


async def _neutralize_conditions(game_id: str) -> None:
    players = await get_players(game_id)
    candidate_ids = [player.user_id for player in players]
    neutral = get_special_condition("cond_bonus_team_repair")
    for player in players:
        set_player_condition(player, dict(neutral))
        set_player_special_state(player, initial_condition_state(dict(neutral), player.user_id, candidate_ids))
        await save_player(player)


@pytest.mark.asyncio
async def test_init_db_keeps_data_when_schema_is_already_current(tmp_path):
    game = await _create_lobby(tmp_path, player_count=4)
    await init_db()
    saved = await get_game(game.id)
    assert saved is not None
    assert saved.id == game.id


@pytest.mark.asyncio
async def test_start_game_uses_official_character_structure_and_slots(tmp_path):
    game = await _create_lobby(tmp_path, player_count=5)
    started_game, players, bunker_card = await start_game(game.id)

    assert started_game.phase == "discussion"
    assert started_game.round == 1
    assert started_game.slots == 2
    assert bunker_card["id"]
    assert len(opened_bunker_cards(started_game)) == 1

    first_player = players[0]
    cards = json.loads(first_player.character_cards)
    condition = json.loads(first_player.special_condition)
    assert set(cards.keys()) == set(CHARACTER_KEYS)
    assert "phobia" not in cards
    assert condition["id"]
    assert condition["effect_code"]


@pytest.mark.asyncio
async def test_start_game_preserves_ui_bindings_for_group_and_private_messages(tmp_path):
    game = await _create_lobby(tmp_path, player_count=4)
    set_endgame_state(game, {"_ui": {"messages": {"main": 777}, "initiator_name": "Host"}})
    await update_game(game)

    players_before = await get_players(game.id)
    first_player = players_before[0]
    set_player_special_state(first_player, {"_ui": {"messages": {"hand": 111, "vote": 222}}})
    await save_player(first_player)

    started_game, started_players, _ = await start_game(game.id)

    assert endgame_state(started_game).get("_ui", {}).get("messages", {}).get("main") == 777
    started_first_player = next(player for player in started_players if player.id == first_player.id)
    assert player_special_state(started_first_player).get("_ui", {}).get("messages", {}).get("hand") == 111


@pytest.mark.asyncio
async def test_round_one_only_profession_and_first_two_rounds_can_skip_voting(tmp_path):
    game = await _create_lobby(tmp_path, player_count=5)
    await start_game(game.id)

    result = await reveal_trait(game.id, 1, "profession")
    assert result.trait_key == "profession"

    with pytest.raises(GameLogicError):
        await reveal_trait(game.id, 1, "health")

    close_result = await close_discussion(game.id)
    assert close_result["kind"] == "no_vote_round"
    assert close_result["skipped_round"] == 1
    assert close_result["game"].round == 2
    assert len(opened_bunker_cards(close_result["game"])) == 2


@pytest.mark.asyncio
async def test_revote_exiles_single_leader_after_tie(tmp_path):
    game = await _create_lobby(tmp_path, player_count=5)
    await start_game(game.id)
    await _neutralize_conditions(game.id)
    await close_discussion(game.id)
    await close_discussion(game.id)

    voting = await close_discussion(game.id)
    assert voting["kind"] == "voting_started"

    await submit_vote(game.id, 1, 5)
    await submit_vote(game.id, 2, 5)
    await submit_vote(game.id, 3, 4)
    await submit_vote(game.id, 4, 4)
    await submit_vote(game.id, 5, 3)

    revote_resolution = await finish_voting_round(game.id)
    assert revote_resolution.outcome == "revote_started"

    vote_state = current_vote_state(revote_resolution.game, revote_resolution.players)
    assert vote_state["revote"] is True
    assert set(vote_state["candidate_ids"]) == {4, 5}

    await submit_vote(game.id, 1, 4)
    await submit_vote(game.id, 2, 4)
    await submit_vote(game.id, 3, 4)
    await submit_vote(game.id, 4, 5)
    await submit_vote(game.id, 5, 4)

    resolution = await finish_voting_round(game.id)
    assert resolution.outcome == "exiled"
    assert resolution.exiled[0].user_id == 4

    exiled_player = await get_player(game.id, 4)
    assert exiled_player is not None
    assert exiled_player.faction_status == "exiled"
    assert exiled_player.is_exiled == 1


@pytest.mark.asyncio
async def test_exiled_players_form_common_vote_in_following_rounds(tmp_path):
    game = await _create_lobby(tmp_path, player_count=5)
    await start_game(game.id)
    await _neutralize_conditions(game.id)
    await close_discussion(game.id)
    await close_discussion(game.id)
    await close_discussion(game.id)

    for voter_id in range(1, 6):
        await submit_vote(game.id, voter_id, 5)
    round3 = await finish_voting_round(game.id)
    assert round3.outcome == "exiled"
    assert round3.exiled[0].user_id == 5
    assert round3.game.phase == "discussion"
    assert round3.game.round == 4

    round4_voting = await close_discussion(game.id)
    assert round4_voting["kind"] == "voting_started"

    progress = await submit_vote(game.id, 1, 2)
    assert progress.total_expected == 5
    await submit_vote(game.id, 2, 3)
    await submit_vote(game.id, 3, 2)
    await submit_vote(game.id, 4, 3)
    await submit_vote(game.id, 5, 2)

    round4 = await finish_voting_round(game.id)
    assert round4.outcome == "exiled"
    assert round4.exiled[0].user_id == 2


@pytest.mark.asyncio
async def test_survival_story_finishes_after_five_rounds_and_opens_threats(tmp_path):
    game = await _create_lobby(tmp_path, player_count=4, mode="survival_story")
    await start_game(game.id)
    await _neutralize_conditions(game.id)

    await close_discussion(game.id)
    await close_discussion(game.id)
    await close_discussion(game.id)

    await close_discussion(game.id)
    for voter_id in range(1, 5):
        await submit_vote(game.id, voter_id, 4)
    round4 = await finish_voting_round(game.id)
    assert round4.outcome == "exiled"
    assert round4.game.round == 5

    await close_discussion(game.id)
    for voter_id in range(1, 5):
        target = 3 if voter_id != 4 else 3
        await submit_vote(game.id, voter_id, target)
    final_resolution = await finish_voting_round(game.id)

    assert final_resolution.finished is True
    assert final_resolution.game.phase == "finished"
    assert len(opened_threat_cards(final_resolution.game)) == 2
    assert all(player.faction_status in {"winner", "lost"} for player in final_resolution.players)


def test_special_conditions_have_real_effect_codes_and_no_phobia():
    ids = [card["id"] for card in SPECIAL_CONDITIONS]
    assert len(ids) == len(set(ids))
    for card in SPECIAL_CONDITIONS:
        assert card["effect_code"] != "none"
        assert card["official_prototype"] == "special_condition"
        assert "placeholder" not in card["id"]
        assert "phobia" not in card["id"]


def test_endgame_uses_live_scenario_rules_from_cards_catalog():
    for scenario in SCENARIOS:
        game = _scenario_game(scenario["id"])
        required, helpful, harmful, threshold, requires_pair = _catastrophe_rules(game)

        assert required == scenario["required_tags"]
        assert helpful == scenario["helpful_tags"]
        assert harmful == scenario["harmful_tags"]
        assert threshold == scenario["threshold"]
        assert requires_pair is scenario["requires_pair"]


@pytest.mark.parametrize(
    ("scenario_id", "helpful_tag", "harmful_tag"),
    [
        ("cat_nuclear_winter", "navigation", "severe_disability"),
        ("cat_global_pandemic", None, "chronic_illness"),
        ("cat_ice_age", "medicine", "severe_disability"),
        ("cat_solar_storm", "discipline", None),
    ],
)
def test_endgame_scores_reflect_catalog_helpful_and_harmful_tags(scenario_id: str, helpful_tag: str | None, harmful_tag: str | None):
    game = _scenario_game(scenario_id)

    base_players = [
        _player_with_tags(1, ["male", "fertile"]),
        _player_with_tags(2, ["female", "fertile"]),
    ]
    base_score, _, _ = _evaluate_side(game, base_players, "bunker", use_bunker_cards=False, all_players=base_players)

    if helpful_tag:
        helpful_players = [
            _player_with_tags(1, ["male", "fertile"], [helpful_tag]),
            _player_with_tags(2, ["female", "fertile"]),
        ]
        helpful_score, _, _ = _evaluate_side(
            game,
            helpful_players,
            "bunker",
            use_bunker_cards=False,
            all_players=helpful_players,
        )
        assert helpful_score == base_score + 1

    if harmful_tag:
        harmful_players = [
            _player_with_tags(1, ["male", "fertile"], [harmful_tag]),
            _player_with_tags(2, ["female", "fertile"]),
        ]
        harmful_score, _, _ = _evaluate_side(
            game,
            harmful_players,
            "bunker",
            use_bunker_cards=False,
            all_players=harmful_players,
        )
        assert harmful_score == base_score - 2


def test_endgame_fails_fast_for_unknown_catastrophe_id():
    game = _scenario_game("cat_asteroid")
    game.catastrophe_id = "cat_unknown"

    players = [
        _player_with_tags(1, ["male", "fertile"]),
        _player_with_tags(2, ["female", "fertile"]),
    ]

    with pytest.raises(GameLogicError, match="Неизвестная катастрофа"):
        _evaluate_side(game, players, "bunker", use_bunker_cards=False, all_players=players)
