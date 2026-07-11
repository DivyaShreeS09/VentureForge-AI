"""Application settings, loaded from environment variables (.env)."""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql://postgres:changeme@localhost:5432/ventureforge_ai"
    backend_cors_origins: str = "http://localhost:5173"
    model_dir: str = str(_BACKEND_DIR.parent / "ml" / "models")

    # Optional narrative enhancement (see backend/app/ai/). Unset by default — the deterministic
    # Judge Agent is fully functional either way. Never sent to the frontend.
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    @field_validator("model_dir")
    @classmethod
    def _anchor_model_dir(cls, value: str) -> str:
        """A relative MODEL_DIR (the .env.example default, `../ml/models`) must resolve the same
        way no matter where the process is launched from. Resolving it against the current working
        directory broke the integration suite, which the README documents running from the repo
        root while backend/.env's `../ml/models` assumes a `backend/` cwd. Anchoring to this file's
        own location instead makes the setting cwd-independent."""
        path = Path(value)
        return str(path) if path.is_absolute() else str((_BACKEND_DIR / path).resolve())


settings = Settings()
