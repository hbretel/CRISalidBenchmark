from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://crisalid:devpassword@localhost:5432/crisalid_benchmark"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-secret-key"

    # NOTE: The OpenAlex API key is NOT here — it is entered through the /setup
    # wizard and stored in the instance_config database row. This avoids
    # exposing it in the environment / .env file.


settings = Settings()