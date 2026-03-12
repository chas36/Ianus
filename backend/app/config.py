from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ianus:ianus_dev@localhost:5432/ianus"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 720

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
