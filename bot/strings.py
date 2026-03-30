from __future__ import annotations

from html import escape

from .cards import MODE_LABELS
from .config import settings


CARD_LABELS = {
    "biology": "Биология",
    "profession": "Профессия",
    "health": "Здоровье",
    "hobby": "Хобби",
    "luggage": "Багаж",
    "fact": "Факт",
}

CARD_ICONS = {
    "biology": "🧬",
    "profession": "💼",
    "health": "🩺",
    "hobby": "🎯",
    "luggage": "🎒",
    "fact": "📌",
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
    "game_title": "Бункер",
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
    "hidden_cards_label": "Не раскрыто",
    "back_label": "Назад к партии",
    "open_cards_label": "Публичные карты игрока",
    "all_players_tab": "Все игроки",
    "alive_players_tab": "Живые",
    "exiled_players_tab": "Изгнанные",
    "candidates_tab": "На вылет",
    "timer_label": "До конца",
    "voting_private_cta": "Голосование в ЛС",
    "voting_private_hint": "Голоса скрыты до конца раунда",
    "private_visible_label": "Скрытые карты видны только вам",
    "self_label": "Это вы",
    "players_section_title": "Участники",
    "exiled_section_title": "Сторона изгнанных",
    "bunker_card_label": "Карта бункера",
    "threat_card_label": "Угроза",
    "profession_hidden": "Профессия скрыта",
    "empty_revealed_title": "Пока нет открытых карт",
    "empty_revealed_text": "Игрок ещё не раскрыл ни одной характеристики публично.",
    "error_eyebrow": "MiniApp",
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


def bot_mention() -> str:
    return f"@{settings.bot_username.lstrip('@')}"


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


def private_start_intro_text() -> str:
    return (
        "<b>БункерAI</b>\n\n"
        "Я ИИ-ведущий партии и помогаю проводить игру: показываю вашу руку, принимаю тайные голоса "
        "и подсказываю, что делать дальше.\n\n"
        "<b>Что делать:</b>\n"
        "• создайте партию в группе через /new_game\n"
        "• присоединитесь к ней через /join\n"
        "• после /start_game вернитесь сюда и снова нажмите /start\n\n"
        "<b>Команды в личке:</b>\n"
        "• /start — открыть свою руку и текущее состояние\n"
        "• /special — посмотреть особое условие\n"
        "• /vote — открыть приватное голосование, если оно активно"
    )


def private_lobby_wait_text() -> str:
    return (
        "Вы уже в лобби, но партия ещё не началась.\n"
        "Дождитесь команды /start_game от инициатора лобби в группе, затем снова откройте /start здесь."
    )


def new_game_text(game, initiator_name: str) -> str:
    return (
        "<b>Создана новая партия «Бункер»</b>\n\n"
        f"<b>Катастрофа:</b> {safe(game.catastrophe_title)}\n"
        f"{safe(game.catastrophe_text)}\n\n"
        f"<b>Режим:</b> {safe(mode_label(game.mode))}\n"
        "<b>Ведущий:</b> ИИ\n"
        f"<b>Инициатор:</b> {safe(initiator_name)}\n\n"
        "Присоединяйтесь кнопкой или через /join. "
        "Инициатор лобби может сменить режим и запустить игру командой /start_game."
    )


def lobby_card_text(game, initiator_name: str, players: list | None = None) -> str:
    lines = [
        "<b>Создана новая партия «Бункер»</b>",
        "",
        f"<b>Катастрофа:</b> {safe(game.catastrophe_title)}",
        safe(game.catastrophe_text),
        "",
        f"<b>Режим:</b> {safe(mode_label(game.mode))}",
        "<b>Ведущий:</b> ИИ",
        f"<b>Инициатор:</b> {safe(initiator_name)}",
    ]
    if players:
        lines.append("")
        lines.append(f"<b>Участники:</b> {len(players)}")
        for index, player in enumerate(players, start=1):
            username = f" (@{player.username})" if getattr(player, "username", None) else ""
            lines.append(f"{index}. {safe(player.full_name)}{safe(username)}")
    else:
        lines.append("")
        lines.append("<b>Участники:</b> пока никого.")
    lines.append("")
    lines.append("Присоединяйтесь кнопкой или через /join. Инициатор лобби может сменить режим и запустить игру командой /start_game.")
    return "\n".join(lines)


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
    round_counts = dict(special_state.get("round_reveal_counts") or {})
    bonus_rounds = set(special_state.get("extra_reveal_rounds") or [])
    allowed_reveals = 2 if game.round in bonus_rounds else 1
    revealed_this_round = int(round_counts.get(str(game.round), 0))

    lines = [
        "<b>🃏 Ваша рука</b>",
        "",
        "<b>🧭 Состояние партии</b>",
        f"• <b>Режим:</b> {safe(mode_label(game.mode))}",
        f"• <b>Фаза:</b> {safe(phase_label(game.phase))}",
        f"• <b>Раунд:</b> {game.round}/{game.round_limit}",
        f"• <b>Статус:</b> {safe(player_status(player))}",
        f"• <b>Катастрофа:</b> {safe(game.catastrophe_title)}",
        "",
    ]

    if game.phase == "discussion" and getattr(player, "faction_status", "alive") == "alive":
        if revealed_this_round < allowed_reveals:
            if game.round == 1:
                lines.append("<b>🎙 Ваш ход:</b> в первом раунде нужно раскрыть профессию.")
            else:
                left = allowed_reveals - revealed_this_round
                lines.append(f"<b>🎙 Ваш ход:</b> выберите карту для раскрытия кнопками ниже. Осталось раскрытий в этом раунде: {left}.")
        else:
            lines.append("<b>✅ В этом раунде вы уже раскрыли всё, что положено по правилам.</b>")
        lines.append("")

    lines.append("<b>👤 Карты персонажа</b>")
    for key in ("biology", "profession", "health", "hobby", "luggage", "fact"):
        card = character_cards.get(key)
        if not card:
            continue
        icon = CARD_ICONS.get(key, "•")
        visibility = "Открыто" if key in revealed else "Скрыто"
        lines.append(f"{icon} <b>{card_label(key)}:</b> {safe(card['text'])}")
        lines.append(f"<i>{visibility}</i>")
    lines.append("")
    lines.append("<b>⚖️ Особое условие</b>")
    lines.append(f"<b>{safe(condition.get('title', 'Неизвестно'))}</b>")
    lines.append(safe(condition.get("text", "")))
    if special_state.get("goal_target_user_name"):
        lines.append(f"<b>🎯 Тайная цель:</b> {safe(special_state['goal_target_user_name'])}")
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
        "<b>Партия завершена</b>" if not forced else "<b>Партия остановлена инициатором лобби</b>",
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
