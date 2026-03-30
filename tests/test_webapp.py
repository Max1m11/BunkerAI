import httpx
import pytest

from bot.cards import get_random_scenario
from bot.config import settings
from bot.database import create_game, get_players, init_db
from bot.game_logic import add_player_to_lobby, reveal_trait, start_game
from bot.models import Game
from webapp.server import app


def _game_fixture() -> Game:
    scenario = get_random_scenario()
    title = f"{scenario['emoji']} {scenario['title']}"
    return Game(
        id="web-game",
        chat_id=777,
        mode="basic_final",
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
        created_at="2026-03-30T00:00:00+00:00",
        updated_at="2026-03-30T00:00:00+00:00",
    )


@pytest.mark.asyncio
async def test_webapp_api_and_pages_match_public_contract(tmp_path):
    settings.db_path = str(tmp_path / "webapp.db")
    await init_db()

    game = _game_fixture()
    await create_game(game)
    for user_id in range(1, 5):
        await add_player_to_lobby(game, user_id, f"user{user_id}", f"User {user_id}")

    await start_game(game.id)
    await reveal_trait(game.id, 1, "profession")

    players = await get_players(game.id)
    target_player = players[0]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/game/{game.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "basic_final"
        assert data["catastrophe"]["title"]
        assert data["alive_count"] == 4
        assert isinstance(data["players"][0]["revealed_cards"], dict)
        assert "alive_players" in data
        assert "exiled_players" in data

        response = await client.get(f"/api/game/{game.id}/player/{target_player.id}")
        assert response.status_code == 200
        player_data = response.json()
        assert "hidden_count" in player_data
        assert "revealed_cards" in player_data
        assert "profession" in player_data["revealed_cards"] or player_data["revealed_cards"] == {}

        response = await client.get(f"/webapp/{game.id}")
        assert response.status_code == 200
        assert game.catastrophe_title in response.text

        response = await client.get(f"/webapp/{game.id}/player/{target_player.id}")
        assert response.status_code == 200
        assert target_player.full_name in response.text

        response = await client.get("/webapp/missing-game")
        assert response.status_code == 404
