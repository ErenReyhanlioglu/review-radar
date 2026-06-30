from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "apollo_reviews"

    anthropic_api_key: str
    openai_api_key: str

    gmail_app_password: str = ""

    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
