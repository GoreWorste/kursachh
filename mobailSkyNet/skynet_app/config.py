from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency fallback
    load_dotenv = None


@dataclass
class AppConfig:
    secretKey: str
    mailServer: str
    mailPort: int
    mailUseTls: bool
    mailUsername: str
    mailPassword: str
    mailFrom: str
    passwordResetExpireMinutes: int
    openrouterApiKey: str
    openrouterKnowledgeModel: str
    openrouterBaseUrl: str


def load_app_config(projectRoot: Path) -> AppConfig:
    envPath = projectRoot / ".env"
    if load_dotenv and envPath.exists():
        load_dotenv(envPath)

    return AppConfig(
        secretKey=os.environ.get("SECRET_KEY", "skynet-mobile-dev-secret-key"),
        mailServer=os.environ.get("MAIL_SERVER", "localhost"),
        mailPort=int(os.environ.get("MAIL_PORT", "25")),
        mailUseTls=os.environ.get("MAIL_USE_TLS", "false").lower() == "true",
        mailUsername=os.environ.get("MAIL_USERNAME", ""),
        mailPassword=os.environ.get("MAIL_PASSWORD", ""),
        mailFrom=os.environ.get("MAIL_FROM", "noreply@skynet.local"),
        passwordResetExpireMinutes=int(os.environ.get("PASSWORD_RESET_EXPIRE_MINUTES", "60")),
        openrouterApiKey=os.environ.get("OPENROUTER_API_KEY", "").strip(),
        openrouterKnowledgeModel=os.environ.get("OPENROUTER_KNOWLEDGE_MODEL", "openrouter/auto").strip(),
        openrouterBaseUrl=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/"),
    )
