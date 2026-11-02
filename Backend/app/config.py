from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = ""
    database_url: str
    webapp_url: str = ""
    gemini_api_key: str = ""
    avia_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    groq_api_key: str = ""
    payment_provider_token: str = ""
    dev_user_id: int | None = None
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        extra="ignore",
        env_ignore_empty=True,
    )


settings = Settings()
