import json

from bot.keyboards import get_reveal_kb, get_return_to_chat_url, get_vote_kb
from bot.models import Game, Player


def _game(chat_id: int = -1001234567890) -> Game:
    return Game(
        id="game-1",
        chat_id=chat_id,
        mode="basic_final",
        scenario_id="scenario",
        scenario_title="Scenario",
        scenario_hint="Hint",
        phase="discussion",
        phase_step="discussion",
        round=2,
        round_limit=5,
        host_id=1,
        slots=3,
        catastrophe_id="cat",
        catastrophe_title="Catastrophe",
        catastrophe_text="Catastrophe text",
        opened_bunker_cards="[]",
        opened_threat_cards="[]",
        revote_state="{}",
        endgame_state=json.dumps({"_ui": {"messages": {"main": 77}}}),
        phase_deadline_at=None,
        created_at="2026-03-30T00:00:00+00:00",
        updated_at="2026-03-30T00:00:00+00:00",
    )


def _player(user_id: int = 1, name: str = "User 1") -> Player:
    return Player(
        id=f"player-{user_id}",
        game_id="game-1",
        user_id=user_id,
        username=f"user{user_id}",
        full_name=name,
        faction_status="alive",
        is_exiled=0,
        character_cards=json.dumps({"biology": {"text": "Test"}}),
        special_condition="{}",
        special_state="{}",
        revealed_character_keys="[]",
    )


def test_return_to_chat_url_is_built_from_supergroup_message():
    assert get_return_to_chat_url(_game()) == "https://t.me/c/1234567890/77"
    assert get_return_to_chat_url(_game(chat_id=-12345)) is None


def test_private_keyboards_include_return_to_chat_when_available():
    game = _game()
    player = _player()

    reveal_kb = get_reveal_kb(player, "discussion", 2, game=game)
    assert reveal_kb.inline_keyboard[-1][0].text == "Вернуться в чат"

    vote_kb = get_vote_kb([player], game.id, candidate_ids=[player.user_id], game=game)
    assert vote_kb.inline_keyboard[-1][0].text == "Вернуться в чат"
