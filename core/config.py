import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


# blackbird is vendored directly in this repo (see blackbird/), not a
# separately-cloned tool the user points at via .env, so its path is a
# fixed constant, not configuration.
BLACKBIRD_DIR = Path(__file__).resolve().parent.parent / "blackbird"


@dataclass
class Config:
    bot_token: str
    admin_id: int
    blackbird_dir: Path = BLACKBIRD_DIR


def load_config(env: dict | None = None) -> Config:
    source = env if env is not None else os.environ

    bot_token = source.get("BOT_TOKEN")
    if not bot_token:
        raise ConfigError("BOT_TOKEN is not set in .env")

    admin_id_raw = source.get("ADMIN_ID")
    if not admin_id_raw:
        raise ConfigError("ADMIN_ID is not set in .env")
    try:
        admin_id = int(admin_id_raw)
    except ValueError:
        raise ConfigError("ADMIN_ID must be an integer Telegram user id") from None

    return Config(bot_token=bot_token, admin_id=admin_id)
