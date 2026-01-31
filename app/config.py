from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Core APIs
    firecrawl_api_key: str = ""
    reducto_api_key: str = ""
    openrouter_api_key: str = ""
    mongodb_uri: str = "mongodb://localhost:27017/signals"
    resend_api_key: str = ""

    # Server
    port: int = 3001

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()