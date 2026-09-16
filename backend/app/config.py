"""Environment configuration."""
from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


def allowed_origins() -> list[str]:
    """Return normalized CORS origins."""
    return [item.strip().rstrip("/") for item in os.getenv("ALLOWED_ORIGINS", "http://localhost:5500").split(",") if item.strip()]
