import os
from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "RecoverAI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    APP_URL: str = "https://recoverai-3ny5.onrender.com" if os.getenv("RENDER") else "http://localhost:3000"
    API_URL: str = "https://recoverai-u329.onrender.com" if os.getenv("RENDER") else "http://localhost:8000"
    CORS_ORIGINS: Union[List[str], str] = [
        "https://recoverai-frontend-3ny5.onrender.com",
        "https://recoverai-3ny5.onrender.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'recoverai.db'))}"
    DB_ECHO: bool = False

    # Authentication & Security
    JWT_SECRET_KEY: str = "recoverai-jwt-secret-key-enterprise-saas-2026-secure-signature"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    COOKIE_NAME: str = "recoverai_session"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"

    # Payment Provider Configuration ("mock" or "razorpay")
    PAYMENT_PROVIDER: str = "mock"
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def canonicalize_sqlite_path(cls, v: str) -> str:
        if v.startswith("sqlite+aiosqlite:///./"):
            rel_file = v.replace("sqlite+aiosqlite:///./", "")
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
            return f"sqlite+aiosqlite:///{os.path.join(base_dir, rel_file)}"
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        origins: List[str] = []
        if isinstance(v, str):
            v_clean = v.strip()
            if v_clean.startswith("[") and v_clean.endswith("]"):
                import json
                try:
                    parsed = json.loads(v_clean)
                    if isinstance(parsed, list):
                        for item in parsed:
                            if isinstance(item, str) and item.strip():
                                clean = item.strip().strip("'\"").rstrip("/")
                                if clean and clean not in origins:
                                    origins.append(clean)
                except Exception:
                    pass
            if not origins:
                for item in v_clean.split(","):
                    clean = item.strip().strip("'\"").rstrip("/")
                    if clean and clean not in origins:
                        origins.append(clean)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str) and item.strip():
                    clean = item.strip().strip("'\"").rstrip("/")
                    if clean and clean not in origins:
                        origins.append(clean)

        # Always include production frontend origin and local dev origins
        known_origins = [
            "https://recoverai-frontend-3ny5.onrender.com",
            "https://recoverai-3ny5.onrender.com",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
        ]
        for known in known_origins:
            if known not in origins:
                origins.append(known)

        return origins

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
