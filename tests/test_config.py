import pytest
from pathlib import Path
from core.config import load_config, ConfigError, Config


def test_load_config_success():
    env = {
        "BOT_TOKEN": "123:ABC",
        "ADMIN_ID": "111222333",
        "BLACKBIRD_DIR": "/opt/blackbird",
    }
    config = load_config(env)
    assert config == Config(
        bot_token="123:ABC",
        admin_id=111222333,
        blackbird_dir=Path("/opt/blackbird"),
    )


def test_load_config_missing_bot_token():
    env = {"ADMIN_ID": "1", "BLACKBIRD_DIR": "/opt/blackbird"}
    with pytest.raises(ConfigError, match="BOT_TOKEN"):
        load_config(env)


def test_load_config_missing_admin_id():
    env = {"BOT_TOKEN": "123:ABC", "BLACKBIRD_DIR": "/opt/blackbird"}
    with pytest.raises(ConfigError, match="ADMIN_ID"):
        load_config(env)


def test_load_config_admin_id_not_integer():
    env = {"BOT_TOKEN": "123:ABC", "ADMIN_ID": "not-a-number", "BLACKBIRD_DIR": "/opt/blackbird"}
    with pytest.raises(ConfigError, match="ADMIN_ID"):
        load_config(env)


def test_load_config_missing_blackbird_dir():
    env = {"BOT_TOKEN": "123:ABC", "ADMIN_ID": "1"}
    with pytest.raises(ConfigError, match="BLACKBIRD_DIR"):
        load_config(env)
