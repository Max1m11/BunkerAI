from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(validation_alias=AliasChoices("BOT_TOKEN"))
    ai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AI_API_KEY", "ANTHROPIC_API_KEY"),
    )
    ai_provider: str = Field(
        default="openrouter",
        validation_alias=AliasChoices("AI_PROVIDER"),
    )
    ai_model: str = Field(
        default="google/gemini-2.5-flash",
        validation_alias=AliasChoices("AI_MODEL"),
    )
    webapp_url: str = Field(validation_alias=AliasChoices("WEBAPP_URL"))
    webapp_port: int = Field(default=8000, validation_alias=AliasChoices("WEBAPP_PORT"))
    db_path: str = Field(default="./bunker.db", validation_alias=AliasChoices("DB_PATH"))
    discussion_minutes: int = Field(
        default=5,
        validation_alias=AliasChoices("DISCUSSION_MINUTES"),
    )
    voting_minutes: int = Field(
        default=2,
        validation_alias=AliasChoices("VOTING_MINUTES"),
    )
    min_players: int = Field(default=4, validation_alias=AliasChoices("MIN_PLAYERS"))
    max_players: int = Field(default=12, validation_alias=AliasChoices("MAX_PLAYERS"))

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
