from __future__ import annotations

import random
from typing import Any


CHARACTER_KEYS = ["biology", "profession", "health", "hobby", "luggage", "fact"]
CARD_KEYS = CHARACTER_KEYS.copy()

MODE_LABELS = {
    "basic_final": "Базовый финал",
    "survival_story": "История выживания",
}

ROUND_EXILES = {
    4: [0, 0, 0, 1, 1],
    5: [0, 0, 1, 1, 1],
    6: [0, 0, 1, 1, 1],
    7: [0, 1, 1, 1, 1],
    8: [0, 1, 1, 1, 1],
    9: [0, 1, 1, 1, 2],
    10: [0, 1, 1, 1, 2],
    11: [0, 1, 1, 2, 2],
    12: [0, 1, 1, 2, 2],
    13: [0, 1, 2, 2, 2],
    14: [0, 1, 2, 2, 2],
    15: [0, 2, 2, 2, 2],
    16: [0, 2, 2, 2, 2],
}

SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "cat_nuclear_winter",
        "emoji": "☢️",
        "title": "Ядерная зима",
        "hint": "Поверхность заражена, инфраструктура разрушена, ценятся медики, инженеры и специалисты по автономному быту.",
        "text": "После обмена ударами большая часть суши заражена. Придётся жить долго, экономно и в условиях дефицита ресурсов.",
        "required_tags": ["medicine", "engineering", "food", "repair"],
        "helpful_tags": ["security", "science", "navigation", "logistics"],
        "harmful_tags": ["infection", "panic", "severe_disability"],
        "threshold": 8,
        "requires_pair": True,
    },
    {
        "id": "cat_global_pandemic",
        "emoji": "🦠",
        "title": "Глобальная пандемия",
        "hint": "Критичны врачебные навыки, карантин, иммунитет и чистые помещения.",
        "text": "Вирус мутировал несколько раз. Любая ошибка в санитарии может уничтожить всю группу за считанные недели.",
        "required_tags": ["medicine", "science", "sanitation"],
        "helpful_tags": ["discipline", "psychology", "food"],
        "harmful_tags": ["infection", "chronic_illness"],
        "threshold": 8,
        "requires_pair": True,
    },
    {
        "id": "cat_flood",
        "emoji": "🌊",
        "title": "Глобальный потоп",
        "hint": "Нужны навыки выживания, ремонта, навигации и добычи еды в сырой среде.",
        "text": "Береговая линия исчезла, климат нестабилен, сухих и безопасных точек почти не осталось.",
        "required_tags": ["repair", "navigation", "food"],
        "helpful_tags": ["security", "medicine", "engineering"],
        "harmful_tags": ["panic"],
        "threshold": 7,
        "requires_pair": True,
    },
    {
        "id": "cat_ice_age",
        "emoji": "🧊",
        "title": "Новый ледниковый период",
        "hint": "Критичны физическая выносливость, тёплый быт, охота и запас энергии.",
        "text": "Температура резко упала. Ошибка в распределении тепла или еды быстро становится смертельной.",
        "required_tags": ["food", "energy", "repair"],
        "helpful_tags": ["security", "medicine", "discipline"],
        "harmful_tags": ["severe_disability", "chronic_illness"],
        "threshold": 7,
        "requires_pair": True,
    },
    {
        "id": "cat_machine_uprising",
        "emoji": "🤖",
        "title": "Восстание машин",
        "hint": "Полезны технари, электрики, программисты и те, кто умеет работать автономно.",
        "text": "Сети и автоматизированные комплексы вышли из-под контроля. Доступ к технике даёт преимущества, но создаёт риск.",
        "required_tags": ["engineering", "science", "energy"],
        "helpful_tags": ["repair", "discipline", "security"],
        "harmful_tags": ["panic"],
        "threshold": 7,
        "requires_pair": True,
    },
    {
        "id": "cat_asteroid",
        "emoji": "☄️",
        "title": "Падение астероида",
        "hint": "Главное — быстрое восстановление быта, организация группы и медицинская устойчивость.",
        "text": "Ударные волны, пожары и долгий климатический след уничтожили привычные цепочки снабжения.",
        "required_tags": ["medicine", "repair", "food"],
        "helpful_tags": ["engineering", "discipline", "psychology"],
        "harmful_tags": ["panic", "infection"],
        "threshold": 8,
        "requires_pair": True,
    },
    {
        "id": "cat_supervolcano",
        "emoji": "🌋",
        "title": "Супервулкан",
        "hint": "Важны вентиляция, запасы воды и еды, медицинский контроль и психологическая устойчивость.",
        "text": "Пепел закрыл небо, урожаи погибли, а воздух часто становится опасным без фильтрации.",
        "required_tags": ["sanitation", "food", "medicine"],
        "helpful_tags": ["engineering", "discipline"],
        "harmful_tags": ["respiratory", "panic"],
        "threshold": 8,
        "requires_pair": True,
    },
    {
        "id": "cat_solar_storm",
        "emoji": "⚡",
        "title": "Солнечный шторм",
        "hint": "Техника горит, связи нет, полезны автономные ремесленные и медицинские навыки.",
        "text": "Энергосистемы выведены из строя. Выживают те, кто умеет жить без привычной электроники.",
        "required_tags": ["repair", "food", "medicine"],
        "helpful_tags": ["engineering", "discipline", "security"],
        "harmful_tags": ["panic"],
        "threshold": 7,
        "requires_pair": True,
    },
]

BUNKER_CARDS: list[dict[str, Any]] = [
    {"id": "bunker_medbay", "title": "Медицинский отсек", "text": "Есть базовые медикаменты и стерильный уголок.", "tags": ["medicine", "sanitation"], "score": 2, "source_confidence": "medium"},
    {"id": "bunker_hydroponics", "title": "Гидропонный модуль", "text": "Можно выращивать простые культуры круглый год.", "tags": ["food"], "score": 2, "source_confidence": "medium"},
    {"id": "bunker_workshop", "title": "Ремонтная мастерская", "text": "Набор инструмента и рабочие столы помогают чинить ключевые системы.", "tags": ["repair", "engineering"], "score": 2, "source_confidence": "medium"},
    {"id": "bunker_generator", "title": "Резервный генератор", "text": "Энергия ограничена, но критические узлы можно поддерживать.", "tags": ["energy"], "score": 2, "source_confidence": "medium"},
    {"id": "bunker_filters", "title": "Фильтрация воздуха", "text": "Воздух можно очищать дольше обычного.", "tags": ["sanitation"], "score": 1, "source_confidence": "medium"},
    {"id": "bunker_armory", "title": "Закрытый оружейный шкаф", "text": "Есть немного снаряжения для охраны и выхода наружу.", "tags": ["security"], "score": 1, "source_confidence": "medium"},
    {"id": "bunker_library", "title": "Архив и инструкции", "text": "Справочники по медицине, технике и быту повышают шансы группы.", "tags": ["science", "discipline"], "score": 1, "source_confidence": "medium"},
    {"id": "bunker_water", "title": "Резерв воды", "text": "Запаса хватает, чтобы пережить провал ближайшего снабжения.", "tags": ["sanitation", "food"], "score": 1, "source_confidence": "medium"},
    {"id": "bunker_kitchen", "title": "Кухонный блок", "text": "Можно безопасно хранить и готовить еду.", "tags": ["food"], "score": 1, "source_confidence": "medium"},
    {"id": "bunker_lab", "title": "Небольшая лаборатория", "text": "Есть условия для простого анализа, сортировки образцов и экспериментов.", "tags": ["science"], "score": 1, "source_confidence": "medium"},
    {"id": "bunker_greenhouse", "title": "Тёплая оранжерея", "text": "Модуль пригоден для семян и лекарственных трав.", "tags": ["food", "medicine"], "score": 2, "source_confidence": "medium"},
    {"id": "bunker_radio", "title": "Узел связи", "text": "Иногда можно поймать сигнал и получить полезную информацию.", "tags": ["navigation", "logistics"], "score": 1, "source_confidence": "medium"},
]

THREAT_CARDS: list[dict[str, Any]] = [
    {"id": "threat_fire", "title": "Пожар внутри", "text": "Нужны дисциплина, ремонт и быстрые решения.", "required_tags": ["repair", "discipline"], "harmful_tags": ["panic"], "threshold": 2, "source_confidence": "medium"},
    {"id": "threat_infection", "title": "Очаг инфекции", "text": "Без медицины и санитарии заражение выйдет из-под контроля.", "required_tags": ["medicine", "sanitation"], "harmful_tags": ["infection"], "threshold": 2, "source_confidence": "medium"},
    {"id": "threat_raiders", "title": "Налёт мародёров", "text": "Критичны безопасность, дисциплина и холодная голова.", "required_tags": ["security", "discipline"], "harmful_tags": ["panic"], "threshold": 2, "source_confidence": "medium"},
    {"id": "threat_power_loss", "title": "Сбой энергосистемы", "text": "Без энергии и ремонта бункер резко теряет преимущества.", "required_tags": ["energy", "repair"], "harmful_tags": [], "threshold": 2, "source_confidence": "medium"},
    {"id": "threat_food_rot", "title": "Порча запасов", "text": "Помогают пищевые навыки, холодный расчёт и запасной источник еды.", "required_tags": ["food"], "harmful_tags": [], "threshold": 1, "source_confidence": "medium"},
    {"id": "threat_conflict", "title": "Внутренний раскол", "text": "Если нет психологии и дисциплины, команда начинает вредить сама себе.", "required_tags": ["psychology", "discipline"], "harmful_tags": ["panic"], "threshold": 2, "source_confidence": "medium"},
    {"id": "threat_filter_failure", "title": "Поломка фильтров", "text": "Нужны санитария, инженерия и спокойная работа по инструкции.", "required_tags": ["sanitation", "engineering"], "harmful_tags": ["respiratory"], "threshold": 2, "source_confidence": "medium"},
    {"id": "threat_cold_snap", "title": "Резкое похолодание", "text": "Критичны энергия, ремонт и физическая пригодность.", "required_tags": ["energy", "repair"], "harmful_tags": ["chronic_illness"], "threshold": 2, "source_confidence": "medium"},
    {"id": "threat_toxic_rain", "title": "Токсичные осадки", "text": "Выход наружу опасен, нужна чёткая защита и санитарный контроль.", "required_tags": ["sanitation", "security"], "harmful_tags": ["infection", "respiratory"], "threshold": 2, "source_confidence": "medium"},
    {"id": "threat_water_loss", "title": "Потеря доступа к воде", "text": "Требуются логистика, запас и дисциплина в распределении.", "required_tags": ["logistics", "sanitation"], "harmful_tags": [], "threshold": 2, "source_confidence": "medium"},
    {"id": "threat_outside_mission", "title": "Рискованный выход наружу", "text": "Нужны безопасность, навигация и умение чинить снаряжение.", "required_tags": ["security", "navigation", "repair"], "harmful_tags": ["panic"], "threshold": 3, "source_confidence": "medium"},
]

SCENARIO_BY_ID = {item["id"]: item for item in SCENARIOS}
BUNKER_BY_ID = {item["id"]: item for item in BUNKER_CARDS}
THREAT_BY_ID = {item["id"]: item for item in THREAT_CARDS}
SPECIAL_CONDITION_BY_ID = {}


def _char(card_id: str, text: str, tags: list[str], prototype: str) -> dict[str, Any]:
    return {
        "id": card_id,
        "text": text,
        "tags": tags,
        "official_prototype": prototype,
        "source_confidence": "medium",
    }


CHARACTER_DECKS: dict[str, list[dict[str, Any]]] = {
    "biology": [
        _char("bio_m_25_fertile", "Мужчина, 25 лет, репродуктивно здоров.", ["male", "young", "fertile"], "biology"),
        _char("bio_f_24_fertile", "Женщина, 24 года, без ограничений по деторождению.", ["female", "young", "fertile"], "biology"),
        _char("bio_m_34_fit", "Мужчина, 34 года, крепкое телосложение.", ["male", "adult", "fit"], "biology"),
        _char("bio_f_31_fit", "Женщина, 31 год, спортивная и выносливая.", ["female", "adult", "fit"], "biology"),
        _char("bio_m_41", "Мужчина, 41 год, без выраженных возрастных ограничений.", ["male", "adult"], "biology"),
        _char("bio_f_39", "Женщина, 39 лет, зрелая и устойчивая к стрессу.", ["female", "adult"], "biology"),
        _char("bio_m_52", "Мужчина, 52 года, опытный, но не самый выносливый.", ["male", "senior"], "biology"),
        _char("bio_f_49", "Женщина, 49 лет, спокойная и собранная.", ["female", "senior"], "biology"),
        _char("bio_m_63", "Мужчина, 63 года, возрастной, с ограниченным ресурсом сил.", ["male", "elderly"], "biology"),
        _char("bio_f_61", "Женщина, 61 год, возрастная, но дисциплинированная.", ["female", "elderly"], "biology"),
        _char("bio_m_28_childfree", "Мужчина, 28 лет, сознательно не планирует детей.", ["male", "young", "childfree"], "biology"),
        _char("bio_f_27_childfree", "Женщина, 27 лет, не хочет заводить детей.", ["female", "young", "childfree"], "biology"),
        _char("bio_m_36_single_parent", "Мужчина, 36 лет, уже воспитывал ребёнка один.", ["male", "adult", "caregiving"], "biology"),
        _char("bio_f_35_single_parent", "Женщина, 35 лет, опыт материнства и ухода за детьми.", ["female", "adult", "caregiving", "fertile"], "biology"),
        _char("bio_m_22", "Мужчина, 22 года, легко адаптируется к нагрузкам.", ["male", "young", "fit"], "biology"),
        _char("bio_f_22", "Женщина, 22 года, быстро учится и хорошо переносит стресс.", ["female", "young", "fit", "fertile"], "biology"),
        _char("bio_m_44", "Мужчина, 44 года, физически средний, ментально устойчивый.", ["male", "adult"], "biology"),
        _char("bio_f_45", "Женщина, 45 лет, зрелая и собранная.", ["female", "adult"], "biology"),
    ],
    "profession": [
        _char("job_surgeon", "Хирург экстренного профиля.", ["medicine", "hands"], "profession"),
        _char("job_paramedic", "Фельдшер скорой помощи.", ["medicine", "discipline"], "profession"),
        _char("job_microbiologist", "Микробиолог-практик.", ["science", "medicine"], "profession"),
        _char("job_agronomist", "Агроном по закрытым системам выращивания.", ["food", "science"], "profession"),
        _char("job_farmer", "Фермер широкого профиля.", ["food", "discipline"], "profession"),
        _char("job_mechanic", "Механик по генераторам и насосам.", ["repair", "engineering"], "profession"),
        _char("job_electrician", "Электрик-силовик.", ["energy", "repair"], "profession"),
        _char("job_programmer", "Системный программист.", ["science", "engineering"], "profession"),
        _char("job_civil_engineer", "Инженер-строитель.", ["engineering", "repair"], "profession"),
        _char("job_security", "Сотрудник охраны объектов.", ["security", "discipline"], "profession"),
        _char("job_police", "Полицейский патрульной службы.", ["security", "discipline"], "profession"),
        _char("job_teacher", "Учитель естественных наук.", ["science", "caregiving"], "profession"),
        _char("job_psychologist", "Кризисный психолог.", ["psychology", "discipline"], "profession"),
        _char("job_cook", "Повар-заготовщик.", ["food", "discipline"], "profession"),
        _char("job_veterinarian", "Ветеринарный врач.", ["medicine", "caregiving"], "profession"),
        _char("job_geologist", "Геолог-полевик.", ["navigation", "science"], "profession"),
        _char("job_welder", "Сварщик монтажных систем.", ["repair", "hands"], "profession"),
        _char("job_driver", "Водитель тяжёлой техники.", ["logistics", "repair"], "profession"),
        _char("job_firefighter", "Пожарный-спасатель.", ["security", "discipline", "fit"], "profession"),
        _char("job_pilot", "Пилот гражданской авиации.", ["navigation", "discipline"], "profession"),
    ],
    "health": [
        _char("health_perfect", "Практически здоров.", ["healthy"], "health"),
        _char("health_asthma", "Лёгкая астма, контролируется терапией.", ["respiratory"], "health"),
        _char("health_diabetes", "Диабет второго типа, требует режима.", ["chronic_illness"], "health"),
        _char("health_vision", "Сильная близорукость.", ["chronic_illness"], "health"),
        _char("health_hearing", "Частичная потеря слуха.", ["chronic_illness"], "health"),
        _char("health_migraine", "Тяжёлые мигрени при перегрузке.", ["chronic_illness"], "health"),
        _char("health_old_injury", "Старая травма колена, иногда мешает длительным выходам.", ["chronic_illness"], "health"),
        _char("health_good", "Крепкое здоровье и хороший иммунитет.", ["healthy"], "health"),
        _char("health_allergy", "Сильная аллергия на несколько лекарств.", ["chronic_illness"], "health"),
        _char("health_hypertension", "Гипертония, нужен контроль давления.", ["chronic_illness"], "health"),
        _char("health_infection", "Есть опасное хроническое инфекционное заболевание.", ["infection"], "health"),
        _char("health_smoker_lungs", "Слабые лёгкие после долгого стажа курения.", ["respiratory"], "health"),
        _char("health_iron", "Очень вынослив, редко болеет.", ["healthy", "fit"], "health"),
        _char("health_back", "Проблемы со спиной, тяжёлый физический труд ограничен.", ["chronic_illness"], "health"),
        _char("health_epilepsy", "Редкие эпилептические приступы.", ["chronic_illness"], "health"),
        _char("health_panic", "Панические атаки в условиях перегрузки.", ["panic"], "health"),
        _char("health_one_hand", "Нет одной кисти, но хорошо адаптирован к быту.", ["severe_disability"], "health"),
        _char("health_coldproof", "Отлично переносит холод и недосып.", ["healthy", "discipline"], "health"),
    ],
    "hobby": [
        _char("hobby_hunting", "Охота и разделка добычи.", ["food", "security"], "hobby"),
        _char("hobby_fishing", "Рыбалка в сложных погодных условиях.", ["food"], "hobby"),
        _char("hobby_gardening", "Выращивание овощей и зелени.", ["food"], "hobby"),
        _char("hobby_first_aid", "Самостоятельно изучал первую помощь.", ["medicine"], "hobby"),
        _char("hobby_locksmith", "Любительский слесарный ремонт.", ["repair"], "hobby"),
        _char("hobby_radio", "Радиолюбитель и сборка простых передатчиков.", ["engineering", "navigation"], "hobby"),
        _char("hobby_climbing", "Альпинизм и страховка на высоте.", ["fit", "discipline"], "hobby"),
        _char("hobby_cooking", "Готовит и консервирует еду.", ["food"], "hobby"),
        _char("hobby_shooting", "Спортивная стрельба.", ["security"], "hobby"),
        _char("hobby_psychology", "Читает и практикует групповые техники поддержки.", ["psychology"], "hobby"),
        _char("hobby_carpentry", "Сборка мебели и столярка.", ["repair"], "hobby"),
        _char("hobby_geocaching", "Ориентирование и работа с картами.", ["navigation"], "hobby"),
        _char("hobby_fitness", "Функциональные тренировки.", ["fit"], "hobby"),
        _char("hobby_beekeeping", "Основы ухода за пчёлами и растениями.", ["food", "science"], "hobby"),
        _char("hobby_chemistry", "Домашняя химия и простые растворы.", ["science", "sanitation"], "hobby"),
        _char("hobby_scouting", "Походы, костры, лагерь и автономный быт.", ["food", "navigation", "discipline"], "hobby"),
        _char("hobby_tailoring", "Шьёт одежду и чинит снаряжение.", ["repair"], "hobby"),
        _char("hobby_music", "Играет на акустических инструментах и снимает стресс группе.", ["psychology"], "hobby"),
    ],
    "luggage": [
        _char("bag_medkit", "Расширенная аптечка.", ["medicine", "sanitation"], "luggage"),
        _char("bag_tools", "Набор инструмента для ремонта.", ["repair"], "luggage"),
        _char("bag_seeds", "Большой запас семян.", ["food"], "luggage"),
        _char("bag_filter_masks", "Фильтрующие маски и расходники.", ["sanitation"], "luggage"),
        _char("bag_hunting", "Охотничий комплект.", ["security", "food"], "luggage"),
        _char("bag_generator", "Компактный генератор и расходники.", ["energy"], "luggage"),
        _char("bag_water", "Резерв чистой воды.", ["sanitation"], "luggage"),
        _char("bag_manuals", "Справочники по выживанию и ремонту.", ["science", "repair"], "luggage"),
        _char("bag_rations", "Долгие сухпайки.", ["food"], "luggage"),
        _char("bag_radio", "Полевое радио.", ["navigation", "logistics"], "luggage"),
        _char("bag_crossbow", "Тихое охотничье оружие.", ["security", "food"], "luggage"),
        _char("bag_lab", "Набор для анализа воды и базовых проб.", ["science", "sanitation"], "luggage"),
        _char("bag_blankets", "Тёплые комплекты и термоодеяла.", ["energy"], "luggage"),
        _char("bag_rope", "Страховочный комплект и карабины.", ["navigation", "repair"], "luggage"),
        _char("bag_pots", "Полевая кухня и котелки.", ["food"], "luggage"),
        _char("bag_documents", "Папка с полезными контактами и схемами объектов.", ["logistics"], "luggage"),
        _char("bag_battery", "Запас аккумуляторов и зарядка от панели.", ["energy"], "luggage"),
        _char("bag_hygiene", "Большой запас средств гигиены.", ["sanitation"], "luggage"),
    ],
    "fact": [
        _char("fact_speaks_languages", "Свободно говорит на трёх языках.", ["logistics"], "fact"),
        _char("fact_ex_military", "Служил в подразделении быстрой реакции.", ["security", "discipline"], "fact"),
        _char("fact_foster_parent", "Имеет опыт ухода за детьми и пожилыми.", ["caregiving"], "fact"),
        _char("fact_night_worker", "Привык к ночным сменам и недосыпу.", ["discipline"], "fact"),
        _char("fact_addiction", "В прошлом была тяжёлая зависимость, сейчас ремиссия.", ["risk"], "fact"),
        _char("fact_organizer", "Умеет быстро распределять задачи в группе.", ["discipline", "logistics"], "fact"),
        _char("fact_panics_blood", "Теряется при виде крови, хотя старается скрывать это.", ["panic"], "fact"),
        _char("fact_mountain_rescue", "Участвовал в спасательных операциях в горах.", ["navigation", "security"], "fact"),
        _char("fact_memory", "Отличная память на схемы и инструкции.", ["science"], "fact"),
        _char("fact_conflict", "Тяжело переносит жёсткую иерархию и давление.", ["risk"], "fact"),
        _char("fact_animal_care", "Умеет работать с животными.", ["food", "caregiving"], "fact"),
        _char("fact_smuggler", "Умеет тихо добывать и перевозить редкие вещи.", ["logistics", "security"], "fact"),
        _char("fact_donor", "Регулярно был донором крови и следил за здоровьем.", ["healthy"], "fact"),
        _char("fact_religious", "Глубоко религиозен и поддерживает людей в кризисе.", ["psychology"], "fact"),
        _char("fact_cardio", "Бегал марафоны и хорошо переносит нагрузку.", ["fit"], "fact"),
        _char("fact_law", "Разбирается в правилах и умеет договариваться.", ["discipline", "logistics"], "fact"),
        _char("fact_mechanical_talent", "С детства чинит почти всё подряд.", ["repair"], "fact"),
        _char("fact_survival_show", "Прошёл несколько серьёзных курсов выживания.", ["food", "navigation", "discipline"], "fact"),
    ],
}


def _condition(
    card_id: str,
    title: str,
    text: str,
    effect_code: str,
    timing: str,
    activation: str = "manual",
    target: str = "none",
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": card_id,
        "title": title,
        "text": text,
        "effect_code": effect_code,
        "timing": timing,
        "activation": activation,
        "target": target,
        "params": params or {},
        "visibility": "secret",
        "official_prototype": "special_condition",
        "source_confidence": "medium",
    }


SPECIAL_CONDITIONS: list[dict[str, Any]] = [
    _condition("cond_peek_hidden", "Подсмотр карты", "Один раз за игру посмотрите случайную закрытую карту выбранного игрока.", "peek_hidden_once", "discussion", target="alive_any"),
    _condition("cond_peek_condition", "Чужой мотив", "Один раз за игру тайно узнайте особое условие выбранного игрока.", "peek_condition_once", "discussion", target="alive_any"),
    _condition("cond_force_reveal", "Неловкий вопрос", "Один раз за игру вынудите выбранного игрока открыть случайную закрытую карту.", "force_reveal_once", "discussion", target="alive_any"),
    _condition("cond_extra_reveal", "Откровенность", "Один раз за игру откройте в этом раунде на одну карту больше обычного.", "extra_reveal_once", "discussion"),
    _condition("cond_double_vote", "Тихий перевес", "Один раз за игру до вскрытия бюллетеней удвойте свой голос в текущем голосовании.", "double_vote_once", "before_vote"),
    _condition("cond_self_shield", "Личная защита", "Первый раз, когда вас должны изгнать, вы остаетесь в игре.", "shield_self_once", "passive", activation="passive"),
    _condition("cond_other_shield", "Страховка союзника", "Один раз за игру защитите выбранного игрока от ближайшего изгнания.", "shield_target_once", "before_vote", target="alive_any"),
    _condition("cond_bunker_peek", "План объекта", "Один раз за игру тайно посмотрите следующую карту бункера.", "peek_bunker_once", "discussion"),
    _condition("cond_threat_peek", "Плохое предчувствие", "Один раз за игру тайно посмотрите одну будущую угрозу финала.", "peek_threat_once", "discussion"),
    _condition("cond_exiled_tiebreak", "Голос изгнанных", "Если среди изгнанных ничья, именно ваш голос станет решающим.", "exiled_tiebreak", "passive", activation="passive"),
]


for tag, title in [
    ("medicine", "Сбереги медика"),
    ("engineering", "Сбереги инженера"),
    ("food", "Сбереги добытчика еды"),
    ("security", "Сбереги защитника"),
    ("science", "Сбереги исследователя"),
    ("psychology", "Сбереги стабилизатора"),
]:
    SPECIAL_CONDITIONS.append(
        _condition(
            f"cond_goal_keep_{tag}",
            title,
            "Если к финалу в вашей стороне останется хотя бы один подходящий специалист, команда получит бонус. Иначе — штраф.",
            "goal_keep_tag_alive",
            "endgame",
            activation="passive",
            params={"goal_tag": tag, "success_bonus": 2, "fail_penalty": 2},
        )
    )

for tag, title in [
    ("repair", "Сделай ставку на мастеровых"),
    ("sanitation", "Сделай ставку на чистоту"),
    ("navigation", "Сделай ставку на разведку"),
    ("discipline", "Сделай ставку на порядок"),
    ("fit", "Сделай ставку на выносливость"),
]:
    SPECIAL_CONDITIONS.append(
        _condition(
            f"cond_bonus_team_{tag}",
            title,
            "Если в вашей финальной стороне есть нужный профиль, команда получает дополнительный бонус.",
            "endgame_bonus_tag",
            "endgame",
            activation="passive",
            params={"goal_tag": tag, "success_bonus": 1},
        )
    )

SPECIAL_CONDITIONS.extend(
    [
        _condition(
            "cond_goal_pair",
            "Сохрани шанс на продолжение рода",
            "Если среди финальных выживших есть репродуктивно совместимая пара, ваша сторона получает бонус. Иначе — штраф.",
            "goal_need_pair",
            "endgame",
            activation="passive",
            params={"success_bonus": 2, "fail_penalty": 2},
        ),
        _condition(
            "cond_goal_clean_team",
            "Без очага заражения",
            "Если в вашей стороне к финалу не останется опасных инфекционных заболеваний, получите бонус.",
            "goal_no_tag",
            "endgame",
            activation="passive",
            params={"forbidden_tag": "infection", "success_bonus": 2, "fail_penalty": 1},
        ),
        _condition(
            "cond_goal_target_alive",
            "Секретный фаворит",
            "В начале игры получите тайную цель. Если этот игрок останется в вашей стороне к финалу, команда получит бонус.",
            "goal_target_alive",
            "endgame",
            activation="passive",
            params={"success_bonus": 2, "fail_penalty": 2},
        ),
        _condition(
            "cond_goal_target_exiled",
            "Секретный антагонист",
            "В начале игры получите тайную цель. Если этот игрок окажется среди изгнанных, команда получит бонус.",
            "goal_target_exiled",
            "endgame",
            activation="passive",
            params={"success_bonus": 2, "fail_penalty": 2},
        ),
        _condition(
            "cond_outside_bonus",
            "План Б снаружи",
            "Если вы окажетесь среди изгнанных, внешняя группа получит дополнительный шанс в финале.",
            "outside_bonus",
            "endgame",
            activation="passive",
            params={"outside_bonus": 2},
        ),
        _condition(
            "cond_bunker_bonus",
            "План Б внутри",
            "Если вы останетесь в бункере, внутренняя группа получит дополнительный бонус в финале.",
            "bunker_bonus",
            "endgame",
            activation="passive",
            params={"bunker_bonus": 2},
        ),
    ]
)

SPECIAL_CONDITION_BY_ID = {item["id"]: item for item in SPECIAL_CONDITIONS}


def get_random_scenario() -> dict[str, Any]:
    return random.choice(SCENARIOS)


def round_exiles_for(total_players: int, round_number: int) -> int:
    schedule = ROUND_EXILES.get(total_players)
    if not schedule or round_number < 1 or round_number > len(schedule):
        return 0
    return schedule[round_number - 1]


def draw_character_cards() -> dict[str, dict[str, Any]]:
    return {key: random.choice(deck) for key, deck in CHARACTER_DECKS.items()}


def draw_special_condition() -> dict[str, Any]:
    return random.choice(SPECIAL_CONDITIONS)


def draw_bunker_card(excluded_ids: set[str] | None = None) -> dict[str, Any]:
    excluded_ids = excluded_ids or set()
    options = [card for card in BUNKER_CARDS if card["id"] not in excluded_ids]
    return random.choice(options or BUNKER_CARDS)


def draw_threat_card(excluded_ids: set[str] | None = None) -> dict[str, Any]:
    excluded_ids = excluded_ids or set()
    options = [card for card in THREAT_CARDS if card["id"] not in excluded_ids]
    return random.choice(options or THREAT_CARDS)


def content_manifest() -> dict[str, Any]:
    return {
        "scenarios": SCENARIOS,
        "character_decks": CHARACTER_DECKS,
        "special_conditions": SPECIAL_CONDITIONS,
        "bunker_cards": BUNKER_CARDS,
        "threat_cards": THREAT_CARDS,
    }


def get_scenario_by_id(card_id: str) -> dict[str, Any]:
    return SCENARIO_BY_ID[card_id]


def get_bunker_card(card_id: str) -> dict[str, Any]:
    return BUNKER_BY_ID[card_id]


def get_threat_card(card_id: str) -> dict[str, Any]:
    return THREAT_BY_ID[card_id]


def get_special_condition(card_id: str) -> dict[str, Any]:
    return SPECIAL_CONDITION_BY_ID[card_id]
