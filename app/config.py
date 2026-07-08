from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CompetitionConfig(BaseModel):
    code: str
    name: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    football_data_api_token: str
    database_url: str = "sqlite:///./prono.db"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, value: str) -> str:
        # Railway/Render/Heroku-style managed Postgres injects "postgres://" or
        # "postgresql://" with no driver specified, which defaults to psycopg2 (not
        # installed - we use psycopg 3). Normalize so the URL matches what's installed.
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    football_data_base_url: str = "https://api.football-data.org/v4"

    # Adding a competition later is just adding an entry here (same provider/sport).
    # A competition from a different sport/provider would need its own client module
    # alongside football_data.py, but the DB schema, scoring, and routes are already
    # sport-agnostic (a Match is just two teams and a home/away score).
    competitions: list[CompetitionConfig] = [
        CompetitionConfig(code="PL", name="Premier League"),
        CompetitionConfig(code="WC", name="FIFA World Cup"),
    ]

    # Signs the session cookie. Dev-only fallback below - MUST be overridden via env var
    # in any real deployment, or anyone could forge another user's session.
    secret_key: str = "dev-only-insecure-secret-change-me"


settings = Settings()
