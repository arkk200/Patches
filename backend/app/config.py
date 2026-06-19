from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "sqlite:///./patches.db"

    uploads_dir: str = str(BASE_DIR / "storage" / "uploads")
    artifacts_dir: str = str(BASE_DIR / "storage" / "artifacts")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
