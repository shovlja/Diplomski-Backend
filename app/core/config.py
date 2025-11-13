# app/core/config.py
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, root_validator   # ⬅ dodaj root_validator

def _load_jwt_secret() -> str:
    env_secret = os.getenv("JWT_SECRET")
    if env_secret:
        return env_secret.strip()

    path = os.getenv("JWT_SECRET_FILE", "/run/secrets/jwt_secret")
    p = Path(path)
    if p.is_dir():
        p = p / "jwt_secret"
    if p.exists() and p.is_file():
        return p.read_text(encoding="utf-8").strip()

    return "dev-secret-change-me"

class Settings(BaseSettings):
    app_name: str = "PM Hub"
    debug: bool = True
    database_url: str
    frontend_url: str

    # JWT
    jwt_alg: str = "HS256"
    jwt_expires_in: int = 3600
    jwt_secret_file: Optional[Path] = None
    jwt_secret: Optional[str] = None   # može doći iz env/secreta

    # ❗️Back-compat za stari kod
    secret_key: Optional[str] = None

    @root_validator(pre=True)
    def _fill_secrets(cls, values):
        # ako jwt_secret nije postavljen kroz env/secrets, učitaj ga iz fajla / fallback
        if not values.get("jwt_secret"):
            values["jwt_secret"] = _load_jwt_secret()
        # secret_key = jwt_secret (alias)
        if not values.get("secret_key"):
            values["secret_key"] = values["jwt_secret"]
        return values

    class Config:
        env_file = ".env"
        fields = {
            "database_url":     {"env": ["DATABASE_URL", "database_url"]},
            "frontend_url":     {"env": ["FRONTEND_URL", "frontend_url"]},
            "debug":            {"env": ["DEBUG", "debug"]},
            "app_name":         {"env": ["APP_NAME", "app_name"]},
            "jwt_alg":          {"env": ["JWT_ALG", "jwt_alg"]},
            "jwt_expires_in":   {"env": ["JWT_EXPIRES_IN", "jwt_expires_in"]},
            "jwt_secret_file":  {"env": ["JWT_SECRET_FILE", "jwt_secret_file"]},
            "jwt_secret":       {"env": ["JWT_SECRET", "jwt_secret"]},
        }

settings = Settings()
