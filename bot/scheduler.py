from __future__ import annotations

from apscheduler.jobstores.base import JobLookupError

from .database import get_game, list_active_games
from .game_logic import GameLogicError, parse_datetime, utc_now
from .runtime import scheduler


def _job_id(game_id: str) -> str:
    return f"game-deadline:{game_id}"


async def sync_game_deadline(game) -> None:
    try:
        scheduler.remove_job(_job_id(game.id))
    except JobLookupError:
        pass

    deadline = parse_datetime(game.phase_deadline_at)
    if not deadline or game.phase == "finished":
        return

    scheduler.add_job(handle_game_deadline, "date", id=_job_id(game.id), run_date=deadline, args=[game.id])


async def handle_game_deadline(game_id: str) -> None:
    game = await get_game(game_id)
    if not game or game.phase == "finished":
        return

    try:
        if game.phase == "discussion":
            from .actions import close_discussion_and_announce

            await close_discussion_and_announce(game.id, by_timer=True)
        elif game.phase == "voting":
            from .actions import finish_voting_and_announce

            await finish_voting_and_announce(game.id)
    except GameLogicError:
        return


async def restore_game_deadlines() -> None:
    for game in await list_active_games():
        deadline = parse_datetime(game.phase_deadline_at)
        if not deadline:
            continue
        if deadline <= utc_now():
            await handle_game_deadline(game.id)
            continue
        await sync_game_deadline(game)
