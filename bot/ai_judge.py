from __future__ import annotations

import json

import httpx

from .config import settings
from .game_logic import player_cards
from .models import Game, Player
from .specials import condition_title


def _player_summary(player: Player) -> str:
    cards = player_cards(player)
    condition = json.loads(player.special_condition or "{}")
    return (
        f"- {player.full_name}: "
        f"биология={cards.get('biology', {}).get('text', '—')}; "
        f"профессия={cards.get('profession', {}).get('text', '—')}; "
        f"здоровье={cards.get('health', {}).get('text', '—')}; "
        f"хобби={cards.get('hobby', {}).get('text', '—')}; "
        f"багаж={cards.get('luggage', {}).get('text', '—')}; "
        f"факт={cards.get('fact', {}).get('text', '—')}; "
        f"особое условие={condition_title(condition)}"
    )


def _group_block(title: str, players: list[Player]) -> str:
    if not players:
        return f"{title}:\n- никого"
    return f"{title}:\n" + "\n".join(_player_summary(player) for player in players)


def build_verdict_prompt(
    game: Game,
    bunker_winners: list[Player],
    outside_winners: list[Player],
    checks: list[str],
    deterministic_notes: list[str],
) -> str:
    checks_block = "\n".join(f"- {item}" for item in checks) if checks else "- без дополнительных проверок"
    notes_block = "\n".join(f"- {item}" for item in deterministic_notes) if deterministic_notes else "- без заметок"
    return (
        "Ты выступаешь как ИИ-ведущий партии «Бункер».\n"
        "Базовый исход уже посчитан кодом. Тебе не нужно перепроверять правила, только коротко и атмосферно "
        "прокомментировать результат на русском языке.\n\n"
        f"Катастрофа: {game.catastrophe_title}\n"
        f"Описание катастрофы: {game.catastrophe_text}\n"
        f"Режим: {game.mode}\n\n"
        f"{_group_block('Победители в бункере', bunker_winners)}\n\n"
        f"{_group_block('Победители среди изгнанных', outside_winners)}\n\n"
        f"Детерминированные проверки:\n{checks_block}\n\n"
        f"Детерминированные заметки движка:\n{notes_block}\n\n"
        "Сформулируй 1 короткий абзац: почему этот исход выглядит правдоподобным, какие сильные или слабые стороны "
        "ты видишь у победившей стороны, и чем для неё может закончиться ближайшее будущее."
    )


async def _request_openrouter(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.ai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.ai_model,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        payload = response.json()
    return payload["choices"][0]["message"]["content"].strip()


async def _request_gemini(prompt: str) -> str:
    model = settings.ai_model.split("/", 1)[-1]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.ai_api_key}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        response.raise_for_status()
        payload = response.json()
    return payload["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _request_anthropic(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ai_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.ai_model,
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        payload = response.json()
    return payload["content"][0]["text"].strip()


async def generate_ai_verdict(
    game: Game,
    bunker_winners: list[Player],
    outside_winners: list[Player],
    checks: list[str],
    deterministic_notes: list[str],
) -> str | None:
    if not settings.ai_api_key:
        return None
    if not bunker_winners and not outside_winners:
        return None

    prompt = build_verdict_prompt(game, bunker_winners, outside_winners, checks, deterministic_notes)
    provider = settings.ai_provider.lower().strip()

    try:
        if provider == "openrouter":
            return await _request_openrouter(prompt)
        if provider == "gemini":
            return await _request_gemini(prompt)
        if provider == "anthropic":
            return await _request_anthropic(prompt)
    except Exception:
        return None

    return None
