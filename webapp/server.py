from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bot.game_logic import (
    GameLogicError,
    build_public_game_payload,
    build_public_player_payload,
    get_game_players_or_raise,
    get_player_for_webapp,
)
from bot.strings import CARD_LABELS, WEBAPP_UI, mode_label, phase_label

app = FastAPI(title="Bunker MiniApp")
app.mount("/static", StaticFiles(directory="webapp/static"), name="static")
templates = Jinja2Templates(directory="webapp/templates")


def render_error(request: Request, message: str, status_code: int = 404):
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={"request": request, "message": message, "ui": WEBAPP_UI},
        status_code=status_code,
    )


@app.get("/webapp/{game_id}", response_class=HTMLResponse)
async def read_game(request: Request, game_id: str):
    try:
        game, players = await get_game_players_or_raise(game_id)
    except GameLogicError as exc:
        return render_error(request, str(exc))

    payload = build_public_game_payload(game, players)
    return templates.TemplateResponse(
        request=request,
        name="game.html",
        context={"request": request, "game": payload, "ui": WEBAPP_UI, "card_labels": CARD_LABELS},
    )


@app.get("/webapp/{game_id}/player/{player_id}", response_class=HTMLResponse)
async def read_player(request: Request, game_id: str, player_id: str):
    try:
        game, player = await get_player_for_webapp(game_id, player_id)
    except GameLogicError as exc:
        return render_error(request, str(exc))

    payload = build_public_player_payload(game, player)
    return templates.TemplateResponse(
        request=request,
        name="player.html",
        context={
            "request": request,
            "game": {
                "id": game.id,
                "phase_label": phase_label(game.phase),
                "mode_label": mode_label(game.mode),
                "catastrophe_title": game.catastrophe_title,
                "catastrophe_text": game.catastrophe_text,
            },
            "player": payload,
            "ui": WEBAPP_UI,
            "card_labels": CARD_LABELS,
        },
    )


@app.get("/api/game/{game_id}")
async def api_game(game_id: str):
    try:
        game, players = await get_game_players_or_raise(game_id)
    except GameLogicError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    return build_public_game_payload(game, players)


@app.get("/api/game/{game_id}/player/{player_id}")
async def api_player(game_id: str, player_id: str):
    try:
        game, player = await get_player_for_webapp(game_id, player_id)
    except GameLogicError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    return build_public_player_payload(game, player)
