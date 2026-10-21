from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./event_booking.db"
    jwt_secret: str = "change-this-development-secret-please"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    admin_username: str = "admin"
    admin_password: str = "admin123!"
    seed_demo_data: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()