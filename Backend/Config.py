import os
import sys
from pathlib import Path

from dotenv import dotenv_values


def _resolve_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _resolve_resource_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()
    return ROOT_DIR


ROOT_DIR = _resolve_app_dir()
RESOURCE_DIR = _resolve_resource_dir()
DATA_DIR = ROOT_DIR / "Data"
FRONTEND_FILES_DIR = ROOT_DIR / "Frontend" / "Files"
ENV_PATH = ROOT_DIR / ".env"
_ENV_VALUES = dotenv_values(ENV_PATH)

REQUIRED_CONFIG_KEYS = (
    "CohereAPIKey",
    "GroqAPIKey",
    "SerperAPIkey",
    "HuggingFaceAPIKey",
)

SETUP_REQUIRED_CONFIG_KEYS = (
    "Username",
    "Assistantname",
    *REQUIRED_CONFIG_KEYS,
)

PLACEHOLDER_VALUES = {
    "your name",
    "your_cohere_api_key",
    "your_groq_api_key",
    "your_serper_api_key",
    "your_huggingface_api_key",
    "change_me",
    "replace_me",
    "todo",
}


class ConfigError(RuntimeError):
    """Raised when required SmartVoice configuration is missing."""


def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_FILES_DIR.mkdir(parents=True, exist_ok=True)


def reload_env() -> dict[str, str | None]:
    global _ENV_VALUES

    _ENV_VALUES = dotenv_values(ENV_PATH)
    return dict(_ENV_VALUES)


def is_placeholder_value(value: str | None) -> bool:
    if value is None:
        return True

    normalized = str(value).strip().lower()
    if normalized == "":
        return True
    if normalized in PLACEHOLDER_VALUES:
        return True
    if normalized.startswith("your_") or normalized.startswith("your-"):
        return True
    if normalized.startswith("<") and normalized.endswith(">"):
        return True
    return False


def get_env(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = _ENV_VALUES.get(name)
    if is_placeholder_value(value):
        value = os.environ.get(name, default)

    if required and is_placeholder_value(value):
        raise ConfigError(
            f"Missing required configuration: {name}. "
            "Run SmartVoice and complete the setup form, or fill it in .env."
        )

    return value


def require_env(name: str) -> str:
    return str(get_env(name, required=True))


def missing_config_keys(required_keys=SETUP_REQUIRED_CONFIG_KEYS) -> list[str]:
    reload_env()
    return [
        key for key in required_keys
        if is_placeholder_value(get_env(key))
    ]


def config_needs_setup(required_keys=SETUP_REQUIRED_CONFIG_KEYS) -> bool:
    return bool(missing_config_keys(required_keys))


ensure_runtime_dirs()
