from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    database_url: str
    webapp_url: str
    gemini_api_key: str
    dev_user_id: int | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()