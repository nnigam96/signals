from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Core APIs
    mongodb_uri: str = "mongodb://localhost:27017/signals"
    firecrawl_api_key: str = ""
    openrouter_api_key: str = ""
    reducto_api_key: str = ""
    resend_api_key: str = ""

    # Model Configs
    model_name: str = "openai/gpt-4o-mini"
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # Server
    port: int = 3001

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
