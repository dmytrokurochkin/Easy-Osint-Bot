import pytest
from pathlib import Path
from core.config import load_config, ConfigError, Config, BLACKBIRD_DIR


def test_load_config_success():
    env = {"BOT_TOKEN": "123:ABC", "ADMIN_ID": "111222333"}
    config = load_config(env)
    assert config == Config(
        bot_token="123:ABC",
        admin_id=111222333,
        blackbird_dir=BLACKBIRD_DIR,
    )


def test_load_config_missing_bot_token():
    env = {"ADMIN_ID": "1"}
    with pytest.raises(ConfigError, match="BOT_TOKEN"):
        load_config(env)


def test_load_config_missing_admin_id():
    env = {"BOT_TOKEN": "123:ABC"}
    with pytest.raises(ConfigError, match="ADMIN_ID"):
        load_config(env)


def test_load_config_admin_id_not_integer():
    env = {"BOT_TOKEN": "123:ABC", "ADMIN_ID": "not-a-number"}
    with pytest.raises(ConfigError, match="ADMIN_ID"):
        load_config(env)


def test_blackbird_dir_points_at_vendored_directory():
    assert BLACKBIRD_DIR.name == "blackbird"
    assert (BLACKBIRD_DIR / "blackbird.py").exists()
