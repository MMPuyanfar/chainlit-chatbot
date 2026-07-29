import os
from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. Check your .env file."
        )
    return value


API_KEY: str = _require_env("API_KEY")
API_ENDPOINT: str = _require_env("API_ENDPOINT")
MODEL: str = _require_env("MODEL")

REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "60.0"))
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "2"))
MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))
SYSTEM_PROMPT: str = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")
