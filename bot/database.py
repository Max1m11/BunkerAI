from __future__ import annotations

from contextlib import asynccontextmanager

import aiosqlite

from .config import settings
from .models import Game, Player, Vote


REBUILD_SCHEMA_SCRIPT = """
DROP TABLE IF EXISTS votes;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS games;

CREATE TABLE games (
    id                  TEXT PRIMARY KEY,
    chat_id             INTEGER NOT NULL,
    mode                TEXT NOT NULL,
    scenario_id         TEXT NOT NULL,
    scenario_title      TEXT NOT NULL,
    scenario_hint       TEXT NOT NULL,
    phase               TEXT NOT NULL,
    phase_step          TEXT NOT NULL DEFAULT '',
    round               INTEGER NOT NULL DEFAULT 0,
    round_limit         INTEGER NOT NULL DEFAULT 5,
    host_id             INTEGER NOT NULL,
    slots               INTEGER NOT NULL DEFAULT 0,
    catastrophe_id      TEXT NOT NULL,
    catastrophe_title   TEXT NOT NULL,
    catastrophe_text    TEXT NOT NULL,
    opened_bunker_cards TEXT NOT NULL DEFAULT '[]',
    opened_threat_cards TEXT NOT NULL DEFAULT '[]',
    revote_state        TEXT NOT NULL DEFAULT '{}',
    endgame_state       TEXT NOT NULL DEFAULT '{}',
    phase_deadline_at   TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);

CREATE TABLE players (
    id                      TEXT PRIMARY KEY,
    game_id                 TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    user_id                 INTEGER NOT NULL,
    username                TEXT,
    full_name               TEXT NOT NULL,
    faction_status          TEXT NOT NULL DEFAULT 'alive',
    is_exiled               INTEGER NOT NULL DEFAULT 0,
    character_cards         TEXT NOT NULL DEFAULT '{}',
    special_condition       TEXT NOT NULL DEFAULT '{}',
    special_state           TEXT NOT NULL DEFAULT '{}',
    revealed_character_keys TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE votes (
    id          TEXT PRIMARY KEY,
    game_id     TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    round       INTEGER NOT NULL,
    phase_step  TEXT NOT NULL,
    faction     TEXT NOT NULL,
    voter_id    INTEGER NOT NULL,
    target_id   TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE INDEX idx_games_chat_phase ON games(chat_id, phase);
CREATE INDEX idx_games_deadline ON games(phase, phase_deadline_at);
CREATE UNIQUE INDEX idx_players_unique_user_per_game ON players(game_id, user_id);
CREATE INDEX idx_votes_round ON votes(game_id, round, phase_step);
CREATE UNIQUE INDEX idx_votes_unique_voter_per_step
    ON votes(game_id, round, phase_step, voter_id);
"""

EXPECTED_GAME_COLUMNS = {
    "id",
    "chat_id",
    "mode",
    "scenario_id",
    "scenario_title",
    "scenario_hint",
    "phase",
    "phase_step",
    "round",
    "round_limit",
    "host_id",
    "slots",
    "catastrophe_id",
    "catastrophe_title",
    "catastrophe_text",
    "opened_bunker_cards",
    "opened_threat_cards",
    "revote_state",
    "endgame_state",
    "phase_deadline_at",
    "created_at",
    "updated_at",
}

EXPECTED_PLAYER_COLUMNS = {
    "id",
    "game_id",
    "user_id",
    "username",
    "full_name",
    "faction_status",
    "is_exiled",
    "character_cards",
    "special_condition",
    "special_state",
    "revealed_character_keys",
}

EXPECTED_VOTE_COLUMNS = {
    "id",
    "game_id",
    "round",
    "phase_step",
    "faction",
    "voter_id",
    "target_id",
    "created_at",
}


@asynccontextmanager
async def get_db():
    connection = await aiosqlite.connect(settings.db_path)
    connection.row_factory = aiosqlite.Row
    await connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        await connection.close()


async def _table_columns(db: aiosqlite.Connection, table_name: str) -> set[str]:
    async with db.execute(f"PRAGMA table_info({table_name})") as cursor:
        rows = await cursor.fetchall()
    return {row["name"] for row in rows}


async def _schema_matches(db: aiosqlite.Connection) -> bool:
    games_columns = await _table_columns(db, "games")
    players_columns = await _table_columns(db, "players")
    votes_columns = await _table_columns(db, "votes")
    return (
        EXPECTED_GAME_COLUMNS.issubset(games_columns)
        and EXPECTED_PLAYER_COLUMNS.issubset(players_columns)
        and EXPECTED_VOTE_COLUMNS.issubset(votes_columns)
    )


async def init_db() -> None:
    async with get_db() as db:
        if not await _schema_matches(db):
            await db.executescript(REBUILD_SCHEMA_SCRIPT)
        await db.commit()


async def create_game(game: Game) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO games (
                id, chat_id, mode, scenario_id, scenario_title, scenario_hint,
                phase, phase_step, round, round_limit, host_id, slots,
                catastrophe_id, catastrophe_title, catastrophe_text,
                opened_bunker_cards, opened_threat_cards, revote_state, endgame_state,
                phase_deadline_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game.id,
                game.chat_id,
                game.mode,
                game.scenario_id,
                game.scenario_title,
                game.scenario_hint,
                game.phase,
                game.phase_step,
                game.round,
                game.round_limit,
                game.host_id,
                game.slots,
                game.catastrophe_id,
                game.catastrophe_title,
                game.catastrophe_text,
                game.opened_bunker_cards,
                game.opened_threat_cards,
                game.revote_state,
                game.endgame_state,
                game.phase_deadline_at,
                game.created_at,
                game.updated_at,
            ),
        )
        await db.commit()


async def update_game(game: Game) -> None:
    async with get_db() as db:
        await db.execute(
            """
            UPDATE games
            SET mode = ?, scenario_id = ?, scenario_title = ?, scenario_hint = ?,
                phase = ?, phase_step = ?, round = ?, round_limit = ?, host_id = ?, slots = ?,
                catastrophe_id = ?, catastrophe_title = ?, catastrophe_text = ?,
                opened_bunker_cards = ?, opened_threat_cards = ?, revote_state = ?, endgame_state = ?,
                phase_deadline_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                game.mode,
                game.scenario_id,
                game.scenario_title,
                game.scenario_hint,
                game.phase,
                game.phase_step,
                game.round,
                game.round_limit,
                game.host_id,
                game.slots,
                game.catastrophe_id,
                game.catastrophe_title,
                game.catastrophe_text,
                game.opened_bunker_cards,
                game.opened_threat_cards,
                game.revote_state,
                game.endgame_state,
                game.phase_deadline_at,
                game.updated_at,
                game.id,
            ),
        )
        await db.commit()


async def get_game(game_id: str) -> Game | None:
    async with get_db() as db:
        async with db.execute("SELECT * FROM games WHERE id = ?", (game_id,)) as cursor:
            row = await cursor.fetchone()
    return Game(**dict(row)) if row else None


async def get_active_game_by_chat(chat_id: int) -> Game | None:
    async with get_db() as db:
        async with db.execute(
            """
            SELECT * FROM games
            WHERE chat_id = ? AND phase != 'finished'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (chat_id,),
        ) as cursor:
            row = await cursor.fetchone()
    return Game(**dict(row)) if row else None


async def list_active_games() -> list[Game]:
    async with get_db() as db:
        async with db.execute(
            """
            SELECT * FROM games
            WHERE phase != 'finished'
            ORDER BY created_at ASC
            """
        ) as cursor:
            rows = await cursor.fetchall()
    return [Game(**dict(row)) for row in rows]


async def create_player(player: Player) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO players (
                id, game_id, user_id, username, full_name,
                faction_status, is_exiled, character_cards, special_condition,
                special_state, revealed_character_keys
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                player.id,
                player.game_id,
                player.user_id,
                player.username,
                player.full_name,
                player.faction_status,
                player.is_exiled,
                player.character_cards,
                player.special_condition,
                player.special_state,
                player.revealed_character_keys,
            ),
        )
        await db.commit()


async def save_player(player: Player) -> None:
    async with get_db() as db:
        await db.execute(
            """
            UPDATE players
            SET username = ?, full_name = ?, faction_status = ?, is_exiled = ?,
                character_cards = ?, special_condition = ?, special_state = ?,
                revealed_character_keys = ?
            WHERE id = ?
            """,
            (
                player.username,
                player.full_name,
                player.faction_status,
                player.is_exiled,
                player.character_cards,
                player.special_condition,
                player.special_state,
                player.revealed_character_keys,
                player.id,
            ),
        )
        await db.commit()


async def get_player(game_id: str, user_id: int) -> Player | None:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM players WHERE game_id = ? AND user_id = ?",
            (game_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
    return Player(**dict(row)) if row else None


async def get_player_by_id(player_id: str) -> Player | None:
    async with get_db() as db:
        async with db.execute("SELECT * FROM players WHERE id = ?", (player_id,)) as cursor:
            row = await cursor.fetchone()
    return Player(**dict(row)) if row else None


async def get_players(game_id: str) -> list[Player]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM players WHERE game_id = ? ORDER BY full_name ASC",
            (game_id,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [Player(**dict(row)) for row in rows]


async def get_active_player_by_user(user_id: int) -> tuple[Game, Player] | None:
    async with get_db() as db:
        async with db.execute(
            """
            SELECT
                g.id AS game_id_ref,
                g.chat_id,
                g.mode,
                g.scenario_id,
                g.scenario_title,
                g.scenario_hint,
                g.phase,
                g.phase_step,
                g.round,
                g.round_limit,
                g.host_id,
                g.slots,
                g.catastrophe_id,
                g.catastrophe_title,
                g.catastrophe_text,
                g.opened_bunker_cards,
                g.opened_threat_cards,
                g.revote_state,
                g.endgame_state,
                g.phase_deadline_at,
                g.created_at AS game_created_at,
                g.updated_at AS game_updated_at,
                p.id AS player_id,
                p.game_id,
                p.user_id,
                p.username,
                p.full_name,
                p.faction_status,
                p.is_exiled,
                p.character_cards,
                p.special_condition,
                p.special_state,
                p.revealed_character_keys
            FROM players p
            JOIN games g ON g.id = p.game_id
            WHERE p.user_id = ? AND g.phase != 'finished'
            ORDER BY g.created_at DESC
            LIMIT 1
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        return None

    game = Game(
        id=row["game_id_ref"],
        chat_id=row["chat_id"],
        mode=row["mode"],
        scenario_id=row["scenario_id"],
        scenario_title=row["scenario_title"],
        scenario_hint=row["scenario_hint"],
        phase=row["phase"],
        phase_step=row["phase_step"],
        round=row["round"],
        round_limit=row["round_limit"],
        host_id=row["host_id"],
        slots=row["slots"],
        catastrophe_id=row["catastrophe_id"],
        catastrophe_title=row["catastrophe_title"],
        catastrophe_text=row["catastrophe_text"],
        opened_bunker_cards=row["opened_bunker_cards"],
        opened_threat_cards=row["opened_threat_cards"],
        revote_state=row["revote_state"],
        endgame_state=row["endgame_state"],
        phase_deadline_at=row["phase_deadline_at"],
        created_at=row["game_created_at"],
        updated_at=row["game_updated_at"],
    )
    player = Player(
        id=row["player_id"],
        game_id=row["game_id"],
        user_id=row["user_id"],
        username=row["username"],
        full_name=row["full_name"],
        faction_status=row["faction_status"],
        is_exiled=row["is_exiled"],
        character_cards=row["character_cards"],
        special_condition=row["special_condition"],
        special_state=row["special_state"],
        revealed_character_keys=row["revealed_character_keys"],
    )
    return game, player


async def cast_vote(vote: Vote) -> None:
    async with get_db() as db:
        await db.execute(
            """
            DELETE FROM votes
            WHERE game_id = ? AND round = ? AND phase_step = ? AND voter_id = ?
            """,
            (vote.game_id, vote.round, vote.phase_step, vote.voter_id),
        )
        await db.execute(
            """
            INSERT INTO votes (id, game_id, round, phase_step, faction, voter_id, target_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vote.id,
                vote.game_id,
                vote.round,
                vote.phase_step,
                vote.faction,
                vote.voter_id,
                vote.target_id,
                vote.created_at,
            ),
        )
        await db.commit()


async def get_votes(game_id: str, round_number: int, phase_step: str) -> list[Vote]:
    async with get_db() as db:
        async with db.execute(
            """
            SELECT * FROM votes
            WHERE game_id = ? AND round = ? AND phase_step = ?
            ORDER BY created_at ASC
            """,
            (game_id, round_number, phase_step),
        ) as cursor:
            rows = await cursor.fetchall()
    return [Vote(**dict(row)) for row in rows]
