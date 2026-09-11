import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass
class Config:
    bot_token: str
    admin_id: int
    blackbird_dir: Path


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

    blackbird_dir_raw = source.get("BLACKBIRD_DIR")
    if not blackbird_dir_raw:
        raise ConfigError("BLACKBIRD_DIR is not set in .env")

    return Config(
        bot_token=bot_token,
        admin_id=admin_id,
        blackbird_dir=Path(blackbird_dir_raw),
    )
