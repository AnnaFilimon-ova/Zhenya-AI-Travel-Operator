from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Всё необязательное имеет значение по умолчанию: без токена бота и ключей
    # веб-часть всё равно запускается и показывает понятные сообщения.
    bot_token: str = ""
    database_url: str
    webapp_url: str = ""
    gemini_api_key: str = ""
    payment_provider_token: str = ""
    dev_user_id: int | None = None
    gemini_model: str = "gemini-3.5-flash"

    # .env ищем рядом с Backend и в корне репозитория; пустые значения считаем незаданными.
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        extra="ignore",
        env_ignore_empty=True,
    )


settings = Settings()
