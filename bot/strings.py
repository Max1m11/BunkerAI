from __future__ import annotations

from html import escape

from .cards import MODE_LABELS


CARD_LABELS = {
    "biology": "Биология",
    "profession": "Профессия",
    "health": "Здоровье",
    "hobby": "Хобби",
    "luggage": "Багаж",
    "fact": "Факт",
}

PHASE_LABELS = {
    "lobby": "Лобби",
    "discussion": "Обсуждение",
    "voting": "Тайное голосование",
    "endgame": "Финал",
    "finished": "Завершена",
}

WEBAPP_UI = {
    "title": "Бункер 3.x",
    "game_label": "Партия",
    "round_label": "Раунд",
    "slots_label": "Мест в бункере",
    "alive_label": "Живые",
    "exiled_label": "Изгнанные",
    "mode_label": "Режим",
    "scenario_hint_label": "Катастрофа",
    "bunker_label": "Открытые карты бункера",
    "threats_label": "Угрозы финала",
    "revealed_label": "Раскрытые карты",
    "hidden_label": "Скрыто",
    "back_label": "Назад к партии",
    "open_cards_label": "Публичные карты игрока",
    "not_found_title": "Ничего не найдено",
    "not_found_action": "Проверьте ссылку из бота и попробуйте снова.",
}


def safe(value: str | None) -> str:
    return escape(value or "")


def phase_label(phase: str) -> str:
    return PHASE_LABELS.get(phase, phase)


def mode_label(mode: str) -> str:
    return MODE_LABELS.get(mode, mode)


def card_label(key: str) -> str:
    return CARD_LABELS.get(key, key)


def player_status(player) -> str:
    status = getattr(player, "faction_status", "alive")
    if status == "winner":
        return "Победитель"
    if status == "lost":
        return "Проиграл"
    if status == "exiled":
        return "Изгнанный"
    return "В игре"


def player_status_badge(player) -> str:
    status = getattr(player, "faction_status", "alive")
    if status == "winner":
        return "Победитель"
    if status == "lost":
        return "Проиграл"
    if status == "exiled":
        return "Изгнанный"
    return "В игре"


def new_game_text(game, host_name: str) -> str:
    return (
        "<b>Создана новая партия «Бункер»</b>\n\n"
        f"<b>Катастрофа:</b> {safe(game.catastrophe_title)}\n"
        f"{safe(game.catastrophe_text)}\n\n"
        f"<b>Режим:</b> {safe(mode_label(game.mode))}\n"
        f"<b>Ведущий:</b> {safe(host_name)}\n\n"
        "Присоединяйтесь кнопкой или через /join. "
        "Хост может переключить режим прямо в лобби и запустить игру командой /start_game."
    )


def lobby_players_text(players: list) -> str:
    if not players:
        return "Пока в лобби никого нет."
    lines = ["<b>Игроки в лобби</b>"]
    for index, player in enumerate(players, start=1):
        username = f" (@{player.username})" if player.username else ""
        lines.append(f"{index}. {safe(player.full_name)}{safe(username)}")
    return "\n".join(lines)


def lobby_joined_text(player_name: str, count: int) -> str:
    return f"<b>{safe(player_name)}</b> присоединился к партии. Сейчас в лобби: {count}."


def mode_changed_text(mode: str) -> str:
    return f"Режим партии: <b>{safe(mode_label(mode))}</b>."


def discussion_started_text(game, bunker_card: dict, alive_count: int, minutes: int) -> str:
    return (
        "<b>Раунд обсуждения открыт</b>\n\n"
        f"<b>Режим:</b> {safe(mode_label(game.mode))}\n"
        f"<b>Раунд:</b> {game.round}/{game.round_limit}\n"
        f"<b>Катастрофа:</b> {safe(game.catastrophe_title)}\n"
        f"<b>Живых:</b> {alive_count}\n"
        f"<b>Открыта карта бункера:</b> {safe(bunker_card['title'])}\n"
        f"{safe(bunker_card['text'])}\n\n"
        f"У каждого живого игрока есть {minutes} мин., чтобы раскрыть положенную карту в личных сообщениях."
    )


def no_vote_round_text(round_number: int) -> str:
    return (
        "<b>Раунд без изгнания</b>\n\n"
        f"В раунде {round_number} по таблице для этого числа игроков голосование не проводится."
    )


def voting_started_text(game, ballot_index: int, ballot_total: int, minutes: int, revote: bool = False) -> str:
    prefix = "Назначен перевыбор между лидерами." if revote else "Открыто тайное голосование."
    return (
        "<b>Тайное голосование</b>\n\n"
        f"{prefix}\n"
        f"<b>Раунд:</b> {game.round}/{game.round_limit}\n"
        f"<b>Бюллетень:</b> {ballot_index} из {ballot_total}\n"
        f"Голосование проходит только в личных сообщениях в течение {minutes} мин."
    )


def game_status_text(game, alive_count: int, exiled_count: int, bunker_cards: list[dict], threats: list[dict]) -> str:
    lines = [
        "<b>Статус партии</b>",
        "",
        f"<b>Режим:</b> {safe(mode_label(game.mode))}",
        f"<b>Фаза:</b> {safe(phase_label(game.phase))}",
        f"<b>Раунд:</b> {game.round}/{game.round_limit}",
        f"<b>Катастрофа:</b> {safe(game.catastrophe_title)}",
        f"<b>Живых:</b> {alive_count}",
        f"<b>Изгнанных:</b> {exiled_count}",
        f"<b>Мест в бункере:</b> {game.slots}",
    ]
    if bunker_cards:
        lines.append("")
        lines.append("<b>Открытые карты бункера:</b>")
        lines.extend(f"• {safe(card['title'])}" for card in bunker_cards)
    if threats:
        lines.append("")
        lines.append("<b>Угрозы финала:</b>")
        lines.extend(f"• {safe(card['title'])}" for card in threats)
    return "\n".join(lines)


def group_reveal_redirect_text() -> str:
    return "Раскрытие карт делается в личных сообщениях с ботом. Откройте /start в ЛС."


def group_vote_redirect_text(game, ballot_index: int, ballot_total: int, revote: bool = False) -> str:
    prefix = "Сейчас идёт перевыбор." if revote else "Сейчас идёт тайное голосование."
    return (
        f"{prefix} Бюллетень {ballot_index} из {ballot_total}. "
        "Голосуйте в личных сообщениях с ботом через /start."
    )


def private_hand_text(game, player, character_cards: dict, condition: dict, revealed: list[str], special_state: dict) -> str:
    lines = [
        "<b>Ваша рука</b>",
        "",
        f"<b>Режим:</b> {safe(mode_label(game.mode))}",
        f"<b>Фаза:</b> {safe(phase_label(game.phase))}",
        f"<b>Раунд:</b> {game.round}/{game.round_limit}",
        f"<b>Статус:</b> {safe(player_status(player))}",
        f"<b>Катастрофа:</b> {safe(game.catastrophe_title)}",
        "",
    ]
    for key in ("biology", "profession", "health", "hobby", "luggage", "fact"):
        card = character_cards.get(key)
        if not card:
            continue
        icon = "Открыто" if key in revealed else "Скрыто"
        lines.append(f"<b>{card_label(key)}:</b> {safe(card['text'])} <i>({icon})</i>")
    lines.append("")
    lines.append(f"<b>Особое условие:</b> {safe(condition.get('title', 'Неизвестно'))}")
    lines.append(safe(condition.get("text", "")))
    if special_state.get("goal_target_user_name"):
        lines.append(f"<b>Тайная цель:</b> {safe(special_state['goal_target_user_name'])}")
    return "\n".join(lines)


def special_condition_text(condition: dict, special_state: dict) -> str:
    lines = [
        "<b>Особое условие</b>",
        "",
        f"<b>{safe(condition.get('title'))}</b>",
        safe(condition.get("text")),
    ]
    if special_state.get("goal_target_user_name"):
        lines.append("")
        lines.append(f"<b>Назначенная цель:</b> {safe(special_state['goal_target_user_name'])}")
    return "\n".join(lines)


def private_vote_prompt(game, ballot_index: int, ballot_total: int, revote: bool = False) -> str:
    prefix = "Перевыбор между лидерами." if revote else "Выберите, кого хотите изгнать в этом бюллетене."
    return (
        "<b>Тайное голосование</b>\n\n"
        f"{prefix}\n"
        f"<b>Раунд:</b> {game.round}/{game.round_limit}\n"
        f"<b>Бюллетень:</b> {ballot_index} из {ballot_total}"
    )


def reveal_announcement(player_name: str, trait_key: str, trait_value: str, auto_revealed: bool = False) -> str:
    prefix = "Авто-раскрытие" if auto_revealed else "Раскрытие"
    return (
        f"<b>{prefix}</b>\n\n"
        f"<b>{safe(player_name)}</b> открыл карту:\n"
        f"<b>{safe(card_label(trait_key))}</b> — {safe(trait_value)}"
    )


def vote_saved_text(total_votes: int, total_expected: int) -> str:
    return f"Бюллетень принят. Получено голосов: {total_votes}/{total_expected}."


def revote_text(candidate_names: list[str]) -> str:
    joined = ", ".join(candidate_names)
    return f"<b>Ничья</b>\n\nНазначен один перевыбор между: {safe(joined)}."


def exile_text(player_name: str) -> str:
    return f"<b>{safe(player_name)}</b> изгнан и переходит в сторону изгнанных."


def saved_text(player_name: str | None = None) -> str:
    if player_name:
        return f"<b>{safe(player_name)}</b> должен был быть изгнан, но сработало особое условие."
    return "Игрок должен был быть изгнан, но сработало особое условие."


def no_exile_text() -> str:
    return "После перевыбора единого результата не получилось. В этом бюллетене никто не изгнан."


def next_round_text(round_number: int, bunker_card: dict) -> str:
    return (
        f"<b>Начинается раунд {round_number}</b>\n"
        f"<b>Новая карта бункера:</b> {safe(bunker_card['title'])} — {safe(bunker_card['text'])}"
    )


def endgame_started_text(mode: str, threats: list[dict]) -> str:
    lines = [
        "<b>Финал партии</b>",
        "",
        f"<b>Режим:</b> {safe(mode_label(mode))}",
    ]
    if threats:
        lines.append("<b>Открытые угрозы:</b>")
        lines.extend(f"• {safe(card['title'])}: {safe(card['text'])}" for card in threats)
    return "\n".join(lines)


def finished_text(
    game,
    bunker_winners: list,
    outside_winners: list,
    notes: list[str],
    ai_verdict: str | None = None,
    forced: bool = False,
) -> str:
    lines = [
        "<b>Партия завершена</b>" if not forced else "<b>Партия остановлена ведущим</b>",
        "",
        f"<b>Режим:</b> {safe(mode_label(game.mode))}",
        f"<b>Катастрофа:</b> {safe(game.catastrophe_title)}",
    ]

    lines.append("")
    lines.append("<b>Победители в бункере:</b>")
    if bunker_winners:
        lines.extend(f"• {safe(player.full_name)}" for player in bunker_winners)
    else:
        lines.append("• Нет")

    lines.append("")
    lines.append("<b>Победители среди изгнанных:</b>")
    if outside_winners:
        lines.extend(f"• {safe(player.full_name)}" for player in outside_winners)
    else:
        lines.append("• Нет")

    if notes:
        lines.append("")
        lines.append("<b>Итоговые заметки:</b>")
        lines.extend(f"• {safe(item)}" for item in notes)

    if ai_verdict:
        lines.append("")
        lines.append("<b>Комментарий ИИ-ведущего:</b>")
        lines.append(safe(ai_verdict))

    return "\n".join(lines)
