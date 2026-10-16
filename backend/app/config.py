from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://crisalid:devpassword@localhost:5432/crisalid_benchmark"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-secret-key"

    # Single-admin basic auth — stand-in until Keycloak is wired up. The hash
    # is generated via `python -m scripts.hash_password <password>` (see
    # backend/scripts/hash_password.py) and pasted into .env; never store the
    # plaintext password anywhere. Session cookies are signed with SECRET_KEY.
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = ""

    # Qualitative indicators (evaluation-grid, app/services/quality/). Reference
    # dumps (DOAJ journal CSV, Retraction Watch CSV) are downloaded here and
    # refreshed when older than QUALITY_DUMPS_MAX_AGE_DAYS; per-work Crossref/
    # HAL/PubMed records are re-fetched after QUALITY_SOURCES_TTL_DAYS.
    QUALITY_DATA_DIR: str = "/app/uploads/quality"
    QUALITY_DUMPS_MAX_AGE_DAYS: int = 7
    QUALITY_SOURCES_TTL_DAYS: int = 90
    NCBI_API_KEY: str = ""

    # Optional small LLM served by vLLM (OpenAI-compatible API), used only for
    # criteria the structured sources cannot settle — currently criterion 1
    # (peer review) for journals absent from DOAJ, read from the journal's own
    # website and cached per journal. Disabled while VLLM_BASE_URL is empty.
    VLLM_BASE_URL: str = ""  # e.g. http://vllm:8000/v1
    VLLM_MODEL: str = ""
    VLLM_API_KEY: str = ""
    VLLM_MAX_JOURNALS_PER_RUN: int = 200

    # NOTE: The OpenAlex API key is NOT here — it is entered through the /setup
    # wizard and stored in the instance_config database row. This avoids
    # exposing it in the environment / .env file.


settings = Settings()