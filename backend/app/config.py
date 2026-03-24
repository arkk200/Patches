from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "sqlite:///./patches.db"

    uploads_dir: str = "backend/storage/uploads"
    generated_patches_dir: str = "backend/storage/generated-patches"
    reviews_pending_dir: str = "backend/reviews/pending"
    reviews_approved_dir: str = "backend/reviews/approved"
    reviews_rejected_dir: str = "backend/reviews/rejected"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
