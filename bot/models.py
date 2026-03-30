from __future__ import annotations

from pydantic import BaseModel, Field


class Game(BaseModel):
    id: str
    chat_id: int
    mode: str = "basic_final"
    scenario_id: str
    scenario_title: str
    scenario_hint: str
    phase: str
    phase_step: str = ""
    round: int = 0
    round_limit: int = 5
    host_id: int
    slots: int = 0
    catastrophe_id: str
    catastrophe_title: str
    catastrophe_text: str
    opened_bunker_cards: str = "[]"
    opened_threat_cards: str = "[]"
    revote_state: str = "{}"
    endgame_state: str = "{}"
    phase_deadline_at: str | None = None
    created_at: str
    updated_at: str


class Player(BaseModel):
    id: str
    game_id: str
    user_id: int
    username: str | None = None
    full_name: str
    faction_status: str = "alive"
    is_exiled: int = 0
    character_cards: str = "{}"
    special_condition: str = "{}"
    special_state: str = "{}"
    revealed_character_keys: str = "[]"


class Vote(BaseModel):
    id: str
    game_id: str
    round: int
    phase_step: str
    faction: str
    voter_id: int
    target_id: str
    created_at: str


class RevealResult(BaseModel):
    game: Game
    player: Player
    trait_key: str
    trait_value: str
    auto_revealed: bool = False


class VoteProgress(BaseModel):
    game: Game
    voter: Player
    total_votes: int
    total_expected: int
    all_voted: bool


class SpecialResult(BaseModel):
    game: Game
    player: Player
    action: str
    private_message: str
    public_message: str | None = None
    target: Player | None = None


class RoundResolution(BaseModel):
    game: Game
    players: list[Player] = Field(default_factory=list)
    exiled: list[Player] = Field(default_factory=list)
    outcome: str
    finished: bool = False
    winners: list[Player] = Field(default_factory=list)
    outside_winners: list[Player] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
