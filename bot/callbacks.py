from aiogram.filters.callback_data import CallbackData


class JoinGameCallback(CallbackData, prefix="join"):
    game_id: str


class SetModeCallback(CallbackData, prefix="mode"):
    game_id: str
    mode: str


class NextPhaseCallback(CallbackData, prefix="next"):
    game_id: str


class RevealTraitCallback(CallbackData, prefix="reveal"):
    game_id: str
    trait_key: str


class VoteCallback(CallbackData, prefix="vote"):
    game_id: str
    target_user_id: int


class CardViewCallback(CallbackData, prefix="card"):
    game_id: str


class SpecialMenuCallback(CallbackData, prefix="spmenu"):
    game_id: str


class SpecialUseCallback(CallbackData, prefix="spuse"):
    game_id: str
    target_user_id: int
