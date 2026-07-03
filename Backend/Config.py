import os
from pathlib import Path

from dotenv import dotenv_values


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
_ENV_VALUES = dotenv_values(ENV_PATH)


class ConfigError(RuntimeError):
    """Raised when required SmartVoice configuration is missing."""


def get_env(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = _ENV_VALUES.get(name)
    if value is None or str(value).strip() == "":
        value = os.environ.get(name, default)

    if required and (value is None or str(value).strip() == ""):
        raise ConfigError(
            f"Missing required configuration: {name}. "
            "Add it to .env or copy .env.example to .env and fill it in."
        )

    return value


def require_env(name: str) -> str:
    return str(get_env(name, required=True))
