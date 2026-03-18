from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    DATABASE_URL: str = "sqlite+aiosqlite:///osmosis.db"
    OPENROUTER_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    SUBDL_API_KEY: str = ""
    OIDC_ISSUER: str = "https://auth.osmosis.page/application/o/osmosis/"
    OIDC_CLIENT_ID: str = "osmosis"
    OIDC_REDIRECT_URI: str = "http://localhost:8000/api/auth/callback"
    SECRET_KEY: str = "change-me-in-production"
    DAILY_TOKEN_LIMIT: int = 50000
    DEV_MODE: bool = False


settings = Settings()

# ── Non-secret configuration ──────────────────────────────────────────
# Used by app.llm.summarization_model() as the OpenRouter fallback
SUMMARIZATION_MODEL = "google/gemini-2.0-flash-001"

# Default chat model — overridden by system.prompt / onboarding.prompt frontmatter
CHAT_MODEL = "openrouter/anthropic/claude-sonnet-4-5"
